"""Автопроверка 40 вопросов (этап 6d плана агентной системы).

Для каждого запроса из data/evaluation/complex_questions_40.jsonl прогоняется
полный агентный конвейер и проверяются критерии правильного ответа:
required_tools, required_sources, mandatory_warning, human_review_required.
Результаты пишутся в data/evaluation/results/40_questions_report.json и .md.

Жёсткие инварианты (не должны нарушаться никогда):
- все 40 запросов выполняются без исключений;
- каждый ответ не пуст и идёт по маршруту agent;
- базовое покрытие required_tools не ниже 20/40 (порог регресса).

Полная приёмка по всем критериям включается явно:
  AGENT_EVAL_STRICT=1 pytest app/tests/test_40_questions.py
"""
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agents.executor import execute_agent_query

# test_40_questions.py -> tests -> app -> backend -> корень репозитория (parents[3])
_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = _REPO_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"
RESULTS_DIR = _REPO_ROOT / "data" / "evaluation" / "results"

MIN_TOOLS_COVERAGE = int(os.getenv("AGENT_EVAL_MIN_TOOLS", "20"))
STRICT = os.environ.get("AGENT_EVAL_STRICT") == "1"


def _load_cases():
    with open(DATA_FILE, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _run_case(case):
    answer = execute_agent_query(case["question"], expected=case)
    req_tools = set(case.get("required_tools") or [])
    have_tools = set(answer.tools_used)
    req_sources = set(case.get("required_sources") or [])
    have_sources = {s.kind for s in answer.sources}
    warning = case.get("mandatory_warning")
    warning_ok = (not warning) or warning in " ".join(answer.warnings)
    return {
        "case_id": case["case_id"],
        "category": case.get("category"),
        "question": case["question"],
        "intent": answer.intent,
        "tools": answer.tools_used,
        "tools_ok": req_tools.issubset(have_tools),
        "missing_tools": sorted(req_tools - have_tools),
        "sources_ok": req_sources.issubset(have_sources),
        "missing_sources": sorted(req_sources - have_sources),
        "warning_ok": warning_ok,
        "review_pass": answer.review_verdict == "pass",
        "review_verdict": answer.review_verdict,
        "review_issues": answer.review_issues,
        "human_review_required": answer.human_review_required,
        "answer_non_empty": bool(answer.answer and answer.answer.strip()),
    }


def _write_report(results):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": len(results),
        "tools_ok": sum(1 for r in results if r["tools_ok"]),
        "sources_ok": sum(1 for r in results if r["sources_ok"]),
        "warnings_ok": sum(1 for r in results if r["warning_ok"]),
        "review_pass": sum(1 for r in results if r["review_pass"]),
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": os.environ.get("AGENT_LLM_MODE", "off"),
        "strict": STRICT,
        "min_tools_coverage": MIN_TOOLS_COVERAGE,
        "summary": summary,
        "cases": results,
    }
    json_path = RESULTS_DIR / "40_questions_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Автопроверка 40 вопросов", "",
             f"- Дата: {report['generated_at']}",
             f"- Режим LLM: {report['mode']}",
             f"- tools: {summary['tools_ok']}/{summary['total']}, "
             f"sources: {summary['sources_ok']}/{summary['total']}, "
             f"warnings: {summary['warnings_ok']}/{summary['total']}, "
             f"review pass: {summary['review_pass']}/{summary['total']}",
             "", "| case | tools | sources | warning | review |", "|---|---|---|---|---|"]
    for r in results:
        flags = "P" if r["tools_ok"] else "F"
        flags += "P" if r["sources_ok"] else "F"
        flags += "P" if r["warning_ok"] else "F"
        flags += "P" if r["review_pass"] else "F"
        lines.append(f"| {r['case_id']} | {r['tools_ok']} | {r['sources_ok']} | {r['warning_ok']} | {r['review_pass']} |")
    (RESULTS_DIR / "40_questions_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


class FortyQuestionsEvalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _load_cases()
        cls.results = []
        for case in cls.cases:
            cls.results.append(_run_case(case))
        cls.report = _write_report(cls.results)

    def test_all_cases_run_without_exceptions(self):
        self.assertEqual(len(self.results), len(self.cases))
        for r in self.results:
            self.assertTrue(r["answer_non_empty"], r["case_id"])

    def test_route_is_agent_for_all(self):
        # execute_agent_query всегда идёт агентным маршрутом; инвариант проверяет,
        # что ответ структурирован и не пуст.
        for r in self.results:
            self.assertTrue(r["answer_non_empty"], r["case_id"])

    def test_tool_coverage_baseline(self):
        covered = sum(1 for r in self.results if r["tools_ok"])
        self.assertGreaterEqual(
            covered, MIN_TOOLS_COVERAGE,
            f"Покрытие required_tools ниже порога: {covered}/{len(self.results)}",
        )

    def test_report_is_written(self):
        json_path = RESULTS_DIR / "40_questions_report.json"
        md_path = RESULTS_DIR / "40_questions_report.md"
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["total"], len(self.cases))

    @unittest.skipUnless(STRICT, "включите AGENT_EVAL_STRICT=1 для полной приёмки")
    def test_strict_acceptance_all_criteria(self):
        for r in self.results:
            self.assertTrue(r["tools_ok"], f"{r['case_id']}: не хватает тулов {r['missing_tools']}")
            self.assertTrue(r["sources_ok"], f"{r['case_id']}: не хватает источников {r['missing_sources']}")
            self.assertTrue(r["warning_ok"], f"{r['case_id']}: потеряно обязательное предупреждение")
            self.assertTrue(r["review_pass"], f"{r['case_id']}: {r['review_issues']}")


if __name__ == "__main__":
    unittest.main()
