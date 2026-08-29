# repository/providers/neo4j_provider.py
"""Провайдер графа объекта (Neo4j) с fallback на pipeline_edges (PostgreSQL).

Формат результата совпадает с JSON-графом (data/graph/gas_pipeline_object.json):
    {"units": [{"unit_id", "name", "medium_code", "synthetic"}],
     "components": [{"component_id", "unit_id", "ksm_code", "installed_card_id",
                     "item_type", "designation", "operating_medium",
                     "compatibility_status", "expert_review_required"}]}

Цепочка провайдеров: Neo4j → pipeline_edges (PG) → None (JSON-fallback выше).
"""

import logging
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("mtr.repository.neo4j")

UNIT_CYPHER = (
    "MATCH (u:Unit) RETURN u.unit_id AS unit_id, u.name AS name, "
    "u.medium_code AS medium_code, u.synthetic AS synthetic"
)
COMPONENT_CYPHER = (
    "MATCH (c:Component) RETURN c.component_id AS component_id, "
    "c.unit_id AS unit_id, c.ksm_code AS ksm_code, "
    "c.installed_card_id AS installed_card_id, c.item_type AS item_type, "
    "c.designation AS designation, c.operating_medium AS operating_medium, "
    "c.compatibility_status AS compatibility_status, "
    "c.expert_review_required AS expert_review_required"
)


def _row_to_comp(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "component_id": row.get("component_id"),
        "unit_id": row.get("unit_id"),
        "ksm_code": row.get("ksm_code"),
        "installed_card_id": row.get("installed_card_id"),
        "item_type": row.get("item_type", ""),
        "designation": row.get("designation"),
        "operating_medium": row.get("operating_medium"),
        "compatibility_status": row.get("compatibility_status"),
        "expert_review_required": bool(row.get("expert_review_required", False)),
    }


class Neo4jGraphProvider:
    """Граф объекта из Neo4j; при недоступности — pipeline_edges из PG."""

    def __init__(
        self,
        card_lookup: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        access_logger: Optional[Any] = None,
    ):
        self._card_lookup = card_lookup
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        self._access_logger = access_logger

    # ---------------------------------------------------------------- conn
    def _get_driver(self):
        if self._driver is not None:
            return self._driver
        from app.config import settings
        from neo4j import GraphDatabase

        uri = self._uri or settings.NEO4J_URI
        user = self._user or settings.NEO4J_USER
        password = self._password or settings.NEO4J_PASSWORD
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            return self._driver
        except Exception as e:
            log.warning("Neo4jGraphProvider: недоступен (%s), fallback на pipeline_edges", e)
            self._driver = None
            return None

    def _log(self, method: str, provider: str, fallback: bool, reason: Optional[str] = None) -> None:
        if self._access_logger is not None:
            try:
                self._access_logger.record(
                    method_name=method,
                    provider_used=provider,
                    fallback_used=fallback,
                    fallback_reason=reason,
                )
            except Exception:
                pass

    # ---------------------------------------------------------------- API
    def graph(self) -> Optional[Dict[str, Any]]:
        units = self._query_units()
        if units is not None:
            comps = self._query_components()
            if comps is not None:
                self._log("get_graph", "neo4j", fallback=False)
                return {
                    "schema_version": 1,
                    "units": units,
                    "components": comps,
                }

        result = self._graph_from_pipeline_edges()
        if result is not None:
            self._log("get_graph", "postgresql", fallback=True, reason="neo4j недоступен/пуст")
            return result

        self._log("get_graph", "json", fallback=True, reason="neo4j и pipeline_edges отсутствуют")
        return None

    def components_by_unit(self, unit_id: str) -> Optional[List[Dict[str, Any]]]:
        driver = self._get_driver()
        if driver is not None:
            try:
                with driver.session() as session:
                    records = session.run(
                        "MATCH (c:Component) WHERE c.unit_id = $unit "
                        "RETURN properties(c) AS comp",
                        unit=unit_id,
                    ).data()
                comps = [_row_to_comp(r["comp"]) for r in records]
                if comps:
                    self._log("get_components_by_unit", "neo4j", fallback=False)
                    return comps
            except Exception as e:
                log.warning("Neo4j components_by_unit failed: %s", e)

        fallback = self.graph()
        if fallback is None:
            return None
        by_unit = [
            c
            for c in fallback.get("components", [])
            if c.get("unit_id") == unit_id
        ]
        return by_unit or None

    # ------------------------------------------------------------ queries
    def _query_units(self) -> Optional[List[Dict[str, Any]]]:
        driver = self._get_driver()
        if driver is None:
            return None
        try:
            with driver.session() as session:
                records = session.run(UNIT_CYPHER).data()
            if not records:
                return None
            return [
                {
                    "unit_id": r.get("unit_id"),
                    "name": r.get("name"),
                    "medium_code": r.get("medium_code"),
                    "synthetic": bool(r.get("synthetic", False)),
                }
                for r in records
            ]
        except Exception as e:
            log.warning("Neo4j units query failed: %s", e)
            return None

    def _query_components(self) -> Optional[List[Dict[str, Any]]]:
        driver = self._get_driver()
        if driver is None:
            return None
        try:
            with driver.session() as session:
                records = session.run(COMPONENT_CYPHER).data()
            if records:
                return [_row_to_comp(r) for r in records]
            # пустой граф: отсутствие узлов не ошибка, но и не источник
            return None
        except Exception as e:
            log.warning("Neo4j components query failed: %s", e)
            return None

    # ------------------------------------------------ pipeline_edges fallback
    def _graph_from_pipeline_edges(self) -> Optional[Dict[str, Any]]:
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import PipelineEdge

            db = SessionLocal()
            try:
                rows = db.query(PipelineEdge).all()
            finally:
                db.close()

            if not rows:
                return None

            units_map: Dict[str, int] = {}
            comps: List[Dict[str, Any]] = []
            seen: set = set()
            for e in rows:
                unit_code = e.unit_code
                if unit_code:
                    units_map.setdefault(unit_code, 0)
                for ksm in (e.from_ksm, e.to_ksm):
                    if ksm in seen:
                        continue
                    seen.add(ksm)
                    card = self._card_lookup(ksm) if self._card_lookup else None
                    comps.append(
                        {
                            "component_id": f"PG-EDGE-{len(comps) + 1:03d}",
                            "unit_id": unit_code,
                            "ksm_code": ksm,
                            "installed_card_id": (card or {}).get("card_id"),
                            "item_type": (card or {}).get("item_type", ""),
                            "designation": (card or {}).get("name"),
                            "operating_medium": None,
                            "compatibility_status": "confirmed",
                            "expert_review_required": False,
                        }
                    )

            if not comps:
                return None
            units = [
                {"unit_id": u, "name": u, "medium_code": "natural_gas", "synthetic": False}
                for u in units_map
            ]
            return {"schema_version": 1, "units": units, "components": comps}
        except Exception as e:
            log.warning("pipeline_edges fallback failed: %s", e)
            return None

    def close(self) -> None:
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                pass
            self._driver = None
