"""Sub-этап 9: прогон 40 вопросов в режиме auto (quality gate).

Запуск (без LLM — детерминированный проход + verifier):
  python app/scripts/eval_40_auto.py

Для замера с LLM-refine нужен доступный LLM (LLMClient). При его отсутствии
скрипт фиксирует escalation_skipped_no_llm, как и fallback в executor.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # backend/

from app.services.agent.core.config import AgentConfig  # noqa: E402
from app.services.agent.executor import AgentExecutor  # noqa: E402

_LOG = logging.getLogger("eval.auto")
logging.basicConfig(level=logging.WARNING)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = _REPO_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"
RESULTS_DIR = _REPO_ROOT / "data" / "evaluation" / "results"
OUT_JSON = RESULTS_DIR / "40_questions_auto_report.json"
OUT_MD = RESULTS_DIR / "40_questions_auto_report.md"


def _load_cases():
    with open(DATA_FILE, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _sufficiency_verdicts(answer) -> list:
    out = []
    for c in answer.components or []:
        st = (c.status or "").lower()
        if any(k in st for k in ("хватает", "не хватает", "дефицит", "потребность", "остаток")):
            out.append(c.status)
    return out


def _run_case(case, mode: str):
    cfg = AgentConfig(use_llm=(mode == "auto_llm"), storage="json")
    ex = AgentExecutor(cfg)
    start = time.time()
    answer = ex.execute(case["question"], mode=mode)
    ms = (time.time() - start) * 1000

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
        "verification_verdict": answer.verification_verdict,
        "verification_reasons": list(answer.verification_reasons or []),
        "escaped": len(answer.verification_reasons or []) > 0,
        "mode_refined": answer.mode_refined,
        "llm_refine_failed": answer.llm_refine_failed,
        "human_review_required": answer.human_review_required,
        "review_verdict": answer.review_verdict,
        "sufficiency_verdicts": _sufficiency_verdicts(answer),
        "tools": answer.tools_used,
        "tools_ok": req_tools.issubset(have_tools),
        "missing_tools": sorted(req_tools - have_tools),
        "sources_ok": req_sources.issubset(have_sources),
        "missing_sources": sorted(req_sources - have_sources),
        "warning_ok": warning_ok,
        "duration_ms": round(ms, 1),
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if mode not in ("auto", "auto_llm"):
        print(f"usage: {sys.argv[0]} [auto|auto_llm]")
        return 1

    cases = _load_cases()
    results = [_run_case(c, mode) for c in cases]

    total = len(results)
    esc = [r for r in results if r["escaped"]]
    pass_ = [r for r in results if r["verification_verdict"] == "pass"]
    review = [r for r in results if r["verification_verdict"] == "review"]
    tools_ok = [r for r in results if r["tools_ok"]]
    sources_ok = [r for r in results if r["sources_ok"]]
    sufficiency = [r for r in results if r["sufficiency_verdicts"]]

    gap_type_counter: dict = {}
    for r in esc:
        for reason in r["verification_reasons"]:
            tag = reason.split("]")[-1].split(":")[0].strip() if "]" in reason else reason
            gap_type_counter[tag] = gap_type_counter.get(tag, 0) + 1

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "total": total,
        "verdict_pass": len(pass_),
        "verdict_review": len(review),
        "escaped": len(esc),
        "escape_rate_pct": round(100 * len(esc) / total, 1),
        "tools_ok": len(tools_ok),
        "sources_ok": len(sources_ok),
        "sufficiency_verdict_cases": len(sufficiency),
        "avg_duration_ms": round(sum(r["duration_ms"] for r in results) / total, 1),
        "gap_by_type": dict(sorted(gap_type_counter.items(), key=lambda x: -x[1])),
    }

    report = {"summary": summary, "mode": mode, "cases": results}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / OUT_JSON.name).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Eval 40 вопросов в auto-режиме (quality gate)", "",
        f"- Дата: {summary['generated_at']}",
        f"- Режим: {mode}",
        f"- Total: {summary['total']}",
        f"- verdict PASS: {summary['verdict_pass']} / REVIEW: {summary['verdict_review']}",
        f"- Эскалаций (REVIEW): {summary['escaped']} ({summary['escape_rate_pct']}%)",
        f"- tools OK: {summary['tools_ok']}/{summary['total']}",
        f"- sources OK: {summary['sources_ok']}/{summary['total']}",
        f"- кейсов с sufficiency-verdict: {summary['sufficiency_verdict_cases']}",
        f"- avg duration: {summary['avg_duration_ms']} ms",
        "",
        "## Распределение gap-типов (reason)", "",
    ]
    for tag, cnt in summary["gap_by_type"].items():
        lines.append(f"- {tag}: {cnt}")
    lines += ["", "## По кейсам", "", "| case | cat | verdict | esc | sufficiency | tools | sources | ms |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        sf = "Y" if r["sufficiency_verdicts"] else "-"
        lines.append(
            f"| {r['case_id']} | {r['category']} | {r['verification_verdict']} "
            f"| {'Y' if r['escaped'] else '-'} | {sf} "
            f"| {'P' if r['tools_ok'] else 'F'} | {'P' if r['sources_ok'] else 'F'} | {r['duration_ms']} |"
        )
    (RESULTS_DIR / OUT_MD.name).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nОтчёт: {OUT_JSON} / {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
