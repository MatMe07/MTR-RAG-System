import json
import random
import pandas as pd
from neo4j import GraphDatabase
from typing import List, Dict, Optional
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_GOLDEN = REPO_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.csv"
DEFAULT_ASSERTIONS = REPO_ROOT / "data" / "catalog" / "templates_from_llm.json"

# ---------- 1. Загрузка данных ----------
mtr_df = pd.read_csv(DEFAULT_GOLDEN, delimiter=';')  # ваш файл с 1000 строк
# print
with open(DEFAULT_ASSERTIONS, encoding='utf-8') as f:
    templates = json.load(f)

# ---------- 2. Подключение к Neo4j ----------
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "qwerty1234"))

def clear_graph(tx):
    tx.run("MATCH (n) DETACH DELETE n")

def create_constraints(tx):
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component) REQUIRE c.ksm_code IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:Unit) REQUIRE u.unit_code IS UNIQUE")

# ---------- 2. Улучшенный подбор деталей (с запасными вариантами) ----------
def pick_component(item_type: str, dn_target: int, pn_target: float, medium: str, h2s_required: bool = False):
    """Возвращает ksm_code или генерирует синтетический, если нет в MTR."""
    candidates = mtr_df[
        (mtr_df['item_type'].str.contains(item_type, case=False, na=False)) &
        (abs(mtr_df['dn'] - dn_target) <= 30) &
        (mtr_df['pn'] >= pn_target * 0.8)  # допуск по давлению
    ]
    if h2s_required:
        candidates = candidates[candidates['h2s_confirmed'] == True]
    if medium and medium != 'любая':
        candidates = candidates[candidates['medium'].str.contains(medium.split()[0], case=False, na=False)]
    
    # Если нет подходящей — генерируем синтетическую (для тестов)
    if candidates.empty:
        # Берём любую деталь из MTR и меняем DN/PN на нужные (для демо)
        fallback = mtr_df.sample(1).iloc[0]
        synthetic_ksm = f"SYN-{item_type[:3]}-{dn_target}-{int(pn_target)}"
        # Добавляем в DataFrame (только для этого запуска)
        new_row = fallback.copy()
        new_row['ksm_code'] = synthetic_ksm
        new_row['dn'] = dn_target
        new_row['pn'] = pn_target
        new_row['item_type'] = item_type
        new_row['h2s_confirmed'] = h2s_required
        mtr_df.loc[len(mtr_df)] = new_row
        return synthetic_ksm
    return candidates.sample(1).iloc[0]['ksm_code']

# ---------- 3. Размножение паттернов с увеличенными повторениями ----------
def expand_template(template, unit_code, instance_id, base_dn):
    edges = []
    prev_ksm = None
    dn_current = base_dn
    
    for step in template['pattern']:
        dn = dn_current
        if 'dn' in step and step['dn'] == 'DN_максимальный':
            dn = base_dn
        elif 'dn' in step and step['dn'].startswith('DN_'):
            factor = 0.6 if 'впуска' in step['dn'] or 'насоса' in step['dn'] else 0.8
            dn = int(base_dn * factor)
        
        pn_target = 25 if dn <= 200 else 16
        if 'H2S' in template['applicable_for']:
            pn_target = 40
        
        ksm = pick_component(
            item_type=step['item_type'],
            dn_target=dn,
            pn_target=pn_target,
            medium=template['applicable_for'][0],
            h2s_required='H2S' in template['applicable_for']
        )
        if not ksm:
            continue
        
        if prev_ksm:
            if 'H2S' in template['applicable_for']:
                conn_type = 'welded' if step['item_type'] not in ['задвижка', 'кран_обратный', 'заглушка'] else 'flanged'
            else:
                conn_type = 'flanged' if dn <= 200 else 'welded'
            
            edges.append({
                'from': prev_ksm,
                'to': ksm,
                'connection_type': conn_type,
                'distance_m': round(random.uniform(2.0, step.get('length_m', 20.0)), 1),
                'unit': unit_code,
                'template': template['template_name'],
                'instance': instance_id
            })
        prev_ksm = ksm
        dn_current = dn
    return edges

