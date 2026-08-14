"""Command-line black-box evaluation for a running MTR agent backend."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests

from frontend.agent_quality import build_report, load_cases, run_case


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data" / "evaluation" / "agent_stress_cases_50.jsonl"


class ApiCallError(RuntimeError):
    pass


def make_post_json(base_url: str):
    base_url = base_url.rstrip("/")

    def post_json(path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{base_url}{path}",
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ApiCallError(f"Не удалось вызвать {path}: {exc}") from exc
        if not response.ok:
            raise ApiCallError(
                f"{path} вернул HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ApiCallError(f"{path} вернул не JSON") from exc

    return post_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Проверка /route и /agent на 50 стресс-запросах"
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        "--backend-url",
        default=os.getenv("MTR_BACKEND_URL", "http://localhost:8000"),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]

    post_json = make_post_json(args.backend_url)
    results = []
    for case in cases:
        try:
            result = run_case(post_json, case)
        except ApiCallError as exc:
            print(f"{case['case_id']}: ERROR - {exc}")
            continue
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        detail = "; ".join(result.issues) if result.issues else "ok"
        print(f"{result.case_id}: {status} - {detail}")

    report = build_report(results)
    summary = report["summary"]
    print(
        "\nИтого: "
        f"{summary['passed']}/{summary['total']} пройдено, "
        f"среднее {summary['mean_latency_ms']} мс, "
        f"p95 {summary['p95_latency_ms']} мс"
    )
    if summary["extraction_checked"] == 0:
        print(
            "Извлечённая карточка пока не проверялась: backend ещё не возвращает "
            "parsed_query в /route или /agent."
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Отчёт: {args.output}")
    return 0 if summary["failed"] == 0 and summary["total"] == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
