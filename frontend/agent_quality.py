"""Black-box quality checks for the public agent API responses."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


PostJson = Callable[[str, dict[str, Any], int], dict[str, Any]]


@dataclass
class CaseResult:
    case_id: str
    query: str
    passed: bool
    route_ok: bool
    intent_ok: bool
    tools_ok: bool
    sources_ok: bool
    warning_ok: bool
    review_ok: bool
    latency_ok: bool
    extraction_checked: bool
    extraction_ok: bool
    latency_ms: float
    issues: list[str] = field(default_factory=list)


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load JSONL cases and reject duplicate or incomplete identifiers."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            case_id = str(row.get("case_id") or "").strip()
            query = str(row.get("query") or "").strip()
            if not case_id or not query:
                raise ValueError(f"Строка {line_number}: нужны case_id и query")
            if case_id in seen:
                raise ValueError(f"Повтор case_id: {case_id}")
            seen.add(case_id)
            rows.append(row)
    return rows


def _as_allowed(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    return {str(item) for item in value}


def _nested_value(data: dict[str, Any], dotted_key: str) -> Any:
    value: Any = data
    for key in dotted_key.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def _contains_expected(actual: Any, expected: Any) -> bool:
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.casefold() in actual.casefold()
    if isinstance(expected, list):
        actual_items = actual if isinstance(actual, list) else [actual]
        return all(item in actual_items for item in expected)
    return actual == expected


def evaluate_responses(
    case: dict[str, Any],
    route_response: dict[str, Any],
    agent_response: dict[str, Any] | None,
    latency_ms: float,
) -> CaseResult:
    """Compare endpoint responses with a single stress-case contract."""
    issues: list[str] = []
    expected_routes = _as_allowed(case.get("expected_route"))
    actual_route = str(route_response.get("route") or "")
    route_ok = not expected_routes or actual_route in expected_routes
    if not route_ok:
        issues.append(
            f"маршрут {actual_route or 'не указан'}, ожидался {sorted(expected_routes)}"
        )

    expected_intents = _as_allowed(case.get("expected_intents"))
    actual_intent = str(
        (agent_response or {}).get("intent") or route_response.get("intent") or ""
    )
    intent_ok = not expected_intents or actual_intent in expected_intents
    if not intent_ok:
        issues.append(
            f"намерение {actual_intent or 'не указано'}, ожидалось {sorted(expected_intents)}"
        )

    required_tools = set(case.get("required_tools") or [])
    available_tools = set(route_response.get("required_tools") or [])
    available_tools.update((agent_response or {}).get("tools_used") or [])
    missing_tools = sorted(required_tools - available_tools)
    tools_ok = not missing_tools
    if missing_tools:
        issues.append("не запущены инструменты: " + ", ".join(missing_tools))

    required_sources = set(case.get("required_source_kinds") or [])
    source_kinds = {
        str(source.get("kind"))
        for source in (agent_response or {}).get("sources") or []
        if isinstance(source, dict) and source.get("kind")
    }
    missing_sources = sorted(required_sources - source_kinds)
    sources_ok = not missing_sources
    if missing_sources:
        issues.append("не хватает источников: " + ", ".join(missing_sources))

    warnings = " ".join(str(item) for item in (agent_response or {}).get("warnings") or [])
    required_warning_terms = case.get("required_warning_terms") or []
    missing_warning_terms = [
        term for term in required_warning_terms if term.casefold() not in warnings.casefold()
    ]
    warning_ok = not missing_warning_terms
    if missing_warning_terms:
        issues.append(
            "в предупреждениях нет: " + ", ".join(missing_warning_terms)
        )

    expected_review = case.get("human_review_required")
    review_ok = (
        expected_review is None
        or bool((agent_response or {}).get("human_review_required")) is expected_review
    )
    if not review_ok:
        issues.append("неверно определена необходимость проверки экспертом")

    max_latency_ms = float(case.get("max_latency_ms") or 10_000)
    latency_ok = latency_ms <= max_latency_ms
    if not latency_ok:
        issues.append(
            f"время {latency_ms:.0f} мс превышает предел {max_latency_ms:.0f} мс"
        )

    expected_extraction = case.get("expected_extraction") or {}
    parsed = (
        (agent_response or {}).get("parsed_query")
        or route_response.get("parsed_query")
    )
    extraction_checked = bool(expected_extraction and isinstance(parsed, dict))
    extraction_ok = True
    if extraction_checked:
        for key, expected in expected_extraction.items():
            actual = _nested_value(parsed, key)
            if not _contains_expected(actual, expected):
                extraction_ok = False
                issues.append(f"извлечение {key}: {actual!r}, ожидалось {expected!r}")

    passed = all(
        (
            route_ok,
            intent_ok,
            tools_ok,
            sources_ok,
            warning_ok,
            review_ok,
            latency_ok,
            extraction_ok,
        )
    )
    return CaseResult(
        case_id=str(case["case_id"]),
        query=str(case["query"]),
        passed=passed,
        route_ok=route_ok,
        intent_ok=intent_ok,
        tools_ok=tools_ok,
        sources_ok=sources_ok,
        warning_ok=warning_ok,
        review_ok=review_ok,
        latency_ok=latency_ok,
        extraction_checked=extraction_checked,
        extraction_ok=extraction_ok,
        latency_ms=round(latency_ms, 2),
        issues=issues,
    )


def run_case(post_json: PostJson, case: dict[str, Any]) -> CaseResult:
    """Run one case through /route and, when needed, through /agent."""
    started = time.perf_counter()
    route_response = post_json("/route", {"query": case["query"]}, 30)
    agent_response = None
    if route_response.get("route") == "agent" or case.get("run_agent"):
        agent_response = post_json("/agent", {"query": case["query"]}, 200)
    latency_ms = (time.perf_counter() - started) * 1000
    return evaluate_responses(case, route_response, agent_response, latency_ms)


def build_report(results: Iterable[CaseResult]) -> dict[str, Any]:
    rows = list(results)
    total = len(rows)
    passed = sum(result.passed for result in rows)
    extraction_checked = sum(result.extraction_checked for result in rows)
    latencies = sorted(result.latency_ms for result in rows)
    p95_index = max(0, int(len(latencies) * 0.95) - 1) if latencies else 0
    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "extraction_checked": extraction_checked,
            "mean_latency_ms": round(sum(latencies) / total, 2) if total else 0.0,
            "p95_latency_ms": latencies[p95_index] if latencies else 0.0,
        },
        "cases": [asdict(result) for result in rows],
    }
