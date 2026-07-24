"""Generate a deterministic JSONL catalog without keeping all cards in memory."""

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any, Iterator


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "data" / "generation" / "million_items_distribution.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "generated" / "mtr_catalog_1m.jsonl"


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_allocations(config: dict[str, Any], count: int) -> dict[str, int]:
    """Scale declared class counts while preserving an exact total."""
    if count < 1:
        raise ValueError("Количество карточек должно быть больше нуля.")

    classes = config["classes"]
    declared_total = sum(int(item["count"]) for item in classes)
    if declared_total < 1:
        raise ValueError("Сумма распределения классов должна быть больше нуля.")

    raw = [
        count * int(item["count"]) / declared_total
        for item in classes
    ]
    allocations = [math.floor(value) for value in raw]
    remainder = count - sum(allocations)
    remainder_order = sorted(
        range(len(classes)),
        key=lambda index: (raw[index] - allocations[index], -index),
        reverse=True,
    )
    for index in remainder_order[:remainder]:
        allocations[index] += 1

    return {
        item["collection_code"]: allocations[index]
        for index, item in enumerate(classes)
    }


def _fact(
    value: Any,
    fragment_id: str,
    *,
    value_type: str | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    if value_type is None:
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, (int, float)):
            value_type = "number"
        elif isinstance(value, list):
            value_type = "list"
        else:
            value_type = "string"

    return {
        "value": value,
        "value_type": value_type,
        "unit": unit,
        "status": "expert_confirmed" if value is not None else "unknown",
        "confidence": 1 if value is not None else None,
        "source_fragment_ids": [fragment_id],
    }


def _nullable_boolean(rng: random.Random, true_weight: float) -> bool | None:
    roll = rng.random()
    if roll < 0.08:
        return None
    return roll < 0.08 + true_weight


def _build_properties(
    class_config: dict[str, Any],
    shared: dict[str, Any],
    fragment_id: str,
    rng: random.Random,
) -> dict[str, dict[str, Any]]:
    medium = rng.choice(shared["mediums"])
    h2s_expected = "H2S" in medium
    co2_expected = "CO2" in medium
    properties = {
        "pn": _fact(rng.choice(class_config["pn_values"]), fragment_id, unit="bar"),
        "steel_grade": _fact(rng.choice(shared["steel_grades"]), fragment_id),
        "strength_class": _fact(rng.choice(shared["strength_classes"]), fragment_id),
        "medium": _fact(medium, fragment_id),
        "h2s_confirmed": _fact(
            _nullable_boolean(rng, 0.75 if h2s_expected else 0.05),
            fragment_id,
            value_type="boolean",
        ),
        "co2_confirmed": _fact(
            _nullable_boolean(rng, 0.75 if co2_expected else 0.05),
            fragment_id,
            value_type="boolean",
        ),
        "inner_coating": _fact(
            _nullable_boolean(rng, 0.42),
            fragment_id,
            value_type="boolean",
        ),
        "outer_coating": _fact(
            _nullable_boolean(rng, 0.68),
            fragment_id,
            value_type="boolean",
        ),
        "gost_tu": _fact(rng.choice(class_config["standards"]), fragment_id),
    }

    item_type = class_config["item_type"]
    if item_type == "переход":
        d1, d2 = rng.choice(class_config["diameter_pairs"])
        properties.update(
            {
                "d1": _fact(d1, fragment_id, unit="mm"),
                "d2": _fact(d2, fragment_id, unit="mm"),
                "wall_thickness": _fact(
                    rng.choice(shared["wall_thickness_mm"]),
                    fragment_id,
                    unit="mm",
                ),
            }
        )
    else:
        properties["dn"] = _fact(
            rng.choice(class_config["dn_values"]),
            fragment_id,
            unit="mm",
        )

    if item_type in {"труба", "отвод"}:
        properties["wall_thickness"] = _fact(
            rng.choice(shared["wall_thickness_mm"]),
            fragment_id,
            unit="mm",
        )
    if item_type == "отвод":
        properties["angle"] = _fact(
            rng.choice(class_config["angle_values"]),
            fragment_id,
            unit="deg",
        )
    if item_type == "задвижка":
        properties["drive_type"] = _fact(
            rng.choice(class_config["drive_types"]),
            fragment_id,
        )
        properties["leak_tightness_class"] = _fact(
            rng.choice(["A", "B", "C"]),
            fragment_id,
        )

    return properties


def iter_cards(
    config: dict[str, Any],
    count: int,
    seed: int,
) -> Iterator[dict[str, Any]]:
    rng = random.Random(seed)
    allocations = calculate_allocations(config, count)
    shared = config["shared_values"]
    domain = config["domain"]
    serial = 0

    for class_config in config["classes"]:
        collection_code = class_config["collection_code"]
        for _ in range(allocations[collection_code]):
            serial += 1
            suffix = f"{serial:07d}"
            fragment_id = f"SYN-FRAG-{suffix}"
            document_id = f"SYN-CATALOG-{suffix}"
            subtype = rng.choice(class_config["subtypes"])
            properties = _build_properties(class_config, shared, fragment_id, rng)
            designation = f"{class_config['item_type']}-{subtype}-SYN-{suffix}"

            yield {
                "schema_version": "2.0",
                "card_id": f"SYN-CARD-{suffix}",
                "card_version": 1,
                "lifecycle_status": "expert_confirmed",
                "item_type": class_config["item_type"],
                "subtype": subtype,
                "name": f"{class_config['item_type'].capitalize()} {subtype}",
                "designation": designation,
                "codes": {
                    "mtr_code": f"MTR-SYN-{suffix}",
                    "ksm_code": f"KSM-SYN-{suffix}",
                },
                "dcd": {
                    "domain": domain,
                    "collection": {
                        "code": collection_code,
                        "name": class_config["collection_name"],
                    },
                    "document": {
                        "document_id": document_id,
                        "document_type": "catalog",
                        "title": f"Синтетический каталог, строка {serial}",
                    },
                },
                "properties": properties,
                "sources": [
                    {
                        "source_id": f"SYN-SOURCE-{suffix}",
                        "type": "catalog",
                        "document_id": document_id,
                        "file_name": "mtr_catalog_1m.jsonl",
                        "source_fragment": {
                            "fragment_id": fragment_id,
                            "text": designation,
                            "page": None,
                            "row": serial,
                            "bbox": None,
                        },
                    }
                ],
            }


def generate_catalog(
    output_path: Path,
    *,
    count: int,
    config_path: Path = DEFAULT_CONFIG,
    seed: int | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    actual_seed = int(config.get("seed", 42) if seed is None else seed)
    allocations = calculate_allocations(config, count)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for card in iter_cards(config, count, actual_seed):
            file.write(json.dumps(card, ensure_ascii=False, separators=(",", ":")))
            file.write("\n")

    return {
        "output": str(output_path),
        "count": count,
        "seed": actual_seed,
        "allocations": allocations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Сгенерировать синтетический каталог карточек ItemCardV2."
    )
    parser.add_argument("--count", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    summary = generate_catalog(
        args.output,
        count=args.count,
        config_path=args.config,
        seed=args.seed,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
