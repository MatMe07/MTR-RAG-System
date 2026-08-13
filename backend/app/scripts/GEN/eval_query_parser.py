"""eval_query_parser.py - бенчмарк точности query_parser.

Запуск:
    PYTHONPATH=app python3 -m app.scripts.GEN.eval_query_parser [--cases PATH ...]

Прогоняет все наборы кейсов из data/evaluation/ (по умолчанию
parser_cases.jsonl и complex_intent_cases.jsonl), сравнивает ожидаемые поля
с фактическими и пишет отчёт в stdout и в data/evaluation/results/parser_baseline.json.

Типы полей:
  - card-поля (scalar): из parsed.card
  - list-поля (operations, item_types, component_ids, unit_ids): сравнение множеств
  - dict-поля (stock_filters, proposed_changes): сравнение по ключам expected
"""

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve()
BACKEND_APP = SCRIPT_DIR.parents[2]
ROOT = BACKEND_APP.parent.parent
sys.path.insert(0, str(BACKEND_APP))

from app.services.query_parser import QueryParser  # noqa: E402

CARD_GETTERS = {
    "item_type": lambda c: c.item_type,
    "subtype": lambda c: c.subtype,
    "designation": lambda c: c.designation,
    "dn": lambda c: c.geometry.dn if c.geometry else None,
    "d1": lambda c: c.geometry.d1 if c.geometry else None,
    "d2": lambda c: c.geometry.d2 if c.geometry else None,
    "angle": lambda c: c.geometry.angle if c.geometry else None,
    "wall_thickness": lambda c: c.geometry.wall_thickness if c.geometry else None,
    "pn": lambda c: c.pressure.pn if c.pressure else None,
    "steel_grade": lambda c: c.material.steel_grade if c.material else None,
    "strength_class": lambda c: c.material.strength_class if c.material else None,
    "medium": lambda c: c.environment.medium if c.environment else None,
    "h2s_confirmed": lambda c: c.environment.h2s_confirmed if c.environment else None,
    "co2_confirmed": lambda c: c.environment.co2_confirmed if c.environment else None,
    "temperature_min_c": lambda c: c.environment.temperature_min_c if c.environment else None,
    "climate_version": lambda c: c.environment.climate_version if c.environment else None,
}

LIST_GETTERS = {
    "operations": lambda p: list(p.operations or []),
    "item_types": lambda p: list(p.item_types or []),
    "component_ids": lambda p: list(p.component_ids or []),
    "unit_ids": lambda p: list(p.unit_ids or []),
}

DICT_GETTERS = {
    "stock_filters": lambda p: dict(p.stock_filters or {}),
    "proposed_changes": lambda p: dict(p.proposed_changes or {}),
}

SCALAR_GETTERS = {
    "units_count": lambda p: p.units_count,
    "length_m": lambda p: p.length_m,
    "limit": lambda p: p.limit,
    "timeframe": lambda p: p.timeframe,
    "urgency": lambda p: p.urgency,
    "sort_by": lambda p: p.sort_by,
    "on_stock": lambda p: p.on_stock,
    "not_installed": lambda p: p.not_installed,
}


def scalar_equal(expected, got):
    if isinstance(expected, bool) or isinstance(got, bool):
        return bool(expected) == bool(got)
    if isinstance(expected, (int, float)) and isinstance(got, (int, float)):
        return abs(float(expected) - float(got)) < 1e-6
    if expected is None or got is None:
        return expected is None and got is None
    return str(expected).strip().lower() == str(got).strip().lower()


def list_equal(expected, got):
    return set(expected or []) == set(got or [])


def dict_equal(expected, got):
    got = got or {}
    for key, exp_val in expected.items():
        if key not in got:
            return False
        if isinstance(exp_val, (int, float)) and isinstance(got.get(key), (int, float)):
            if abs(float(exp_val) - float(got.get(key))) >= 1e-6:
                return False
        elif not scalar_equal(exp_val, got.get(key)):
            return False
    return True


def compare(expected, got):
    if isinstance(expected, list):
        return list_equal(expected, got)
    if isinstance(expected, dict):
        return dict_equal(expected, got)
    return scalar_equal(expected, got)


class _EmptyCard:
    def __getattr__(self, name):
        return None


def get_field_value(parsed, field):
    if field in CARD_GETTERS:
        card = parsed.card
        if card is None:
            card = _EmptyCard()
        return CARD_GETTERS[field](card)
    if field in LIST_GETTERS:
        return LIST_GETTERS[field](parsed)
    if field in DICT_GETTERS:
        return DICT_GETTERS[field](parsed)
    if field in SCALAR_GETTERS:
        return SCALAR_GETTERS[field](parsed)
    return None


