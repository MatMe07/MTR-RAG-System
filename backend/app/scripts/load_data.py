import sys
import os
import csv
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import SessionLocal
from app.models import (
    MTRItem, KSMItem, Document, DocumentPage, TestCase,
    ExtractedCharacteristic, ExpertMatch, MatchingRule,
    ReplacementSet
)


def load_mtr_catalog(file_path: str, manifest_path: str):
    db = SessionLocal()
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
            mtr_code = row.get('mtr_code', '').strip()
            mtr = MTRItem(
                mtr_code=mtr_code,
                ksm_code=row.get('ksm_code', '').strip() or None,
                item_type=row.get('item_type', '').strip(),
                subtype=row.get('subtype', '').strip() or None,
                designation=row.get('designation', '').strip() or None,
                dn=float(row['dn']) if row.get('dn') and row['dn'].strip() else None,
                d1=float(row['d1']) if row.get("d1") and row['d1'].strip() else None,
                d2=float(row['d2']) if row.get("d2") and row['d2'].strip() else None,
                wall_thickness=float(row['wall_thickness']) if row.get('wall_thickness') and row['wall_thickness'].strip() else None,
                angle=float(row['angle']) if row.get('angle') and row['angle'].strip() else None,
                pressure=float(row['pn']) if row.get('pn') and row['pn'].strip() else None,
                strength_class=row.get('strength_class', '').strip() or None,
                steel_grade=row.get('steel_grade', '').strip() or None,
                medium=row.get('medium', '').strip() or None,
                inner_coating=row.get('inner_coating', 'false').lower() == 'true',
                outer_coating=row.get('outer_coating', 'false').lower() == 'true',
                climate_version=row.get('climate_version', 'УХЛ').strip() or None,
                gost_or_tu=row.get('gost_tu', '').strip() or None,
                short_text=row.get('name', '').strip() or None,
                lot=row.get('lot', 'LOT-001').strip() or None,
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
    db = SessionLocal()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('ksm_code'):
                continue

            ksm = KSMItem(
                ksm_code=row.get('ksm_code', '').strip(),
                short_text=row.get('name', '').strip() or None,
                quantity=float(row['stock_qty']) if row.get('stock_qty') and row['stock_qty'].strip() else None,
                unit=row.get('unit', '').strip() or None,
                cost=float(row['cost']) if row.get('cost') and row['cost'].strip() else None,
                stock_category=row.get('stock_category', '').strip() or None,
                business_unit=row.get('business_unit', '').strip() or None,
                planned_involvement_date=datetime.strptime(row['planned_involvement_date'], '%Y-%m-%d') if row.get('planned_involvement_date') and row['planned_involvement_date'].strip() else None,
                forecast_involvement_date=datetime.strptime(row['forecast_involvement_date'], '%Y-%m-%d') if row.get('forecast_involvement_date') and row['forecast_involvement_date'].strip() else None,
                item_type=row.get('item_type', '').strip() or None,
                subtype=row.get('subtype', '').strip() or None,
                designation=row.get('designation', '').strip() or None,
                dn=float(row['dn']) if row.get('dn') and row['dn'].strip() else None,
                wall_thickness=float(row['wall_thickness']) if row.get('wall_thickness') and row['wall_thickness'].strip() else None,
                angle=float(row['angle']) if row.get('angle') and row['angle'].strip() else None,
                pressure=float(row['pn']) if row.get('pn') and row['pn'].strip() else None,
                strength_class=row.get('strength_class', '').strip() or None,
                steel_grade=row.get('steel_grade', '').strip() or None,
                medium=row.get('medium', '').strip() or None,
                inner_coating=row.get('inner_coating', 'false').lower() == 'true',
                outer_coating=row.get('outer_coating', 'false').lower() == 'true',
                climate_version=row.get('climate_version', 'УХЛ').strip() or None,
                gost_or_tu=row.get('gost_tu', '').strip() or None,

            )
            db.add(ksm)
            count += 1

    db.commit()
    db.close()
    print(f"Загружено KSM: {count} записей")


def load_documents(file_path: str, cards_path: str):
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
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
    db = SessionLocal()
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            
            if not line.strip():
                continue
            
            card_data = json.loads(line)
            if not card_data.get('mtr_code'):
                continue

            doc = db.query(Document).filter(
                Document.file_name.like(f'%{card_data.get("sources", [{}])[0].get("file", "")}%')
            ).first()

            if not doc:
                continue

            for source in card_data.get('sources', []):
                if source.get('type') != 'passport':
                    continue

                fields = []
                geo = card_data.get('geometry', {})
                if geo.get('dn'):
                    fields.append(('dn', str(geo['dn'])))
                if geo.get('wall_thickness'):
                    fields.append(('wall_thickness', str(geo['wall_thickness'])))
                if geo.get('angle'):
                    fields.append(('angle', str(geo['angle'])))

                if card_data.get('pressure') and card_data['pressure'].get('pn'):
                    fields.append(('pressure', str(card_data['pressure']['pn'])))

                mat = card_data.get('material', {})
                if mat.get('steel_grade'):
                    fields.append(('steel_grade', mat['steel_grade']))
                if mat.get('strength_class'):
                    fields.append(('strength_class', mat['strength_class']))

                env = card_data.get('environment', {})
                if env.get('medium'):
                    fields.append(('medium', env['medium']))
                if env.get('climate_version'):
                    fields.append(('climate_version', env['climate_version']))

                coat = card_data.get('coating', {})
                if coat.get('inner_coating') is not None:
                    fields.append(('inner_coating', str(coat.get('inner_coating', False))))
                if coat.get('outer_coating') is not None:
                    fields.append(('outer_coating', str(coat.get('outer_coating', False))))

                if card_data.get('normative') and card_data['normative'].get('gost_tu'):
                    fields.append(('gost_or_tu', card_data['normative']['gost_tu']))

                for field_name, value in fields:
                    char = ExtractedCharacteristic(
                        document_id=doc.id,
                        page_number=source.get('page', 1),
                        field_name=field_name,
                        normalized_value=value,
                        confidence=card_data.get('extraction', {}).get('confidence', 0.95)
                    )
                    # db.add(char)
                count += 1

    # db.commit()
    db.close()
    print(f"Загружено характеристик: {count} записей")


if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "sample"

    print("Загрузка данных...")

    load_mtr_catalog(data_dir / "mtr_catalog.csv", data_dir / "document_manifest.csv")
    load_ksm_from_catalog(data_dir / "mtr_catalog.csv")
    load_documents(data_dir / "document_manifest.csv", data_dir / "expected_item_cards.jsonl")
    load_golden_dataset(data_dir / "golden_dataset.csv")
    load_expected_cards(data_dir / "expected_item_cards.jsonl")

    replacement_path = data_dir / "replacement_sets.csv"
    if replacement_path.exists():
        load_replacement_sets(replacement_path)

    rules_path = data_dir / "matching_rules.csv"
    if rules_path.exists():
        load_matching_rules(rules_path)

    print("Все данные загружены!")
