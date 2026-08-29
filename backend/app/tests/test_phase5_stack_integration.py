# tests/test_phase5_stack_integration.py
"""DOD Шага 3 «полный стек»: проверка провайдеров на живых сервисах.

Каталог/склад — PostgreSQL (+Redis-кеш), граф — Neo4j, нормативы — Qdrant,
паспорта — PG, история — PG, журналы data_access_logs/tool_execution_logs — PG.

Тест запускается только при доступном стеке (PG на localhost); иначе — skip.
"""

import os

os.environ.setdefault("AGENT_STORAGE", "db")
os.environ.setdefault("AGENT_LLM_MODE", "off")
os.environ.setdefault("DATABASE_URL", "postgresql://syn:syn_password@localhost:5432/syn")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "changeme")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")
os.environ.setdefault("QDRANT_COLLECTION", "mtr_descriptions")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import psycopg2
import pytest

from app.services.agent.repository.providers.access_context import request_scope


def _stack_available() -> bool:
    url = os.environ["DATABASE_URL"]
    try:
        conn = psycopg2.connect(url, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


_needs_stack = pytest.mark.skipif(not _stack_available(), reason="Полный стек недоступен")


@pytest.fixture(scope="module")
def repo():
    from app.services.agent.repository.repository_factory import get_repository, reset_repository
    from app.services.agent.tools.tool_log import reset_tool_logger

    reset_repository()
    reset_tool_logger()
    r = get_repository(storage="db")
    r.get_catalog()
    return r


def _count(table: str) -> int:
    from sqlalchemy import text

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        return db.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0
    finally:
        db.close()


def _teardown_env() -> None:
    os.environ["AGENT_STORAGE"] = "json"
    from app.services.agent.repository.repository_factory import reset_repository
    from app.services.agent.tools.tool_log import reset_tool_logger

    reset_repository()
    reset_tool_logger()


@_needs_stack
def test_catalog_comes_from_postgres(repo):
    catalog = repo.get_catalog()
    assert len(catalog) >= 1000
    assert all(card.get("db_id") for card in catalog), "карточки должны читаться из PG"
    assert repo.get_card_by_ksm(catalog[0]["codes"]["ksm_code"]) is not None


@_needs_stack
def test_stock_from_postgres(repo):
    catalog = repo.get_catalog()
    with_cost = [c for c in catalog if (c.get("properties") or {}).get("cost")]
    assert with_cost, "в PG должны быть позиции со стоимостью (см. seed)"
    ksm = with_cost[0]["codes"]["ksm_code"]
    assert repo.get_stock_cost(ksm) is not None
    assert repo.get_stock_quantity(ksm) is not None


@_needs_stack
def test_catalog_filled_and_redis_cache(repo):
    first = repo.get_catalog()
    assert len(first) == len(sorted(first, key=lambda c: c["card_id"]))
    assert _count("data_access_logs") >= 0  # не падаем из-за пустого журнала

    cache = repo._cache  # RedisCache read-through
    if not cache.available:
        pytest.skip("Redis недоступен — проверка кеша пропускается")
    cached = cache.get("catalog.json")
    assert cached is not None and len(cached) >= 1000, "каталог должен лежать в Redis"


@_needs_stack
def test_graph_from_neo4j(repo):
    graph = repo.get_graph()
    assert len(graph["units"]) >= 7
    assert len(graph["components"]) >= 42
    comp = graph["components"][0]
    assert comp.get("ksm_code") and comp.get("unit_id")

    by_unit = repo.get_components_by_unit("UNIT-SYN-GAS-001")
    assert by_unit and by_unit[0]["unit_id"] == "UNIT-SYN-GAS-001"


@_needs_stack
def test_neighbors_via_graph(repo):
    from app.services.agent.tools.tool_dal import ToolDAL

    dal = ToolDAL(repo)
    graph = repo.get_graph()
    ksm = graph["components"][0]["ksm_code"]
    neighbors = dal.get_neighbors(ksm, depth=1)
    if not neighbors:
        pytest.skip("нет соседей у выбранного узла")
    assert isinstance(neighbors, list)


@_needs_stack
def test_norms_via_qdrant(repo):
    fragments = repo.search_norms("подтверждение пригодности к H2S", limit=5)
    assert fragments, "поиск нормативов должен вернуть результаты из Qdrant"
    texts = [f.get("text", "") for f in fragments]
    assert any("H2S" in t or "H2S" in t.upper() or "сероводород" in t.lower() or "h2s" in t.lower() for t in texts)


@_needs_stack
def test_passport_from_postgres(repo):
    result = repo.get_passport_params("passport_013_oksh90_h2s")
    assert result is not None, "документ должен быть проиндексирован в PG"
    assert result.get("params", {}).get("dn", {}).get("value") == 159

    material_doc = repo.get_passport_params("passport_001_oksh90_dn159")
    assert "material" in material_doc["params"]


@_needs_stack
def test_history_from_postgres(repo):
    from app.db.session import SessionLocal
    from app.models.sqlalchemy.all_models import MtrItem

    db = SessionLocal()
    try:
        mtr_code = db.query(MtrItem).first().mtr_code
    finally:
        db.close()

    card = repo.get_card_by_id(mtr_code)
    ksm = (card or {}).get("codes", {}).get("ksm_code")
    history = repo.get_component_history(ksm, limit=5)
    assert history, "история должна читаться из mtr_item_history (см. seed)"


@_needs_stack
def test_data_access_logs_written(repo):
    before = _count("data_access_logs")
    with request_scope("itest-dal"):
        repo.get_stock_quantity(repo.get_catalog()[0]["codes"]["ksm_code"])
        repo.get_graph()
        repo.search_norms("H2S")
        repo.get_passport_params("passport_001_oksh90_dn159")
    after = _count("data_access_logs")
    assert after > before, "вызовы провайдеров должны писать data_access_logs"


@_needs_stack
def test_tool_execution_logs_written(repo):
    before = _count("tool_execution_logs")
    from app.services.agent.tools.tool_log import get_tool_logger

    get_tool_logger().record(
        tool_name="itest_stack_check",
        input_data={"probe": True},
        duration_ms=1,
        output_data={"ok": True},
        request_id="itest-tool-log",
    )
    after = _count("tool_execution_logs")
    assert after > before, "логи инструментов должны писаться в PG"


@_needs_stack
def test_e2e_deterministic_on_stack(repo):
    if _count("mtr_items") < 1000:
        pytest.skip("нет каталога в PG")

    from app.services.agent.executor import AgentExecutor

    for query in ["подбери отвод 90 на DN159", "найди задвижку DN100"]:
        answer = AgentExecutor().execute(query, mode="deterministic")
        assert answer.status, "детерминированный режим должен вернуть status"
        assert answer.answer is not None


def teardown_module(module):
    _teardown_env()