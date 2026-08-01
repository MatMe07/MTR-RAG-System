"""Audit whether the demo catalog supports approved user scenarios."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CATALOG = (
    REPO_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl"
)

CORE_MVP_CLASSES = {
    "труба",
    "отвод",
    "переход",
    "задвижка",
    "заглушка",
    "тройник",
}

REPAIR_KIT_CLASSES = {
    "фланец",
    "прокладка",
    "крепеж",
    "сварочный материал",
    "материал восстановления покрытия",
}

KEY_PROPERTIES = {
    "pn",
    "steel_grade",
    "medium",
    "gost_tu",
    "stock_qty",
    "h2s_confirmed",
    "co2_confirmed",
}


def load_cards(path: Path = DEFAULT_CATALOG) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _property_value(card: dict[str, Any], key: str) -> Any:
    characteristic = card.get("properties", {}).get(key)
    if isinstance(characteristic, dict):
        return characteristic.get("value")
    return characteristic


def _signature(card: dict[str, Any]) -> str:
    ignored = {
        "stock_qty",
        "synthetic",
        "regulation_rule_id",
        "required_evidence",
        "conformity_status",
    }
    values = [
        (key, _property_value(card, key))
        for key in sorted(card.get("properties", {}))
        if key not in ignored
    ]
    return json.dumps(
        [card.get("item_type"), card.get("subtype"), values],
        ensure_ascii=False,
        sort_keys=True,
    )


def audit_catalog(cards: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts = Counter(card["item_type"] for card in cards)
    medium_counts = Counter(
        _property_value(card, "medium_code") for card in cards
    )
    property_presence = {
        key: sum(
            key in card.get("properties", {})
            for card in cards
        )
        for key in sorted(KEY_PROPERTIES)
    }
    unknown_values = {
        key: sum(
            _property_value(card, key) is None
            for card in cards
        )
        for key in ("h2s_confirmed", "co2_confirmed")
    }
    zero_stock = sum(
        _property_value(card, "stock_qty") == 0
        for card in cards
    )

    signatures = defaultdict(list)
    for card in cards:
        signatures[_signature(card)].append(card["codes"]["ksm_code"])
    duplicate_groups = [
        codes for codes in signatures.values() if len(codes) > 1
    ]

    present_classes = set(class_counts)
    return {
        "catalog_count": len(cards),
        "class_counts": dict(sorted(class_counts.items())),
        "medium_counts": dict(sorted(medium_counts.items())),
        "core_mvp": {
            "required": sorted(CORE_MVP_CLASSES),
            "missing": sorted(CORE_MVP_CLASSES - present_classes),
            "complete": CORE_MVP_CLASSES.issubset(present_classes),
        },
        "repair_kits": {
            "required": sorted(REPAIR_KIT_CLASSES),
            "missing": sorted(REPAIR_KIT_CLASSES - present_classes),
            "complete": REPAIR_KIT_CLASSES.issubset(present_classes),
        },
        "property_presence": property_presence,
        "unknown_values": unknown_values,
        "zero_stock_positions": zero_stock,
        "duplicate_signature_groups": len(duplicate_groups),
        "largest_duplicate_signature_group": max(
            (len(group) for group in duplicate_groups),
            default=1,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Проверить полноту демонстрационного каталога"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
    )
    args = parser.parse_args()
    print(
        json.dumps(
            audit_catalog(load_cards(args.catalog)),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
