import sys
import argparse
import csv
from typing import Dict, Any
import json
from app.utils.jsonb_utils import (
    get_property_unit,
    get_property_value,
    normalize_properties,
    set_property_value,
)
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

SessionLocal = None
MTRItem = None
KSMItem = None
Document = None
DocumentPage = None
TestCase = None
ExtractedCharacteristic = None
MatchingRule = None
ReplacementSet = None


def _new_session():
    global SessionLocal
    global MTRItem, KSMItem, Document, DocumentPage, TestCase
    global ExtractedCharacteristic, MatchingRule, ReplacementSet

    if SessionLocal is None:
        from app.database import SessionLocal as session_factory
        from app.models import (
            Document as document_model,
            DocumentPage as document_page_model,
            ExtractedCharacteristic as characteristic_model,
            KSMItem as ksm_model,
            MTRItem as mtr_model,
            MatchingRule as matching_rule_model,
            ReplacementSet as replacement_set_model,
            TestCase as test_case_model,
        )

        SessionLocal = session_factory
        MTRItem = mtr_model
        KSMItem = ksm_model
        Document = document_model
        DocumentPage = document_page_model
        TestCase = test_case_model
        ExtractedCharacteristic = characteristic_model
        MatchingRule = matching_rule_model
        ReplacementSet = replacement_set_model

    return SessionLocal()


