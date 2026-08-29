# app/scripts/seed_stack.py
"""Загрузка данных «полного стека» (Шаг 3).

Наполняет реальные провайдеры данными из демо-источников:
  --graph     граф объекта                  -> Neo4j (Unit/Component) + pipeline_edges (PG)
  --norms     нормативные фрагменты         -> Qdrant (коллекция mtr_descriptions)
  --passports параметры паспортов           -> documents + extracted_characteristics (PG)
  --history   история изменений карточек    -> mtr_item_history (PG)

Пример (локальный стек, хосты localhost):
  DATABASE_URL=postgresql://syn:syn_password@localhost:5432/syn \
  NEO4J_URI=bolt://localhost:7687 QDRANT_HOST=localhost REDIS_URL=redis://localhost:6379/0 \
  python3 -m app.scripts.seed_stack --all
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.seed_stack")


def _repo_root() -> Path:
    return Path(__file__).parents[3]


def _load_json(rel: str) -> Dict[str, Any]:
    path = _repo_root() / rel
    if not path.exists():
        raise FileNotFoundError(f"нет данных: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ==================================================================== GRAPH
def seed_graph() -> int:
    graph = _load_json("data/graph/gas_pipeline_object.json")
    units = graph.get("units", [])
    components = graph.get("components", [])
    log.info("graph: %d units, %d components", len(units), len(components))

    from neo4j import GraphDatabase

    from app.config import settings

    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        for u in units:
            session.run(
                "MERGE (u:Unit {unit_id: $unit_id}) "
                "SET u.name = $name, u.medium_code = $medium_code, u.synthetic = $synthetic",
                unit_id=u["unit_id"],
                name=u.get("name"),
                medium_code=u.get("medium_code"),
                synthetic=bool(u.get("synthetic", False)),
            )
        for c in components:
            session.run(
                "MERGE (c:Component {component_id: $cid}) "
                "SET c.unit_id = $unit_id, c.ksm_code = $ksm, "
                "c.installed_card_id = $card, c.item_type = $itype, "
                "c.designation = $descr, c.operating_medium = $medium, "
                "c.compatibility_status = $status, "
                "c.expert_review_required = $review",
                cid=c["component_id"],
                unit_id=c.get("unit_id"),
                ksm=c.get("ksm_code"),
                card=c.get("installed_card_id"),
                itype=c.get("item_type", ""),
                descr=c.get("designation"),
                medium=c.get("operating_medium"),
                status=c.get("compatibility_status"),
                review=bool(c.get("expert_review_required", False)),
            )
    driver.close()
    log.info("graph -> Neo4j: готово")

    seed_pipeline_edges(components)
    return 0


def seed_pipeline_edges(components: List[Dict[str, Any]]) -> int:
    from app.db.session import SessionLocal
    from app.models.sqlalchemy.all_models import PipelineEdge

    db = SessionLocal()
    try:
        db.query(PipelineEdge).delete()
        edges = 0
        by_unit: Dict[str, List[Dict[str, Any]]] = {}
        for c in components:
            unit_id = c.get("unit_id")
            if unit_id:
                by_unit.setdefault(unit_id, []).append(c)

        for unit_id, comps in by_unit.items():
            for i in range(len(comps) - 1):
                a, b = comps[i], comps[i + 1]
                if not a.get("ksm_code") or not b.get("ksm_code"):
                    continue
                db.add(
                    PipelineEdge(
                        from_ksm=a["ksm_code"],
                        to_ksm=b["ksm_code"],
                        connection_type="pipeline",
                        distance_m=0.0,
                        unit_code=unit_id,
                        is_synthetic=True,
                    )
                )
                edges += 1
        db.commit()
        log.info("graph -> pipeline_edges: %d рёбер", edges)
    finally:
        db.close()
    return 0


# ==================================================================== NORMS
def seed_norms() -> int:
    from app.services.agent.repository.providers.norms_fragments import build_norm_fragments
    from app.services.agent.repository.providers.norms_provider import NormsProvider

    provider = NormsProvider(auto_index=False)
    fragments = build_norm_fragments()
    log.info("norms: %d фрагментов", len(fragments))
    ok = provider.ensure_index(fragments)
    provider.close()
    if not ok:
        log.error("norms: индексация в Qdrant не удалась")
        return 1
    log.info("norms -> Qdrant: готово")
    return 0


# ==================================================================== PASSPORTS
def seed_passports() -> int:
    import re

    from app.db.session import SessionLocal
    from app.models.sqlalchemy.all_models import Document, ExtractedCharacteristic
    from app.services.agent.repository.providers.passport_provider import extract_passport_params

    docs_dir = _repo_root() / "data" / "sample" / "documents"
    db = SessionLocal()
    _NOW = datetime.now(timezone.utc)
    try:
        count = 0
        rows: List[tuple] = []
        for path in sorted(docs_dir.glob("passport_*.md")):
            document_id = path.stem
            text = path.read_text(encoding="utf-8", errors="ignore")

            existing = db.query(Document).filter(Document.document_id == document_id).first()
            if existing is None:
                db.add(
                    Document(
                        document_id=document_id,
                        file_name=path.name,
                        file_path=str(path),
                        document_type="passport",
                        ocr_status="processed",
                        ocr_confidence=1.0,
                        processed_date=datetime.now(timezone.utc),
                        is_synthetic=True,
                    )
                )
                db.flush()

            db.query(ExtractedCharacteristic).filter(
                ExtractedCharacteristic.document_id == document_id
            ).delete()

            params = extract_passport_params(text)
            for field, info in params.items():
                rows.append(
                    (
                        document_id,
                        field,
                        info.get("value"),
                        _normalize_value(field, info.get("value")),
                        float(info.get("confidence", 1.0)),
                        path.name,
                        "regex",
                        True,
                        "seed_stack",
                        _NOW,
                        _NOW,
                    )
                )
            count += len(params)

        if rows:
            # Вставка характеристик bulk-курсором: драйвер psycopg2 напрямую
            # (см. идиосинкразию SQLAlchemy insertmanyvalues с этим пакетом).
            raw_conn = db.connection().connection
            with raw_conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO extracted_characteristics
                       (document_id, field_name, raw_value, normalized_value,
                        confidence, source_fragment, source_type, is_verified,
                        verified_by, verified_at, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    rows,
                )
        db.commit()
        log.info("passports -> PG: документов %d, характеристик %d", len(list(docs_dir.glob("passport_*.md"))), count)
    finally:
        db.close()
    return 0


def _normalize_value(field: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    if field in ("dn", "angle"):
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)
    if field in ("pn", "wall_thickness"):
        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return str(value)
    return str(value)


# ==================================================================== HISTORY
def seed_history(n: int = 200, per: int = 3) -> int:
    from app.db.session import SessionLocal
    from app.models.sqlalchemy.all_models import CandidateItem, MtrItem, MtrItemHistory

    db = SessionLocal()
    try:
        mtrs = db.query(MtrItem).limit(n).all()
        added = 0
        base = datetime.now(timezone.utc)
        payload_fields = ["stock_qty", "steel_grade", "material", "medium", "gost_tu"]

        for mtr in mtrs:
            attrs = mtr.attributes or {}
            for i in range(per):
                old = {p: (attrs.get(p) or {}).get("value") if isinstance(attrs.get(p), dict) else attrs.get(p) for p in payload_fields}
                new = dict(old)
                key = payload_fields[i % len(payload_fields)]
                new[key] = _mutated(new.get(key), mtr.mtr_code, i)
                db.add(
                    MtrItemHistory(
                        mtr_code=mtr.mtr_code,
                        changed_at=base - timedelta(days=(per - i) * 7),
                        changed_by="synthetic",
                        old_attributes={k: v for k, v in old.items() if v is not None},
                        new_attributes={k: v for k, v in new.items() if v is not None},
                    )
                )
                added += 1
        db.commit()
        log.info("history -> PG: %d событий", added)
    finally:
        db.close()
    return 0


def _mutated(value: Any, mtr_code: str, i: int) -> Any:
    digest = hashlib.sha1(f"{mtr_code}:{i}".encode()).hexdigest()
    seed = int(digest[:6], 16)
    if value is None:
        return seed % 1000
    if isinstance(value, (int, float)):
        return float(value) + (seed % 7)
    return f"{value}-v{seed % 9 + 1}"


# ==================================================================== MAIN
def main() -> int:
    parser = argparse.ArgumentParser(description="Загрузка данных полного стека (Шаг 3)")
    parser.add_argument("--graph", action="store_true", help="граф -> Neo4j + pipeline_edges")
    parser.add_argument("--norms", action="store_true", help="нормативы -> Qdrant")
    parser.add_argument("--passports", action="store_true", help="паспорта -> PG")
    parser.add_argument("--history", action="store_true", help="история -> PG")
    parser.add_argument("--all", action="store_true", help="все источники")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.all:
        args.graph = args.norms = args.passports = args.history = True
    if not any([args.graph, args.norms, args.passports, args.history]):
        parser.print_help()
        return 2

    status = 0
    if args.graph and seed_graph() != 0:
        status = 1
    if args.norms and seed_norms() != 0:
        status = 1
    if args.passports and seed_passports() != 0:
        status = 1
    if args.history and seed_history() != 0:
        status = 1
    if status == 0:
        log.info("seed_stack: все источники загружены")
    return status


if __name__ == "__main__":
    sys.exit(main())
