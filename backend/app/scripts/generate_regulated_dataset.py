"""Build the reviewed 1,000-card demo catalog and a linked pipeline object."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGULATION = REPO_ROOT / "data" / "regulation" / "regulation_matrix.json"
DEFAULT_CATALOG_JSONL = (
    REPO_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl"
)
DEFAULT_CATALOG_CSV = (
    REPO_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.csv"
)
DEFAULT_OBJECT = REPO_ROOT / "data" / "graph" / "gas_pipeline_object.json"
DEFAULT_RELATIONS = REPO_ROOT / "data" / "graph" / "object_relations.csv"

DOMAIN = {
    "code": "gas_pipeline_mtr",
    "name": "МТР газопроводного объекта",
}
PN_VALUES = [16, 25, 40, 63, 100, 160]
STRENGTH_CLASSES = ["К42", "К48", "К52", "К56"]
DRIVE_TYPES = ["ручной", "электрический", "пневматический"]
OUTER_DIAMETER_TO_DN = {
    32: 25,
    38: 32,
    45: 40,
    57: 50,
    76: 65,
    89: 80,
    108: 100,
    114: 100,
    133: 125,
    159: 150,
    219: 200,
    273: 250,
    325: 300,
    377: 350,
    426: 400,
    530: 500,
    630: 600,
    720: 700,
    820: 800,
    1020: 1000,
}


def load_regulation(path: Path = DEFAULT_REGULATION) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _fact(
    value: Any,
    fragment_ids: Iterable[str],
    *,
    unit: str | None = None,
    status: str = "inferred",
    confidence: float | None = 0.85,
) -> dict[str, Any]:
    if isinstance(value, bool):
        value_type = "boolean"
    elif isinstance(value, (int, float)):
        value_type = "number"
    elif isinstance(value, list):
        value_type = "list"
    else:
        value_type = "string"
    if value is None:
        value_type = "boolean"
        status = "unknown"
        confidence = None
    return {
        "value": value,
        "value_type": value_type,
        "unit": unit,
        "status": status,
        "confidence": confidence,
        "source_fragment_ids": list(fragment_ids),
    }


def _material_for(
    rng: random.Random,
    material_profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    return rng.choice(material_profiles)


def _coating_value(rng: random.Random, probability: float) -> bool | None:
    roll = rng.random()
    if roll < 0.18:
        return None
    return roll < 0.18 + probability


def _common_properties(
    *,
    rule: dict[str, Any],
    regulation: dict[str, Any],
    rng: random.Random,
    synthetic_fragment: str,
    standard_fragments: list[str],
) -> dict[str, dict[str, Any]]:
    medium = rng.choice(regulation["medium_profiles"])
    material = _material_for(rng, regulation["material_profiles"])
    primary_standard = next(
        source
        for source in regulation["sources"]
        if source["source_id"] == rule["standard_ids"][0]
    )
    properties = {
        "synthetic": _fact(True, [synthetic_fragment], confidence=1),
        "regulation_rule_id": _fact(
            rule["rule_id"],
            [synthetic_fragment, *standard_fragments],
            confidence=1,
        ),
        "standard": _fact(
            primary_standard["standard"],
            [standard_fragments[0]],
            status="normalized",
            confidence=1,
        ),
        "gost_tu": _fact(
            primary_standard["standard"],
            [standard_fragments[0]],
            status="normalized",
            confidence=1,
        ),
        "applicable_standards": _fact(
            [
                next(
                    source["standard"]
                    for source in regulation["sources"]
                    if source["source_id"] == standard_id
                )
                for standard_id in rule["standard_ids"]
            ],
            standard_fragments,
            status="normalized",
            confidence=1,
        ),
        "standards_verification_status": _fact(
            rule["verification_status"],
            standard_fragments,
            status="normalized",
            confidence=1,
        ),
        "steel_grade": _fact(
            material["steel_grade"],
            [synthetic_fragment],
        ),
        "material_verification_status": _fact(
            material["verification_status"],
            [synthetic_fragment, *standard_fragments],
        ),
        "medium": _fact(
            medium["name"],
            [synthetic_fragment],
        ),
        "medium_code": _fact(
            medium["code"],
            [synthetic_fragment],
        ),
        "medium_compatibility_status": _fact(
            medium["compatibility_status"],
            [synthetic_fragment, *standard_fragments],
        ),
        "h2s_confirmed": _fact(
            None,
            [synthetic_fragment],
        ),
        "co2_confirmed": _fact(
            None,
            [synthetic_fragment],
        ),
        "required_evidence": _fact(
            medium["required_evidence"],
            [synthetic_fragment, *standard_fragments],
        ),
        "inner_coating": _fact(
            _coating_value(rng, 0.35),
            [synthetic_fragment],
        ),
        "outer_coating": _fact(
            _coating_value(rng, 0.65),
            [synthetic_fragment],
        ),
        "coating_evidence_status": _fact(
            "requires_passport_or_certificate",
            [synthetic_fragment],
        ),
        "conformity_status": _fact(
            "synthetic_not_certified",
            [synthetic_fragment, *standard_fragments],
        ),
        "stock_qty": _fact(
            rng.randint(0, 80),
            [synthetic_fragment],
            unit="pcs",
        ),
    }
    if rule["item_type"] != "задвижка":
        properties["pn"] = _fact(
            rng.choice(PN_VALUES),
            [synthetic_fragment],
            unit="PN",
        )
        properties["pn_verification_status"] = _fact(
            "requires_strength_calculation_and_project",
            [synthetic_fragment, *standard_fragments],
        )
        properties["strength_class"] = _fact(
            rng.choice(STRENGTH_CLASSES),
            [synthetic_fragment],
        )
    return properties


def _apply_dimensions(
    properties: dict[str, dict[str, Any]],
    rule: dict[str, Any],
    subtype: str,
    rng: random.Random,
    synthetic_fragment: str,
) -> None:
    item_type = rule["item_type"]
    if item_type in {"труба", "отвод", "заглушка"}:
        diameter, thickness = rng.choice(rule["dimension_profiles"])
        properties["outer_diameter"] = _fact(
            diameter, [synthetic_fragment], unit="mm"
        )
        properties["wall_thickness"] = _fact(
            thickness, [synthetic_fragment], unit="mm"
        )
        properties["dn"] = _fact(
            OUTER_DIAMETER_TO_DN[diameter],
            [synthetic_fragment],
            unit="DN",
        )
    elif item_type == "переход":
        d1, t1, d2, t2 = rng.choice(rule["dimension_profiles"])
        properties.update(
            {
                "outer_diameter_1": _fact(d1, [synthetic_fragment], unit="mm"),
                "wall_thickness_1": _fact(t1, [synthetic_fragment], unit="mm"),
                "outer_diameter_2": _fact(d2, [synthetic_fragment], unit="mm"),
                "wall_thickness_2": _fact(t2, [synthetic_fragment], unit="mm"),
                "d1": _fact(d1, [synthetic_fragment], unit="mm"),
                "d2": _fact(d2, [synthetic_fragment], unit="mm"),
                "dn_1": _fact(
                    OUTER_DIAMETER_TO_DN[d1],
                    [synthetic_fragment],
                    unit="DN",
                ),
                "dn_2": _fact(
                    OUTER_DIAMETER_TO_DN[d2],
                    [synthetic_fragment],
                    unit="DN",
                ),
            }
        )
    elif item_type == "тройник":
        profiles = [
            profile
            for profile in rule["dimension_profiles"]
            if (profile[0] == profile[2]) == (subtype == "равнопроходной")
        ]
        d_main, t_main, d_branch, t_branch = rng.choice(profiles)
        properties.update(
            {
                "outer_diameter_main": _fact(
                    d_main, [synthetic_fragment], unit="mm"
                ),
                "wall_thickness_main": _fact(
                    t_main, [synthetic_fragment], unit="mm"
                ),
                "outer_diameter_branch": _fact(
                    d_branch, [synthetic_fragment], unit="mm"
                ),
                "wall_thickness_branch": _fact(
                    t_branch, [synthetic_fragment], unit="mm"
                ),
                "dn": _fact(
                    OUTER_DIAMETER_TO_DN[d_main],
                    [synthetic_fragment],
                    unit="DN",
                ),
                "dn_main": _fact(
                    OUTER_DIAMETER_TO_DN[d_main],
                    [synthetic_fragment],
                    unit="DN",
                ),
                "dn_branch": _fact(
                    OUTER_DIAMETER_TO_DN[d_branch],
                    [synthetic_fragment],
                    unit="DN",
                ),
            }
        )
    elif item_type == "задвижка":
        dn, pn = rng.choice(rule["dn_pn_profiles"])
        properties["dn"] = _fact(dn, [synthetic_fragment], unit="mm")
        properties["pn"] = _fact(pn, [synthetic_fragment], unit="PN")
        properties["connection_type"] = _fact(
            "фланцевое", [synthetic_fragment]
        )
        properties["body_material"] = _fact(
            properties["steel_grade"]["value"],
            [synthetic_fragment],
        )
        properties["drive_type"] = _fact(
            rng.choice(DRIVE_TYPES), [synthetic_fragment]
        )
        properties["leak_tightness_class"] = _fact(
            rng.choice(["A", "B"]), [synthetic_fragment]
        )
        properties["pn_verification_status"] = _fact(
            "requires_passport_and_medium_check",
            [synthetic_fragment],
        )

    if item_type == "труба":
        properties["length"] = _fact(
            rng.choice([6, 8, 10, 11.7, 12]),
            [synthetic_fragment],
            unit="m",
        )
        properties["weld_type"] = _fact(
            "нет"
            if "бесшовная" in subtype
            else (
                "прямой шов"
                if "прямошовная" in subtype
                else "спиральный шов"
            ),
            [synthetic_fragment],
        )
    elif item_type == "отвод":
        properties["angle"] = _fact(
            rng.choice(rule["angles"]), [synthetic_fragment], unit="deg"
        )
        properties["bend_radius"] = _fact(
            "1.5 DN", [synthetic_fragment]
        )


def _designation(
    item_type: str,
    subtype: str,
    properties: dict[str, dict[str, Any]],
) -> str:
    value = lambda key: properties[key]["value"]
    if item_type == "труба":
        return (
            f"Труба {subtype} {value('outer_diameter')}x"
            f"{value('wall_thickness')} {value('steel_grade')}"
        )
    if item_type == "отвод":
        return (
            f"ОКШ {value('angle')}-{value('outer_diameter')}x"
            f"{value('wall_thickness')} {value('steel_grade')}"
        )
    if item_type == "переход":
        return (
            f"Переход {subtype} {value('outer_diameter_1')}x"
            f"{value('wall_thickness_1')}-{value('outer_diameter_2')}x"
            f"{value('wall_thickness_2')} {value('steel_grade')}"
        )
    if item_type == "тройник":
        return (
            f"Тройник {subtype} {value('outer_diameter_main')}x"
            f"{value('wall_thickness_main')}-{value('outer_diameter_branch')}x"
            f"{value('wall_thickness_branch')} {value('steel_grade')}"
        )
    if item_type == "задвижка":
        return f"Задвижка {subtype} DN{value('dn')} PN{value('pn')}"
    return (
        f"Заглушка {subtype} {value('outer_diameter')}x"
        f"{value('wall_thickness')} {value('steel_grade')}"
    )


def iter_cards(
    regulation: dict[str, Any],
    *,
    seed: int = 20260728,
) -> Iterable[dict[str, Any]]:
    rng = random.Random(seed)
    source_by_id = {
        source["source_id"]: source
        for source in regulation["sources"]
    }
    serial = 0
    for rule in regulation["class_rules"]:
        for _ in range(rule["target_count"]):
            serial += 1
            suffix = f"{serial:06d}"
            synthetic_fragment = f"SYN-CAT-FRAG-{suffix}"
            standards = [
                source_by_id[standard_id]
                for standard_id in rule["standard_ids"]
            ]
            standard_fragments = [
                f"STD-FRAG-{suffix}-{index:02d}"
                for index in range(1, len(standards) + 1)
            ]
            subtype = rng.choice(rule["subtypes"])
            properties = _common_properties(
                rule=rule,
                regulation=regulation,
                rng=rng,
                synthetic_fragment=synthetic_fragment,
                standard_fragments=standard_fragments,
            )
            _apply_dimensions(
                properties,
                rule,
                subtype,
                rng,
                synthetic_fragment,
            )
            designation = _designation(rule["item_type"], subtype, properties)
            yield {
                "schema_version": "2.0",
                "card_id": f"SYN-REG-CARD-{suffix}",
                "card_version": 1,
                "lifecycle_status": "draft",
                "item_type": rule["item_type"],
                "subtype": subtype,
                "name": designation,
                "designation": designation,
                "codes": {
                    "mtr_code": f"MTR-SYN-REG-{suffix}",
                    "ksm_code": f"KSM-SYN-REG-{suffix}",
                },
                "dcd": {
                    "domain": DOMAIN,
                    "collection": {
                        "code": rule["collection_code"],
                        "name": rule["collection_name"],
                    },
                    "document": {
                        "document_id": f"SYN-REG-CATALOG-{suffix}",
                        "document_type": "catalog",
                        "title": "Синтетический нормативно привязанный каталог",
                    },
                },
                "properties": properties,
                "sources": [
                    {
                        "source_id": f"SYN-REG-SOURCE-{suffix}",
                        "type": "catalog",
                        "document_id": f"SYN-REG-CATALOG-{suffix}",
                        "file_name": "regulated_mtr_catalog_1000.jsonl",
                        "source_fragment": {
                            "fragment_id": synthetic_fragment,
                            "text": (
                                "Синтетическая демонстрационная позиция; "
                                "не является реальным КСМ или сертификатом."
                            ),
                            "page": None,
                            "row": serial,
                            "bbox": None,
                        },
                    },
                    *[
                        {
                            "source_id": standard["source_id"],
                            "type": "standard",
                            "document_id": standard["source_id"],
                            "file_name": standard["official_url"],
                            "source_fragment": {
                                "fragment_id": fragment_id,
                                "text": standard["scope"],
                                "page": None,
                                "row": None,
                                "bbox": None,
                            },
                        }
                        for standard, fragment_id in zip(
                            standards,
                            standard_fragments,
                        )
                    ],
                ],
            }


def _property_value(card: dict[str, Any], key: str) -> Any:
    characteristic = card["properties"].get(key)
    return None if characteristic is None else characteristic["value"]


def _write_catalog_jsonl(
    cards: list[dict[str, Any]],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as file:
        for card in cards:
            file.write(
                json.dumps(card, ensure_ascii=False, separators=(",", ":"))
            )
            file.write("\n")


def _write_catalog_csv(
    cards: list[dict[str, Any]],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "card_id",
        "mtr_code",
        "ksm_code",
        "item_type",
        "subtype",
        "name",
        "designation",
        "dn",
        "outer_diameter",
        "wall_thickness",
        "d1",
        "d2",
        "angle",
        "pn",
        "steel_grade",
        "strength_class",
        "medium",
        "medium_compatibility_status",
        "h2s_confirmed",
        "co2_confirmed",
        "inner_coating",
        "outer_coating",
        "gost_tu",
        "standard",
        "stock_qty",
        "unit",
        "synthetic",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for card in cards:
            writer.writerow(
                {
                    "card_id": card["card_id"],
                    "mtr_code": card["codes"]["mtr_code"],
                    "ksm_code": card["codes"]["ksm_code"],
                    "item_type": card["item_type"],
                    "subtype": card["subtype"],
                    "name": card["name"],
                    "designation": card["designation"],
                    "dn": _property_value(card, "dn"),
                    "outer_diameter": _property_value(
                        card, "outer_diameter"
                    ),
                    "wall_thickness": _property_value(
                        card, "wall_thickness"
                    ),
                    "d1": _property_value(card, "d1"),
                    "d2": _property_value(card, "d2"),
                    "angle": _property_value(card, "angle"),
                    "pn": _property_value(card, "pn"),
                    "steel_grade": _property_value(card, "steel_grade"),
                    "strength_class": _property_value(
                        card, "strength_class"
                    ),
                    "medium": _property_value(card, "medium"),
                    "medium_compatibility_status": _property_value(
                        card, "medium_compatibility_status"
                    ),
                    "h2s_confirmed": _property_value(
                        card, "h2s_confirmed"
                    ),
                    "co2_confirmed": _property_value(
                        card, "co2_confirmed"
                    ),
                    "inner_coating": _property_value(
                        card, "inner_coating"
                    ),
                    "outer_coating": _property_value(
                        card, "outer_coating"
                    ),
                    "gost_tu": _property_value(card, "gost_tu"),
                    "standard": _property_value(card, "standard"),
                    "stock_qty": _property_value(card, "stock_qty"),
                    "unit": "pcs",
                    "synthetic": _property_value(card, "synthetic"),
                }
            )


def _select_object_components(
    cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    target_types = [
        "труба",
        "отвод",
        "переход",
        "задвижка",
        "заглушка",
        "тройник",
    ]
    medium_codes = [
        "natural_gas",
        "gas_h2s",
        "gas_co2",
        "gas_h2s_co2",
        "oil",
        "process_water",
        "corrosive_medium",
    ]
    selected: list[dict[str, Any]] = []
    for medium_code in medium_codes:
        for item_type in target_types:
            match = next(
                card
                for card in cards
                if card["item_type"] == item_type
                and _property_value(card, "medium_code") == medium_code
                and card not in selected
            )
            selected.append(match)
    return selected


def _build_object_graph(
    cards: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    selected = _select_object_components(cards)
    object_id = "OBJ-SYN-GAS-001"
    units = [
        {
            "unit_id": "UNIT-SYN-GAS-001",
            "name": "Узел приёма и первичной подготовки газа",
            "medium_code": "natural_gas",
        },
        {
            "unit_id": "UNIT-SYN-H2S-001",
            "name": "Участок кислого газа",
            "medium_code": "gas_h2s",
        },
        {
            "unit_id": "UNIT-SYN-CO2-001",
            "name": "Участок газа с CO2",
            "medium_code": "gas_co2",
        },
        {
            "unit_id": "UNIT-SYN-MIX-001",
            "name": "Участок газа с H2S и CO2",
            "medium_code": "gas_h2s_co2",
        },
        {
            "unit_id": "UNIT-SYN-OIL-001",
            "name": "Линия отвода углеводородного конденсата",
            "medium_code": "oil",
        },
        {
            "unit_id": "UNIT-SYN-WATER-001",
            "name": "Линия технической воды",
            "medium_code": "process_water",
        },
        {
            "unit_id": "UNIT-SYN-CORR-001",
            "name": "Контрольный коррозионно-активный участок",
            "medium_code": "corrosive_medium",
        },
    ]
    component_rows = []
    relations: list[dict[str, str]] = []
    for index, card in enumerate(selected, start=1):
        medium_code = _property_value(card, "medium_code")
        unit = next(
            unit for unit in units if unit["medium_code"] == medium_code
        )
        component_id = f"COMP-SYN-{index:03d}"
        component_rows.append(
            {
                "component_id": component_id,
                "unit_id": unit["unit_id"],
                "installed_card_id": card["card_id"],
                "ksm_code": card["codes"]["ksm_code"],
                "item_type": card["item_type"],
                "designation": card["designation"],
                "operating_medium": _property_value(card, "medium"),
                "compatibility_status": _property_value(
                    card, "medium_compatibility_status"
                ),
                "expert_review_required": True,
            }
        )
        relations.extend(
            [
                {
                    "from_id": component_id,
                    "relation": "PART_OF",
                    "to_id": unit["unit_id"],
                },
                {
                    "from_id": component_id,
                    "relation": "USES_MTR",
                    "to_id": card["card_id"],
                },
                {
                    "from_id": unit["unit_id"],
                    "relation": "PART_OF",
                    "to_id": object_id,
                },
            ]
        )
    graph = {
        "schema_version": "1.0",
        "object_id": object_id,
        "name": "Синтетический газопроводный объект для демонстрации RAG",
        "synthetic": True,
        "purpose": (
            "Проверка поиска, правил, графовых связей, складских и ТОиР "
            "сценариев. Не является проектной документацией реального объекта."
        ),
        "units": units,
        "components": component_rows,
        "relations": relations,
        "safety_note": (
            "Рабочая среда объекта не доказывает совместимость установленной "
            "синтетической позиции. Для H2S/CO2 и коррозионной среды всегда "
            "нужны паспорт, ТУ/ЛНД и решение эксперта."
        ),
    }
    return graph, relations


def _write_object(
    graph: dict[str, Any],
    relations: list[dict[str, str]],
    object_output: Path,
    relations_output: Path,
) -> None:
    object_output.parent.mkdir(parents=True, exist_ok=True)
    object_output.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    relations_output.parent.mkdir(parents=True, exist_ok=True)
    with relations_output.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["from_id", "relation", "to_id"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(relations)


def generate_regulated_dataset(
    *,
    regulation_path: Path = DEFAULT_REGULATION,
    catalog_jsonl: Path = DEFAULT_CATALOG_JSONL,
    catalog_csv: Path = DEFAULT_CATALOG_CSV,
    object_output: Path = DEFAULT_OBJECT,
    relations_output: Path = DEFAULT_RELATIONS,
    seed: int = 20260728,
) -> dict[str, Any]:
    regulation = load_regulation(regulation_path)
    cards = list(iter_cards(regulation, seed=seed))
    expected_count = sum(
        rule["target_count"] for rule in regulation["class_rules"]
    )
    if len(cards) != expected_count:
        raise ValueError(
            f"Generated {len(cards)} cards instead of {expected_count}."
        )
    _write_catalog_jsonl(cards, catalog_jsonl)
    _write_catalog_csv(cards, catalog_csv)
    graph, relations = _build_object_graph(cards)
    _write_object(
        graph,
        relations,
        object_output,
        relations_output,
    )
    return {
        "catalog_count": len(cards),
        "class_distribution": dict(
            Counter(card["item_type"] for card in cards)
        ),
        "object_components": len(graph["components"]),
        "relations": len(relations),
        "seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the reviewed 1,000-card MTR dataset."
    )
    parser.add_argument("--regulation", type=Path, default=DEFAULT_REGULATION)
    parser.add_argument("--catalog-jsonl", type=Path, default=DEFAULT_CATALOG_JSONL)
    parser.add_argument("--catalog-csv", type=Path, default=DEFAULT_CATALOG_CSV)
    parser.add_argument("--object", type=Path, default=DEFAULT_OBJECT)
    parser.add_argument("--relations", type=Path, default=DEFAULT_RELATIONS)
    parser.add_argument("--seed", type=int, default=20260728)
    args = parser.parse_args()
    summary = generate_regulated_dataset(
        regulation_path=args.regulation,
        catalog_jsonl=args.catalog_jsonl,
        catalog_csv=args.catalog_csv,
        object_output=args.object,
        relations_output=args.relations,
        seed=args.seed,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
