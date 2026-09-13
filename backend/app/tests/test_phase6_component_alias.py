# tests/test_phase6_component_alias.py
"""Фаза 6: узел ComponentAlias (COMP-SYN-XXX -> KSM) и индексы графа.

Тест работает без живого Neo4j: проверяются чистая функция маппинга
и состав schema-стейтментов, которые сеют оба скрипта
(seed_stack.seed_graph и GEN/generate_graph_neo4j).
"""

import json
from pathlib import Path

from app.scripts.seed_stack import GRAPH_SCHEMA_STATEMENTS, _object_graph_aliases

REPO_ROOT = Path(__file__).parents[3]
OBJECT_GRAPH_PATH = REPO_ROOT / "data" / "graph" / "gas_pipeline_object.json"


def _load_object_graph() -> dict:
    return json.loads(OBJECT_GRAPH_PATH.read_text(encoding="utf-8"))


def test_alias_rows_map_object_graph():
    graph = _load_object_graph()
    aliases = _object_graph_aliases(graph)

    assert aliases, "должен быть хотя бы один COMP-SYN alias"
    assert len(aliases) == len(graph["components"])

    by_comp = {a["comp_id"]: a for a in aliases}
    for c in graph["components"]:
        assert c["component_id"] in by_comp
        alias = by_comp[c["component_id"]]
        assert alias["ksm_code"] == c["ksm_code"]
        assert alias["unit_code"] == c["unit_id"]
        assert c["ksm_code"].startswith("KSM-SYN-")


def test_alias_rows_comp_id_unique():
    aliases = _object_graph_aliases(_load_object_graph())
    comp_ids = [a["comp_id"] for a in aliases]
    assert len(comp_ids) == len(set(comp_ids))


def test_alias_rows_skip_missing_keys():
    graph = {
        "components": [
            {"component_id": "COMP-MISSING-KSM", "unit_id": "U1"},
            {"ksm_code": "KSM-MISSING-ID", "unit_id": "U2"},
            {"component_id": "COMP-GOOD", "ksm_code": "KSM-GOOD", "unit_id": "U3"},
        ]
    }
    aliases = _object_graph_aliases(graph)
    assert len(aliases) == 1
    assert aliases[0] == {"comp_id": "COMP-GOOD", "ksm_code": "KSM-GOOD", "unit_code": "U3"}


def test_schema_statements_complete():
    stmts = GRAPH_SCHEMA_STATEMENTS
    assert any(
        "ComponentAlias" in s and "comp_id" in s and "IS UNIQUE" in s for s in stmts
    ), "должен быть constraint comp_id IS UNIQUE для ComponentAlias"
    assert any("ON (c.item_type)" in s for s in stmts), "должен быть индекс по item_type"
    assert any("ON (c.dn)" in s for s in stmts), "должен быть индекс по dn"