# ---------- 4. Генерация 12 установок с увеличенными повторениями ----------
def generate_all_edges():
    all_edges = []
    
    # 12 установок (вместо 8)
    unit_configs = [
        {'code': 'UNIT-H2S-001', 'medium': 'H2S', 'templates': [0, 1, 3, 5]},
        {'code': 'UNIT-H2S-002', 'medium': 'H2S', 'templates': [0, 1, 2, 4]},
        {'code': 'UNIT-H2S-003', 'medium': 'H2S', 'templates': [2, 3, 5]},
        {'code': 'UNIT-CO2-001', 'medium': 'CO2', 'templates': [0, 2, 3, 5]},
        {'code': 'UNIT-CO2-002', 'medium': 'CO2', 'templates': [1, 2, 4, 5]},
        {'code': 'UNIT-CO2-003', 'medium': 'CO2', 'templates': [0, 3, 4]},
        {'code': 'UNIT-GAS-001', 'medium': 'газ', 'templates': [0, 1, 3, 4]},
        {'code': 'UNIT-GAS-002', 'medium': 'газ', 'templates': [0, 2, 3, 5]},
        {'code': 'UNIT-GAS-003', 'medium': 'газ', 'templates': [1, 4, 5]},
        {'code': 'UNIT-OIL-001', 'medium': 'нефть', 'templates': [1, 2, 4, 5]},
        {'code': 'UNIT-OIL-002', 'medium': 'нефть', 'templates': [0, 3, 4]},
        {'code': 'UNIT-UTILITY-001', 'medium': 'вода', 'templates': [4, 5]},
    ]
    
    for unit in unit_configs:
        for template_idx in unit['templates']:
            template = templates['unit_templates'][template_idx]
            # Увеличиваем число повторений до 5-8
            reps = random.randint(5, 8) if '3-5' in template['repetitions'] else random.randint(3, 6)
            for inst in range(reps):
                dn_range = template['typical_dn_range']
                base_dn = random.choice(range(dn_range[0], dn_range[1]+1, 50))
                edges = expand_template(template, unit['code'], inst, base_dn)
                all_edges.extend(edges)
    
    # Добавляем кросс-соединения между установками (больше)
    for rule in templates['cross_connection_rules'] * 3:  # утраиваем
        units_in_rule = [u for u in unit_configs if any(t in u['templates'] for t in [0,1])]
        if len(units_in_rule) >= 2:
            from_unit = random.choice(units_in_rule)['code']
            to_unit = random.choice([u for u in units_in_rule if u['code'] != from_unit])['code']
            from_edges = [e for e in all_edges if e['unit'] == from_unit]
            to_edges = [e for e in all_edges if e['unit'] == to_unit]
            if from_edges and to_edges:
                all_edges.append({
                    'from': random.choice(from_edges)['to'],
                    'to': random.choice(to_edges)['from'],
                    'connection_type': 'welded',
                    'distance_m': round(random.uniform(15, 120), 1),
                    'unit': 'CROSS-CONNECTION',
                    'template': 'cross_unit',
                    'instance': 0
                })
    return all_edges

# ---------- 5. Загрузка в Neo4j (та же, что была) ----------
def load_to_neo4j(edges):
    with driver.session() as session:
        session.execute_write(clear_graph)
        session.execute_write(create_constraints)
        
        all_ksm = set()
        for e in edges:
            all_ksm.add(e['from'])
            all_ksm.add(e['to'])
        
        for ksm in all_ksm:
            row = mtr_df[mtr_df['ksm_code'] == ksm]
            if not row.empty:
                row = row.iloc[0]
                session.run("""
                    CREATE (c:Component {
                        ksm_code: $ksm,
                        item_type: $item_type,
                        dn: $dn,
                        pn: $pn,
                        material: $material,
                        medium: $medium,
                        h2s_confirmed: $h2s,
                        stock_qty: $stock
                    })
                """, ksm=ksm, item_type=row['item_type'], dn=int(row['dn']), 
                    pn=float(row['pn']), material=row.get('steel_grade', 'unknown'), 
                    medium=row['medium'], h2s=row.get('h2s_confirmed', False), 
                    stock=float(row.get('stock_qty', 0)))
        for e in edges:
            session.run(
                """
                MATCH (a:Component {ksm_code: $from_ksm})
                MATCH (b:Component {ksm_code: $to_ksm})
                CREATE (a)-[:CONNECTS_TO {
                    connection_type: $conn_type,
                    distance_m: $distance,
                    unit: $unit,
                    template: $template,
                    instance: $instance
                }]->(b)
                """,
                from_ksm=e['from'],
                to_ksm=e['to'],
                conn_type=e['connection_type'],
                distance=e['distance_m'],
                unit=e['unit'],
                template=e.get('template', 'unknown'),
                instance=e.get('instance', 0)
            )
        
        units = set(e['unit'] for e in edges)
        for unit in units:
            session.run("CREATE (u:Unit {unit_code: $unit})", unit=unit)
            for e in edges:
                if e['unit'] == unit:
                    for ksm in [e['from'], e['to']]:
                        session.run("""
                            MATCH (u:Unit {unit_code: $unit})
                            MATCH (c:Component {ksm_code: $ksm})
                            CREATE (c)-[:BELONGS_TO]->(u)
                        """, unit=unit, ksm=ksm)

# ---------- 6. Запуск ----------
if __name__ == "__main__":
    random.seed(42)  # для воспроизводимости
    edges = generate_all_edges()
    print(f"Сгенерировано {len(edges)} рёбер")
    unique_nodes = len(set([e['from'] for e in edges] + [e['to'] for e in edges]))
    print(f"Уникальных узлов: {unique_nodes}")
    load_to_neo4j(edges)
    print("Граф загружен. Откройте http://localhost:7474")