def evaluate(parser, cases, parser_name):
    field_stats = {f: {"ok": 0, "checked": 0, "fail": []}
                   for f in list(CARD_GETTERS) + list(LIST_GETTERS) + list(DICT_GETTERS) + list(SCALAR_GETTERS)}
    case_results = []
    latencies = []
    for case in cases:
        t0 = time.perf_counter()
        try:
            parsed = parser.parse(case["query"])
        except Exception as e:
            case_results.append({"case_id": case["case_id"], "ok": False,
                                 "error": "%s: %s" % (type(e).__name__, str(e)[:100])})
            continue
        latencies.append(time.perf_counter() - t0)
        failures = []
        for field, expected in case.get("expected", {}).items():
            if expected is None or field not in field_stats:
                continue
            got = get_field_value(parsed, field)
            stat = field_stats[field]
            stat["checked"] += 1
            if compare(expected, got):
                stat["ok"] += 1
            else:
                stat["fail"].append(case["case_id"])
                failures.append({"field": field, "expected": expected, "got": got})
        case_results.append({"case_id": case["case_id"], "query": case["query"][:60],
                             "note": case.get("note", ""), "ok": not failures,
                             "failures": failures})
    n = len(cases)
    ok_cases = sum(1 for r in case_results if r["ok"])
    return {
        "parser": parser_name,
        "cases_total": n,
        "cases_ok": ok_cases,
        "case_accuracy": ok_cases / n if n else 0.0,
        "field_stats": {f: {"accuracy": (s["ok"] / s["checked"] if s["checked"] else None),
                            "checked": s["checked"], "ok": s["ok"],
                            "fail_cases": s["fail"]}
                        for f, s in field_stats.items()},
        "mean_latency_ms": (sum(latencies) / len(latencies) * 1000) if latencies else None,
        "case_results": case_results,
    }


def print_report(report):
    print("=" * 70)
    print("PARSER BASELINE | %s | cases=%d ok=%d acc=%.3f"
          % (report["parser"], report["cases_total"], report["cases_ok"], report["case_accuracy"]))
    if report["mean_latency_ms"] is not None:
        print("mean latency: %.1f ms/query" % report["mean_latency_ms"])
    print("-" * 70)
    checked = [(f, s) for f, s in report["field_stats"].items() if s["checked"]]
    checked.sort(key=lambda fs: fs[1]["accuracy"])
    for f, s in checked:
        print("  %-18s acc=%.3f (%d/%d)" % (f, s["accuracy"], s["ok"], s["checked"]))
    print("-" * 70)
    for r in report["case_results"]:
        if not r["ok"]:
            print("  FAIL %s | %s (%s)" % (r["case_id"], r["query"], r.get("note", "")))
            for fl in r.get("failures", []):
                print("       %s: expected=%r got=%r" % (fl["field"], fl["expected"], fl["got"]))
    print("=" * 70)


def load_cases(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    default_cases = [str(ROOT / "data/evaluation/parser_cases.jsonl"),
                     str(ROOT / "data/evaluation/complex_intent_cases.jsonl")]
    ap.add_argument("--cases", nargs="+", default=default_cases)
    args = ap.parse_args()

    reports = []
    rule = QueryParser()
    for path in args.cases:
        if not Path(path).exists():
            print("Skipping missing: %s" % path)
            continue
        cases = load_cases(path)
        name = Path(path).stem
        print("Loaded %d cases from %s" % (len(cases), path))
        for parser, parser_label in ((rule, "query_parser (rule)"),
                                     (HybridParserOrNone(), "hybrid_parser")):
            if parser is None:
                continue
            report = evaluate(parser, cases, "%s / %s" % (parser_label, name))
            reports.append(report)
            print_report(report)

    out_path = ROOT / "data/evaluation/results/parser_baseline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Report written: %s" % out_path)


class HybridParserOrNone:
    """Ленивый враппер: гибридный парсер может быть недоступен (нет моделей natasha)."""

    def __init__(self):
        self._parser = None
        try:
            from app.services.query_parser import HybridParser
            self._parser = HybridParser()
        except Exception as e:
            print("HybridParser skipped: %s: %s" % (type(e).__name__, str(e)[:120]))

    def __bool__(self):
        return self._parser is not None

    def parse(self, query):
        return self._parser.parse(query)


if __name__ == "__main__":
    main()
