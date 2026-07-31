"""Evaluate ranked search output against the project golden dataset."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLDEN = REPO_ROOT / "data" / "sample" / "golden_dataset.csv"
DEFAULT_ASSERTIONS = REPO_ROOT / "data" / "evaluation" / "golden_assertions.jsonl"

DEFAULT_THRESHOLDS = {
    "top3_hit_rate": 0.70,
    "top20_hit_rate": 0.95,
    "exact_code_top1_rate": 0.95,
    "warning_coverage": 1.0,
    "explanation_coverage": 1.0,
    "source_coverage": 1.0,
}


def _normalize(value: Any) -> str:
    return str(value or "").lower().replace("ё", "е").strip()


def _contains_all(haystack: str, terms: Iterable[str]) -> bool:
    normalized = _normalize(haystack)
    return all(_normalize(term) in normalized for term in terms)


def load_golden(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Некорректный JSON в {path}, строка {line_number}: {error}"
                ) from error
    return records


def _rate(passed: int, total: int) -> float | None:
    return passed / total if total else None


def evaluate_cases(
    golden_cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
    assertions: list[dict[str, Any]],
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)

    result_by_id = {row["case_id"]: row for row in results}
    assertion_by_id = {row["case_id"]: row for row in assertions}

    retrieval_total = 0
    top1_passed = 0
    top3_passed = 0
    top20_passed = 0
    exact_total = 0
    exact_passed = 0
    warning_total = 0
    warning_passed = 0
    explanation_total = 0
    explanation_passed = 0
    source_total = 0
    source_passed = 0
    case_details = []

    for golden in golden_cases:
        case_id = golden["case_id"]
        result = result_by_id.get(case_id, {})
        assertion = assertion_by_id.get(case_id, {})
        ranked = list(result.get("ranked_mtr_codes") or [])
        expected_code = golden.get("expected_top1_mtr") or None

        top1_hit = top3_hit = top20_hit = None
        if expected_code:
            retrieval_total += 1
            top1_hit = expected_code in ranked[:1]
            top3_hit = expected_code in ranked[:3]
            top20_hit = expected_code in ranked[:20]
            top1_passed += int(top1_hit)
            top3_passed += int(top3_hit)
            top20_passed += int(top20_hit)

        exact_hit = None
        if assertion.get("exact_code_case"):
            exact_total += 1
            exact_hit = bool(expected_code and expected_code in ranked[:1])
            exact_passed += int(exact_hit)

        warning_terms = list(assertion.get("required_warning_terms") or [])
        warning_ok = None
        if warning_terms:
            warning_total += 1
            warnings_text = " ".join(str(item) for item in result.get("warnings") or [])
            warning_ok = _contains_all(warnings_text, warning_terms)
            warning_passed += int(warning_ok)

        explanation_terms = list(assertion.get("required_explanation_terms") or [])
        explanation_ok = None
        if explanation_terms:
            explanation_total += 1
            explanation_ok = _contains_all(
                str(result.get("explanation") or ""),
                explanation_terms,
            )
            explanation_passed += int(explanation_ok)

        required_sources = list(assertion.get("required_sources") or [])
        sources_ok = None
        if required_sources:
            source_total += 1
            actual_sources = set(result.get("sources") or [])
            sources_ok = all(source in actual_sources for source in required_sources)
            source_passed += int(sources_ok)

        case_details.append(
            {
                "case_id": case_id,
                "has_result": case_id in result_by_id,
                "top1_hit": top1_hit,
                "top3_hit": top3_hit,
                "top20_hit": top20_hit,
                "exact_code_top1": exact_hit,
                "warnings_ok": warning_ok,
                "explanation_ok": explanation_ok,
                "sources_ok": sources_ok,
            }
        )

    metrics = {
        "top1_hit_rate": _rate(top1_passed, retrieval_total),
        "top3_hit_rate": _rate(top3_passed, retrieval_total),
        "top20_hit_rate": _rate(top20_passed, retrieval_total),
        "exact_code_top1_rate": _rate(exact_passed, exact_total),
        "warning_coverage": _rate(warning_passed, warning_total),
        "explanation_coverage": _rate(explanation_passed, explanation_total),
        "source_coverage": _rate(source_passed, source_total),
    }
    passed = {
        metric: (value is not None and value >= limits[metric])
        for metric, value in metrics.items()
        if metric in limits
    }

    return {
        "counts": {
            "golden_cases": len(golden_cases),
            "received_results": len(result_by_id),
            "retrieval_cases": retrieval_total,
            "exact_code_cases": exact_total,
            "warning_cases": warning_total,
            "explanation_cases": explanation_total,
            "source_cases": source_total,
        },
        "metrics": metrics,
        "thresholds": limits,
        "passed": passed,
        "overall_passed": bool(passed) and all(passed.values()),
        "cases": case_details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Посчитать Top-3, Top-20 и качество объяснений."
    )
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--assertions", type=Path, default=DEFAULT_ASSERTIONS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate_cases(
        load_golden(args.golden),
        load_jsonl(args.results),
        load_jsonl(args.assertions),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
