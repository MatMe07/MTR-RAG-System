"""Валидация каталога МТР против Pydantic-схемы CatalogCard (Фаза 7).

Проверяет каждую карточку `regulated_mtr_catalog_1000.jsonl` на
соответствие `app.schemas.CatalogCard` и печатает сводку.

Использование:
    python app/scripts/validate_catalog.py [--catalog PATH]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import CatalogCard


def load_cards(path: Path):
    if not path.exists():
        print(f"Каталог не найден: {path}")
        raise SystemExit(2)
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if line.strip():
                yield i, line


def validate_catalog(path: Path) -> int:
    ok = 0
    skipped = 0
    errors: list[tuple[int, str, str]] = []
    for lineno, line in load_cards(path):
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            skipped += 1
            errors.append((lineno, "<json>", str(e)[:100]))
            continue
        try:
            CatalogCard.model_validate(raw)
            ok += 1
        except Exception as e:
            skipped += 1
            card_id = raw.get("card_id") or raw.get("name") or "<no id>"
            errors.append((lineno, str(card_id), str(e)[:120]))

    print(f"Файл: {path}")
    print(f"Карточек загружено: {ok + skipped}")
    print(f"  валидных: {ok}")
    print(f"  невалидных: {skipped}")
    if errors:
        print("\nПримеры ошибок (первые 10):")
        for lineno, card_id, msg in errors[:10]:
            print(f"  строка {lineno}, {card_id}: {msg}")
    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Валидация каталога против CatalogCard")
    parser.add_argument(
        "--catalog",
        default=str(
            Path(__file__).parent.parent.parent.parent
            / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl"
        ),
        help="Путь к JSONL-каталогу",
    )
    args = parser.parse_args()
    return validate_catalog(Path(args.catalog))


if __name__ == "__main__":
    raise SystemExit(main())