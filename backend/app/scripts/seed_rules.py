"""CLI: перенос правил валидации (sync/rebuild/verify) из кода в БД.

Запуск:
    python -m app.scripts.seed_rules [--sync|--rebuild|--verify]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from app.services.agent.rules.seed import seed_rules
from app.services.agent.rules.dynamic_rules import get_dynamic_rules


def cmd_sync() -> int:
    db = SessionLocal()
    try:
        counts = seed_rules(db)
        print("sync: ", counts)
        return 0
    finally:
        db.close()


def cmd_rebuild() -> int:
    """Полная пересборка таблиц правил: удалить и засеить заново."""
    from app.models.sqlalchemy.all_models import SynonymRecord, ValidationConstant, ValidationRule

    db = SessionLocal()
    try:
        for model in (ValidationConstant, ValidationRule, SynonymRecord):
            db.query(model).delete()
        db.commit()
        counts = seed_rules(db)
        print("rebuild: ", counts)
        return 0
    finally:
        db.close()


def cmd_verify() -> int:
    """Проверка: правила в БД соответствуют дефолтам кода."""
    db = SessionLocal()
    try:
        counts = seed_rules(db)
        provider = get_dynamic_rules()
        provider.refresh(force=True)
        total = 0
        for group in ("item_type", "medium", "operation", "climate"):
            total += len(provider.synonyms(group))
        rules = len(provider.validation_rule_item_types())
        print(f"verify: synced={counts}, synonyms_in_db~{total}, "
              f"rules_types={rules}, constants={len(provider.constants())}")
        return 0
    finally:
        db.close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync validation rules to DB")
    parser.add_argument("cmd", nargs="?", default="sync", choices=["sync", "rebuild", "verify"])
    args = parser.parse_args()

    if args.cmd == "rebuild":
        return cmd_rebuild()
    if args.cmd == "verify":
        return cmd_verify()
    return cmd_sync()


if __name__ == "__main__":
    sys.exit(main())