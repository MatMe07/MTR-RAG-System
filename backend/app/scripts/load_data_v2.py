"""Load catalog data into the database (compatible with current models)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import engine, Base, SessionLocal
from app.models.sqlalchemy.all_models import (
    User, MtrItem, CandidateItem, Document, ExtractedCharacteristic,
    GoldenDataset, GroupKeyword, ContextualOverride, SynonymRecord,
    ValidationConstant, ValidationRule,
)
from app.core.security import hash_password
from app.services.agent.rules.seed import seed_rules_standalone
from datetime import datetime, timezone


def create_tables():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


def seed_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            import bcrypt
            db.add(User(
                username="admin",
                hashed_password=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
                role="admin",
                is_active=True,
            ))
            db.commit()
            print("Admin user created (admin / admin123)")
        else:
            print("Admin user already exists.")
    finally:
        db.close()


def load_catalog_jsonl(file_path: str, batch_size: int = 500):
    """Load ItemCardV2 JSONL catalog into MtrItem + CandidateItem."""
    db = SessionLocal()
    mtr_count = 0
    ksm_count = 0

    print(f"Loading catalog from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                data = json.loads(line)

                codes = data.get("codes", {})
                mtr_code = codes.get("mtr_code")
                ksm_code = codes.get("ksm_code")
                if not mtr_code:
                    continue

                props = data.get("properties", {})
                props_flat = {}
                for k, v in props.items():
                    if isinstance(v, dict) and "value" in v:
                        props_flat[k] = v["value"]
                    else:
                        props_flat[k] = v

                mtr = MtrItem(
                    mtr_code=mtr_code,
                    ksm_code=ksm_code,
                    card_id=data.get("card_id"),
                    item_type=data.get("item_type", ""),
                    subtype=data.get("subtype"),
                    name=data.get("name") or data.get("designation") or "",
                    designation=data.get("designation"),
                    attributes=props_flat,
                    gost_tu=props_flat.get("gost_tu") or props_flat.get("gost_or_tu"),
                    standard=props_flat.get("standard"),
                    stock_qty=float(props_flat.get("stock_qty", 0) or 0),
                    unit=props_flat.get("unit", "pcs") or "pcs",
                    is_synthetic=bool(props_flat.get("synthetic", False)),
                )
                db.add(mtr)
                mtr_count += 1

                if ksm_code:
                    ksm = CandidateItem(
                        ksm_code=ksm_code,
                        short_text=data.get("name") or data.get("designation"),
                        quantity=float(props_flat.get("stock_qty", 0) or 0),
                        stock_balance=float(props_flat.get("stock_qty", 0) or 0),
                    )
                    db.add(ksm)
                    ksm_count += 1

                if mtr_count % batch_size == 0:
                    db.commit()
                    print(f"  {mtr_count} MTR, {ksm_count} KSM loaded...")

        db.commit()
        print(f"Catalog loaded: {mtr_count} MTR, {ksm_count} KSM")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_sample_data():
    """Load sample data from data/sample/."""
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "sample"

    db = SessionLocal()
    try:
        # Load golden dataset
        golden_path = data_dir / "golden_dataset.csv"
        if golden_path.exists():
            import csv
            count = 0
            with open(golden_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    if not row.get("case_id"):
                        continue
                    db.add(GoldenDataset(
                        case_id=row["case_id"].strip(),
                        requested_mtr=row.get("expected_top1_mtr", "").strip() or None,
                        requested_description=row.get("input_ref", "").strip() or None,
                        expected_status=row.get("expected_status", "").strip() or None,
                        expert_comment=row.get("expert_comment", "").strip() or None,
                    ))
                    count += 1
            db.commit()
            print(f"Golden dataset loaded: {count} cases")

        # Load synonyms for better search
        synonyms = [
            ("item_type", "задвижка", "задвижка"),
            ("item_type", "заслонка", "задвижка"),
            ("item_type", "отвод", "отвод"),
            ("item_type", "колено", "отвод"),
            ("item_type", "тройник", "тройник"),
            ("item_type", "труба", "труба"),
            ("item_type", "переход", "переход"),
            ("item_type", "reducers", "переход"),
            ("item_type", "фланец", "фланец"),
            ("item_type", "заглушка", "заглушка"),
            ("item_type", "просвет", "просвет"),
            ("medium", "H2S", "H2S"),
            ("medium", "h2s", "H2S"),
            ("medium", "сероводород", "H2S"),
            ("medium", "CO2", "CO2"),
            ("medium", "co2", "CO2"),
        ]
        for group, raw, norm in synonyms:
            if not db.query(SynonymRecord).filter(
                SynonymRecord.group_name == group,
                SynonymRecord.raw_value == raw,
            ).first():
                db.add(SynonymRecord(
                    group_name=group, raw_value=raw, normalized_value=norm,
                ))
        db.commit()
        print("Synonyms loaded.")

        # Load group keywords
        keywords = [
            ("item_type", "задвижка", 10),
            ("item_type", "труба", 10),
            ("item_type", "отвод", 10),
            ("item_type", "тройник", 10),
            ("item_type", "фланец", 10),
            ("item_type", "заглушка", 10),
            ("item_type", "переход", 10),
            ("item_type", "клапан", 10),
            ("item_type", "смеситель", 10),
            ("item_type", "фильтр", 10),
            ("medium", "H2S", 15),
            ("medium", "CO2", 15),
        ]
        for group, kw, pri in keywords:
            if not db.query(GroupKeyword).filter(
                GroupKeyword.group_name == group,
                GroupKeyword.keyword == kw,
            ).first():
                db.add(GroupKeyword(
                    group_name=group, keyword=kw, priority=pri,
                ))
        db.commit()
        print("Group keywords loaded.")

        # Load validation rules for common item types
        rules = [
            ("труба", ["dn", "wall_thickness", "steel_grade"], [], ["angle", "pn"]),
            ("отвод", ["dn", "angle", "steel_grade"], [], []),
            ("задвижка", ["dn", "pn", "steel_grade"], [], []),
            ("тройник", ["dn", "steel_grade"], [], []),
            ("переход", ["d1", "d2", "steel_grade"], [], []),
            ("фланец", ["dn", "pn", "steel_grade"], [], []),
            ("заглушка", ["dn", "pn"], [], []),
        ]
        for itype, required, forbidden, optional in rules:
            if not db.query(ValidationRule).filter(
                ValidationRule.item_type == itype
            ).first():
                db.add(ValidationRule(
                    item_type=itype,
                    required_params=json.dumps(required),
                    forbidden_params=json.dumps(forbidden),
                    optional_params=json.dumps(optional),
                ))
        db.commit()
        print("Validation rules loaded.")

    finally:
        db.close()


if __name__ == "__main__":
    
    # print((Path(__file__).parent.parent.parent.parent / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl").exists())
    
    import argparse

    parser = argparse.ArgumentParser(description="Load data into the database")
    parser.add_argument("--catalog-jsonl", type=Path, help="JSONL catalog file")
    parser.add_argument("--skip-sample", action="store_true")
    parser.add_argument("--skip-catalog", action="store_true")
    parser.add_argument("--skip-tables", action="store_true")
    args = parser.parse_args()

    if not args.skip_tables:
        create_tables()

    seed_admin()

    print("Seeding validation rules from code...")
    counts = seed_rules_standalone()
    print(f"Rules seeded: constants={counts['constants']}, "
          f"synonyms={counts['synonyms']}, rules={counts['rules']}")

    if not args.skip_sample:
        load_sample_data()

    if args.catalog_jsonl:
        load_catalog_jsonl(args.catalog_jsonl)
    elif not args.skip_catalog:
        catalog_candidates = [
            Path("./data/catalog/regulated_mtr_catalog_1000.jsonl"),
            Path(__file__).parent.parent.parent.parent / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl",
        ]
        print(Path(__file__))
        catalog_path = next((p for p in catalog_candidates if p.exists()), None)
        if catalog_path:
            load_catalog_jsonl(catalog_path)
        else:
            print("Catalog not found, skipping.")

    print("\nAll data loaded successfully!")