def load_mtr_catalog(file_path: str, manifest_path: str):
    db = _new_session()
    doc_map = {}
    with open(manifest_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            doc = db.query(Document).filter(
                Document.file_name == row.get('file_name', '').strip()
            ).first()
            if doc:
                expected_mtr = row.get('expected_mtr_code', '').strip()
                if expected_mtr:
                    doc_map[expected_mtr] = doc.id
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('mtr_code'):
                continue
            
            props = {}
            
            if row.get('dn') and row['dn'].strip():
                props = set_property_value(props, 'dn', float(row['dn']), 'мм')
            if row.get('wall_thickness') and row['wall_thickness'].strip():
                props = set_property_value(props, 'wall_thickness', float(row['wall_thickness']), 'мм')
            if row.get('angle') and row['angle'].strip():
                props = set_property_value(props, 'angle', float(row['angle']), '°')
            if row.get('pn') and row['pn'].strip():
                props = set_property_value(props, 'pn', float(row['pn']), 'PN')
            if row.get('strength_class') and row['strength_class'].strip():
                props = set_property_value(props, 'strength_class', row['strength_class'].strip())
            if row.get('steel_grade') and row['steel_grade'].strip():
                props = set_property_value(props, 'steel_grade', row['steel_grade'].strip())
            if row.get('medium') and row['medium'].strip():
                props = set_property_value(props, 'medium', row['medium'].strip())
            if row.get('climate_version') and row['climate_version'].strip():
                props = set_property_value(props, 'climate_version', row['climate_version'].strip())
            if row.get('gost_tu') and row['gost_tu'].strip():
                props = set_property_value(props, 'gost_tu', row['gost_tu'].strip())
            if row.get('inner_coating', 'false').lower() == 'true':
                props = set_property_value(props, 'inner_coating', True)
            if row.get('outer_coating', 'false').lower() == 'true':
                props = set_property_value(props, 'outer_coating', True)
            mtr_code = row.get('mtr_code', '').strip()
            mtr = MTRItem(
                mtr_code=mtr_code,
                ksm_code=row.get('ksm_code', '').strip() or None,
                item_type=row.get('item_type', '').strip(),
                subtype=row.get('subtype', '').strip() or None,
                designation=row.get('designation', '').strip() or None,
                short_text=row.get('name', '').strip() or None,
                lot=row.get('lot', 'LOT-001').strip() or None,
                properties=props,
                material_class=row.get('material_class', '').strip() or None,
                source_excel_row=count + 1,
                source_document_id = doc_map.get(mtr_code)
            )
            db.add(mtr)
            count += 1

    db.commit()
    db.close()
    print(f"Загружено MTR: {count} записей")


def load_ksm_from_catalog(file_path: str):
    db = _new_session()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('ksm_code'):
                continue
            
            props = {}
            
            if row.get('dn') and row['dn'].strip():
                props = set_property_value(props, 'dn', float(row['dn']), 'мм')
            if row.get('wall_thickness') and row['wall_thickness'].strip():
                props = set_property_value(props, 'wall_thickness', float(row['wall_thickness']), 'мм')
            if row.get('angle') and row['angle'].strip():
                props = set_property_value(props, 'angle', float(row['angle']), '°')
            if row.get('pn') and row['pn'].strip():
                props = set_property_value(props, 'pn', float(row['pn']), 'PN')
            if row.get('strength_class') and row['strength_class'].strip():
                props = set_property_value(props, 'strength_class', row['strength_class'].strip())
            if row.get('steel_grade') and row['steel_grade'].strip():
                props = set_property_value(props, 'steel_grade', row['steel_grade'].strip())
            if row.get('medium') and row['medium'].strip():
                props = set_property_value(props, 'medium', row['medium'].strip())
            if row.get('climate_version') and row['climate_version'].strip():
                props = set_property_value(props, 'climate_version', row['climate_version'].strip())
            if row.get('gost_tu') and row['gost_tu'].strip():
                props = set_property_value(props, 'gost_tu', row['gost_tu'].strip())
            if row.get('inner_coating', 'false').lower() == 'true':
                props = set_property_value(props, 'inner_coating', True)
            if row.get('outer_coating', 'false').lower() == 'true':
                props = set_property_value(props, 'outer_coating', True)
            
            ksm = KSMItem(
                ksm_code=row.get('ksm_code', '').strip(),
                short_text=row.get('name', '').strip() or None,
                item_type=row.get('item_type', '').strip() or None,
                subtype=row.get('subtype', '').strip() or None,
                designation=row.get('designation', '').strip() or None,
                properties=props,
                quantity=float(row['stock_qty']) if row.get('stock_qty') and row['stock_qty'].strip() else None,
                unit=row.get('unit', '').strip() or None,
                cost=None,
                stock_category=None,
                business_unit=None
            )
            db.add(ksm)
            count += 1

    db.commit()
    db.close()
    print(f"Загружено KSM: {count} записей")


def load_documents(file_path: str, cards_path: str):
    db = _new_session()
    cards_map = {}
    with open(cards_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            card = json.loads(line)
            sources = card.get('sources', [])
            for src in sources:
                if src.get('type') == 'passport':
                    file_name = src.get('file', '').strip()
                    if file_name:
                        cards_map[file_name] = {
                            'table_json': card.get('table_json'),
                            'card_id': card.get('card_id')
                        }
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('file_name'):
                continue

            file_name = row.get('file_name', '').strip()
            page_count = int(row['pages']) if row.get('pages') and row['pages'].strip() else 2
            quality = row.get('document_quality', 'хорошее').strip()

            doc = Document(
                file_name=file_name,
                file_type='passport',
                page_count=page_count,
                ocr_status='done' if quality != 'неполное' else 'pending',
                ocr_confidence=0.95 if quality == 'хорошее' else 0.5
            )
            db.add(doc)
            db.flush()
        
            card_info = cards_map.get(file_name, {})
            table_json = card_info.get('table_json')

            for i in range(page_count):
                page = DocumentPage(
                    document_id=doc.id,
                    page_number=i + 1,
                    ocr_text=f"Страница {i+1} документа {doc.file_name}",
                    ocr_confidence=0.95,
                    rotation_angle=0.0,
                    table_json=table_json
                )
                db.add(page)

            count += 1

    db.commit()
    db.close()
    print(f"Загружено документов: {count} записей")


def load_golden_dataset(file_path: str):
    db = _new_session()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('case_id'):
                continue

            expected_top1 = row.get('expected_top1_mtr', '').strip()
            expected_top3 = row.get('expected_top3_mtr', '').strip()

            test = TestCase(
                test_id=row.get('case_id', '').strip(),
                input_type='text_query' if row.get('input_type') == 'query' else 'passport',
                input_data={'ref': row.get('input_ref', '').strip()},
                expected_mtr_code=expected_top1 or None,
                expected_ksm_code=row.get('expected_top1_ksm', '').strip() or None,
                expected_status=row.get('expected_status', '').strip() or None,
                expected_reason=row.get('expert_comment', '').strip() or None,
                passed=False
            )
            db.add(test)
            count += 1

    db.commit()
    db.close()
    print(f"Загружено тестов: {count} записей")


def load_replacement_sets(file_path: str):
    db = _new_session()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('target_item_type'):
                continue

            rs = ReplacementSet(
                target_item_type=row.get('target_item_type', '').strip(),
                target_angle=int(row['target_angle']) if row.get('target_angle') and row['target_angle'].strip() else None,
                target_dn=float(row['target_dn']) if row.get('target_dn') and row['target_dn'].strip() else None,
                component_item_type=row.get('component_item_type', '').strip(),
                component_angle=int(row['component_angle']) if row.get('component_angle') and row['component_angle'].strip() else None,
                component_dn=float(row['component_dn']) if row.get('component_dn') and row['component_dn'].strip() else None,
                quantity=int(row['quantity']) if row.get('quantity') and row['quantity'].strip() else 1,
                condition=row.get('condition', '').strip() or None,
                source=row.get('source', '').strip() or None
            )
            db.add(rs)
            count += 1

    db.commit()
    db.close()
    print(f"Загружено замен: {count} записей")


def load_matching_rules(file_path: str):
    db = _new_session()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('parameter'):
                continue

            rule = MatchingRule(
                rule_type=row.get('rule_type', 'penalty').strip(),
                parameter=row.get('parameter', '').strip(),
                from_value=row.get('from_value', '').strip() or None,
                to_value=row.get('to_value', '').strip() or None,
                allowed=row.get('allowed', 'true').lower() == 'true',
                condition=row.get('condition', '').strip() or None,
                penalty=int(row['penalty']) if row.get('penalty') and row['penalty'].strip() else 0,
                source=row.get('source', '').strip() or None
            )
            db.add(rule)
            count += 1

    db.commit()
    db.close()
    print(f"Загружено правил: {count} записей")


def load_expected_cards(file_path: str):
    db = _new_session()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            card_data = json.loads(line)

            sources = card_data.get('sources', [])
            passport_source = None
            for src in sources:
                if src.get('type') == 'passport' and src.get('file'):
                    passport_source = src
                    break

            if not passport_source:
                continue

            file_name = passport_source.get('file')
            doc = db.query(Document).filter(
                Document.file_name.like(f'%{file_name}%')
            ).first()

            if not doc:
                print(f"Документ не найден: {file_name}")
                continue

            fields = []
            
            geo = card_data.get('geometry', {})
            if geo.get('dn') is not None:
                fields.append(('dn', str(geo['dn']), 'мм'))
            if geo.get('wall_thickness') is not None:
                fields.append(('wall_thickness', str(geo['wall_thickness']), 'мм'))
            if geo.get('angle') is not None:
                fields.append(('angle', str(geo['angle']), '°'))
            if geo.get('d1') is not None:
                fields.append(('d1', str(geo['d1']), 'мм'))
            if geo.get('d2') is not None:
                fields.append(('d2', str(geo['d2']), 'мм'))

            if card_data.get('pressure') and card_data['pressure'].get('pn') is not None:
                fields.append(('pressure', str(card_data['pressure']['pn']), 'МПа'))

            mat = card_data.get('material', {})
            if mat.get('steel_grade'):
                fields.append(('steel_grade', mat['steel_grade'], None))
            if mat.get('strength_class'):
                fields.append(('strength_class', mat['strength_class'], None))

            env = card_data.get('environment', {})
            if env.get('medium'):
                fields.append(('medium', env['medium'], None))
            if env.get('climate_version'):
                fields.append(('climate_version', env['climate_version'], None))
            if env.get('h2s_confirmed') is not None:
                fields.append(('h2s_confirmed', str(env['h2s_confirmed']), None))
            if env.get('co2_confirmed') is not None:
                fields.append(('co2_confirmed', str(env['co2_confirmed']), None))

            coat = card_data.get('coating', {})
            if coat.get('inner_coating') is not None:
                fields.append(('inner_coating', str(coat.get('inner_coating', False)), None))
            if coat.get('outer_coating') is not None:
                fields.append(('outer_coating', str(coat.get('outer_coating', False)), None))
            if coat.get('coating_type'):
                fields.append(('coating_type', coat['coating_type'], None))

            norm = card_data.get('normative', {})
            if norm.get('gost_tu'):
                fields.append(('gost_or_tu', norm['gost_tu'], None))

            if card_data.get('item_type'):
                fields.append(('item_type', card_data['item_type'], None))
            if card_data.get('subtype'):
                fields.append(('subtype', card_data['subtype'], None))

            if card_data.get('designation'):
                fields.append(('designation', card_data['designation'], None))

            for field_name, value, unit in fields:
                char = ExtractedCharacteristic(
                    document_id=doc.id,
                    page_number=passport_source.get('page', 1),
                    field_name=field_name,
                    raw_value=value,       
                    normalized_value=value, 
                    unit_code=unit, 
                    confidence=card_data.get('extraction', {}).get('confidence', 0.95),
                    source_fragment=passport_source.get('fragment', None) 
                )
                db.add(char)
                count += 1

    db.commit()
    db.close()
    print(f"Загружено характеристик: {count} записей")


def map_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    return normalize_properties(properties)


def _schema_version(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 1


def catalog_card_to_payloads(
    data: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any] | None]:
    codes = data.get('codes', {})
    mtr_code = codes.get('mtr_code')
    if not mtr_code:
        raise ValueError("В карточке отсутствует codes.mtr_code")

    properties = map_properties(data.get('properties', {}))
    common = {
        "item_type": data.get('item_type', ''),
        "subtype": data.get('subtype'),
        "designation": data.get('designation'),
        "short_text": data.get('name') or data.get('designation'),
        "properties": properties,
        "schema_version": _schema_version(data.get('schema_version')),
    }
    mtr_payload = {
        "mtr_code": mtr_code,
        "ksm_code": codes.get('ksm_code'),
        **common,
    }

    ksm_code = codes.get('ksm_code')
    if not ksm_code:
        return mtr_payload, None

    ksm_payload = {
        "ksm_code": ksm_code,
        **common,
        "quantity": get_property_value(properties, 'stock_qty'),
        "unit": get_property_unit(properties, 'stock_qty') or "pcs",
    }
    return mtr_payload, ksm_payload


def _upsert_mtr(db, payload: Dict[str, Any]) -> None:
    item = db.query(MTRItem).filter(
        MTRItem.mtr_code == payload["mtr_code"]
    ).first()
    if item is None:
        db.add(MTRItem(**payload))
        return
    for key, value in payload.items():
        setattr(item, key, value)


def _upsert_ksm(db, payload: Dict[str, Any]) -> None:
    item = db.query(KSMItem).filter(
        KSMItem.ksm_code == payload["ksm_code"]
    ).first()
    if item is None:
        db.add(KSMItem(**payload))
        return
    for key, value in payload.items():
        setattr(item, key, value)


def load_catalog_jsonl(
    file_path: str | Path,
    batch_size: int = 1000,
    *,
    load_ksm: bool = True,
) -> Dict[str, int]:
    """Load one ItemCardV2 JSONL catalog into PostgreSQL."""
    db = _new_session()
    mtr_count = 0
    ksm_count = 0

    print(f"Начинаем загрузку из {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Некорректный JSON в строке {line_number}: {exc}"
                    ) from exc

                try:
                    mtr_payload, ksm_payload = catalog_card_to_payloads(
                        data
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"Ошибка карточки в строке {line_number}: {exc}"
                    ) from exc

                _upsert_mtr(db, mtr_payload)
                mtr_count += 1

                if load_ksm and ksm_payload:
                    _upsert_ksm(db, ksm_payload)
                    ksm_count += 1

                if mtr_count % batch_size == 0:
                    db.commit()
                    print(f"Загружено {mtr_count} карточек...")

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        f"Каталог загружен: {mtr_count} МТР, {ksm_count} КСМ"
    )
    return {"mtr_count": mtr_count, "ksm_count": ksm_count}



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузка тестовых данных")
    parser.add_argument(
        "--catalog-jsonl",
        type=Path,
        help="ItemCardV2 JSONL-каталог для загрузки в МТР и КСМ",
    )
    parser.add_argument(
        "--skip-sample",
        action="store_true",
        help="Не загружать небольшой каталог из data/sample",
    )
    parser.add_argument(
        "--mtr-only",
        action="store_true",
        help="Из JSONL загружать только МТР без складских записей КСМ",
    )
    args = parser.parse_args()

    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "sample"
    print("Загрузка данных...")

    if not args.skip_sample:
        # load_mtr_catalog(
        #     data_dir / "mtr_catalog.csv",
        #     data_dir / "document_manifest.csv",
        # )
        # load_ksm_from_catalog(data_dir / "mtr_catalog.csv")
        load_documents(
            data_dir / "document_manifest.csv",
            data_dir / "expected_item_cards.jsonl",
        )
        load_golden_dataset(data_dir / "golden_dataset.csv")
        load_expected_cards(data_dir / "expected_item_cards.jsonl")

        replacement_path = data_dir / "replacement_sets.csv"
        if replacement_path.exists():
            load_replacement_sets(replacement_path)

        rules_path = data_dir / "matching_rules.csv"
        if rules_path.exists():
            load_matching_rules(rules_path)

    if args.catalog_jsonl:
        load_catalog_jsonl(
            args.catalog_jsonl,
            load_ksm=not args.mtr_only,
        )

    
    print("Все данные загружены!")
