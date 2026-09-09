Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 16:12:16,525 INFO    | mtr.agent.executor               | [Executor] Execute query='Посчитай запас деталей для ремонта трех таких же участков как UNIT-SYN-GAS-001, один полный комплект должен всегда оставаться на складе' mode=auto request_id=None
2026-09-09 16:12:16,525 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 16:12:16,799 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.64 operations=['repair', 'inventory', 'plan', 'calculate'] item_types=[] technical_filters={} ambiguities=[] (274ms)
2026-09-09 16:12:16,811 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['PLAN_REPAIR', 'CHECK_STOCK'] missing={'PLAN_REPAIR': [], 'CHECK_STOCK': []}
2026-09-09 16:12:16,818 INFO    | mtr.agent.executor               | [Executor] Intent resolved: inventory
2026-09-09 16:12:16,818 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 16:12:17,164 INFO    | mtr.agent.tools                  | [graph_search] Found 6 components, 6 targets in 216ms
2026-09-09 16:12:17,165 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 16:12:17,173 INFO    | mtr.agent.tools                  | [catalog_search] Found 40 candidates (from 1000 cards) in 7ms
2026-09-09 16:12:17,285 INFO    | mtr.agent.tools                  | [stock_query] Checked 40 items (kept 40) in 112ms
2026-09-09 16:12:17,287 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=1 для KSM-SYN-REG-000003: тип=труба(база=1), остаток=13.0(+0)
2026-09-09 16:12:17,288 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000222: тип=отвод(база=2), нет на складе(+2)
2026-09-09 16:12:17,288 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000445: тип=переход(база=2), нет на складе(+2)
2026-09-09 16:12:17,288 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=5 для KSM-SYN-REG-000591: тип=задвижка(база=3), нет на складе(+2)
2026-09-09 16:12:17,288 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=3 для KSM-SYN-REG-000742: тип=заглушка(база=1), нет на складе(+2)
2026-09-09 16:12:17,288 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000872: тип=тройник(база=2), нет на складе(+2)
2026-09-09 16:12:17,289 INFO    | mtr.agent.tools                  | [rules_engine] Scored 40 candidates in 0ms
2026-09-09 16:12:17,293 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['марка стали', 'PN', 'DN', 'стенка', 'угол', 'материал', 'среда', 'тип изделия']
Запрос: Посчитай запас деталей для ремонта трех таких же участков как UNIT-SYN-GAS-001, один полный комплект должен всегда оставаться на складе
Найденные детали:
- Труба бесшовная горячедеформированная 159x8 09Г2С: совпадает по параметрам
- Труба бесшовная горячедеформированная 159x8 09ГСФ: совпадает по параметрам
- Труба бесшовная горячедеформированная 273x10 13ХФА: совпадает по параметрам
- Труба бесшовная горячедеформированная 108x6 20: совпадает по параметрам
- Труба бесшовная горячедеформированная 133x6 13ХФА: совпадает по параметрам
Результаты проверок: —
Предупреждения: ['Расчёт — черновик: нормы запаса требуют утверждения', 'Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.', 'Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.', 'Рекомендуемое количество является расчетным до получения норм страхового запаса.', 'Расчет нужно пересчитать после получения утвержденных норм страхового запаса.', 'Заявка остается черновиком до утверждения норм запаса и технической пригодности.', 'Система не заменяет наряд и производственную процедуру безопасного проведения работ.', 'Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S.']
Ошибки: —

Твой ответ должен быть:
1. Кратким (3–5 предложений).
2. Содержать рекомендацию (какую деталь выбрать, что проверить).
3. Если есть риски — указать их.
4. Не повторять сухие технические данные — переформулировать их.
5. Если хотя бы один критический параметр не совпал — явно указать это.

Ответ:
🔍 API Key resolved: OK
🔍 Base URL: https://openrouter.ai/api/v1/
🔍 Model: nvidia/nemotron-3-super-120b-a12b:free
2026-09-09 16:12:19,267 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-09 16:12:58,655 INFO    | mtr.agent.executor               | [Executor] Graph finished in 41837ms: components=45 sources=137 warnings=2 tools_used=['graph_search', 'catalog_search', 'stock_query', 'inventory_calculator', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 16:12:58,655 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 16:12:58,687 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 16:12:58,687 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Посчитай запас деталей для ремонта трех таких же участков как UNIT-SYN-GAS-001, один полный комплект должен всегда оставаться на складе",
  "intent": "inventory",
  "intent_label": "Склад и запас",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "catalog_search",
    "stock_query",
    "inventory_calculator",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "Рекомендуем взять бесшовную горячедеформированную трубу диаметром 159 мм, толщиной стенки 8 мм из стали 09Г2С, поскольку она полностью соответствует всем критическим параметрам участка UNIT‑SYN‑GAS‑001. Перед включением в запас необходимо проверить паспорт материала, подтвердить устойчивость к среде H₂S/CO₂ и наличие требуемого защитного покрытия, а также получить утверждение норм страхового запаса у ответственного за ремонт эксперта. Основные риски связаны с невозможностью гарантировать коррозионную стойкость только по геометрическим данным и с тем, что расчёт остаётся черновиком до официального утверждения норм запаса. После получения одобрения специалиста по ремонту участка H₂S можно оформить заявку на три комплекта плюс один резервный комплект на складе.",
  "components": [
    {
      "mtr_code": "MTR-SYN-REG-000020",
      "ksm_code": "KSM-SYN-REG-000020",
      "name": "Труба бесшовная горячедеформированная 159x8 09Г2С",
      "item_type": "труба",
      "quantity": 80.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 80.0; оценка правил",
      "source_id": "MTR-SYN-REG-000020",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000028",
      "ksm_code": "KSM-SYN-REG-000028",
      "name": "Труба бесшовная горячедеформированная 159x8 09ГСФ",
      "item_type": "труба",
      "quantity": 79.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 79.0; оценка правил",
      "source_id": "MTR-SYN-REG-000028",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000029",
      "ksm_code": "KSM-SYN-REG-000029",
      "name": "Труба бесшовная горячедеформированная 273x10 13ХФА",
      "item_type": "труба",
      "quantity": 75.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 75.0; оценка правил",
      "source_id": "MTR-SYN-REG-000029",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000008",
      "ksm_code": "KSM-SYN-REG-000008",
      "name": "Труба бесшовная горячедеформированная 108x6 20",
      "item_type": "труба",
      "quantity": 73.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 73.0; оценка правил",
      "source_id": "MTR-SYN-REG-000008",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000023",
      "ksm_code": "KSM-SYN-REG-000023",
      "name": "Труба бесшовная горячедеформированная 133x6 13ХФА",
      "item_type": "труба",
      "quantity": 64.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 64.0; оценка правил",
      "source_id": "MTR-SYN-REG-000023",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000039",
      "ksm_code": "KSM-SYN-REG-000039",
      "name": "Труба бесшовная горячедеформированная 133x6 20",
      "item_type": "труба",
      "quantity": 64.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 64.0; оценка правил",
      "source_id": "MTR-SYN-REG-000039",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000013",
      "ksm_code": "KSM-SYN-REG-000013",
      "name": "Труба бесшовная горячедеформированная 57x4 13ХФА",
      "item_type": "труба",
      "quantity": 60.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 60.0; оценка правил",
      "source_id": "MTR-SYN-REG-000013",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000040",
      "ksm_code": "KSM-SYN-REG-000040",
      "name": "Труба бесшовная горячедеформированная 57x4 13ХФА",
      "item_type": "труба",
      "quantity": 58.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 58.0; оценка правил",
      "source_id": "MTR-SYN-REG-000040",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000037",
      "ksm_code": "KSM-SYN-REG-000037",
      "name": "Труба бесшовная горячедеформированная 377x12 09ГСФ",
      "item_type": "труба",
      "quantity": 57.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 57.0; оценка правил",
      "source_id": "MTR-SYN-REG-000037",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000018",
      "ksm_code": "KSM-SYN-REG-000018",
      "name": "Труба бесшовная горячедеформированная 133x6 13ХФА",
      "item_type": "труба",
      "quantity": 56.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 56.0; оценка правил",
      "source_id": "MTR-SYN-REG-000018",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000033",
      "ksm_code": "KSM-SYN-REG-000033",
      "name": "Труба бесшовная горячедеформированная 377x12 13ХФА",
      "item_type": "труба",
      "quantity": 56.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 56.0; оценка правил",
      "source_id": "MTR-SYN-REG-000033",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000004",
      "ksm_code": "KSM-SYN-REG-000004",
      "name": "Труба бесшовная горячедеформированная 219x10 13ХФА",
      "item_type": "труба",
      "quantity": 52.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 52.0; оценка правил",
      "source_id": "MTR-SYN-REG-000004",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000005",
      "ksm_code": "KSM-SYN-REG-000005",
      "name": "Труба бесшовная горячедеформированная 89x6 09Г2С",
      "item_type": "труба",
      "quantity": 50.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 50.0; оценка правил",
      "source_id": "MTR-SYN-REG-000005",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000002",
      "ksm_code": "KSM-SYN-REG-000002",
      "name": "Труба бесшовная горячедеформированная 133x6 13ХФА",
      "item_type": "труба",
      "quantity": 49.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 49.0; оценка правил",
      "source_id": "MTR-SYN-REG-000002",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000010",
      "ksm_code": "KSM-SYN-REG-000010",
      "name": "Труба бесшовная горячедеформированная 89x6 13ХФА",
      "item_type": "труба",
      "quantity": 47.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 47.0; оценка правил",
      "source_id": "MTR-SYN-REG-000010",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000006",
      "ksm_code": "KSM-SYN-REG-000006",
      "name": "Труба бесшовная горячедеформированная 377x12 20",
      "item_type": "труба",
      "quantity": 44.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 44.0; оценка правил",
      "source_id": "MTR-SYN-REG-000006",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000019",
      "ksm_code": "KSM-SYN-REG-000019",
      "name": "Труба бесшовная горячедеформированная 76x5 09ГСФ",
      "item_type": "труба",
      "quantity": 41.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 41.0; оценка правил",
      "source_id": "MTR-SYN-REG-000019",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000035",
      "ksm_code": "KSM-SYN-REG-000035",
      "name": "Труба бесшовная горячедеформированная 133x6 09ГСФ",
      "item_type": "труба",
      "quantity": 41.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 41.0; оценка правил",
      "source_id": "MTR-SYN-REG-000035",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000021",
      "ksm_code": "KSM-SYN-REG-000021",
      "name": "Труба бесшовная горячедеформированная 426x14 09ГСФ",
      "item_type": "труба",
      "quantity": 40.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 40.0; оценка правил",
      "source_id": "MTR-SYN-REG-000021",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000036",
      "ksm_code": "KSM-SYN-REG-000036",
      "name": "Труба бесшовная горячедеформированная 377x12 13ХФА",
      "item_type": "труба",
      "quantity": 40.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 40.0; оценка правил",
      "source_id": "MTR-SYN-REG-000036",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000031",
      "ksm_code": "KSM-SYN-REG-000031",
      "name": "Труба бесшовная горячедеформированная 89x6 20",
      "item_type": "труба",
      "quantity": 38.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 38.0; оценка правил",
      "source_id": "MTR-SYN-REG-000031",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000007",
      "ksm_code": "KSM-SYN-REG-000007",
      "name": "Труба бесшовная горячедеформированная 530x16 09ГСФ",
      "item_type": "труба",
      "quantity": 37.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 37.0; оценка правил",
      "source_id": "MTR-SYN-REG-000007",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000024",
      "ksm_code": "KSM-SYN-REG-000024",
      "name": "Труба бесшовная горячедеформированная 108x6 13ХФА",
      "item_type": "труба",
      "quantity": 36.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 36.0; оценка правил",
      "source_id": "MTR-SYN-REG-000024",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000022",
      "ksm_code": "KSM-SYN-REG-000022",
      "name": "Труба бесшовная горячедеформированная 325x12 20",
      "item_type": "труба",
      "quantity": 35.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 35.0; оценка правил",
      "source_id": "MTR-SYN-REG-000022",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000026",
      "ksm_code": "KSM-SYN-REG-000026",
      "name": "Труба бесшовная горячедеформированная 530x16 09Г2С",
      "item_type": "труба",
      "quantity": 35.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 35.0; оценка правил",
      "source_id": "MTR-SYN-REG-000026",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000032",
      "ksm_code": "KSM-SYN-REG-000032",
      "name": "Труба бесшовная горячедеформированная 108x6 13ХФА",
      "item_type": "труба",
      "quantity": 31.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 31.0; оценка правил",
      "source_id": "MTR-SYN-REG-000032",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000014",
      "ksm_code": "KSM-SYN-REG-000014",
      "name": "Труба бесшовная горячедеформированная 273x10 13ХФА",
      "item_type": "труба",
      "quantity": 26.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 26.0; оценка правил",
      "source_id": "MTR-SYN-REG-000014",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000009",
      "ksm_code": "KSM-SYN-REG-000009",
      "name": "Труба бесшовная горячедеформированная 89x6 09ГСФ",
      "item_type": "труба",
      "quantity": 20.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 20.0; оценка правил",
      "source_id": "MTR-SYN-REG-000009",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000012",
      "ksm_code": "KSM-SYN-REG-000012",
      "name": "Труба бесшовная горячедеформированная 219x10 20",
      "item_type": "труба",
      "quantity": 20.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 20.0; оценка правил",
      "source_id": "MTR-SYN-REG-000012",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000016",
      "ksm_code": "KSM-SYN-REG-000016",
      "name": "Труба бесшовная горячедеформированная 89x6 09Г2С",
      "item_type": "труба",
      "quantity": 20.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 20.0; оценка правил",
      "source_id": "MTR-SYN-REG-000016",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000025",
      "ksm_code": "KSM-SYN-REG-000025",
      "name": "Труба бесшовная горячедеформированная 159x8 09ГСФ",
      "item_type": "труба",
      "quantity": 20.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 20.0; оценка правил",
      "source_id": "MTR-SYN-REG-000025",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000001",
      "ksm_code": "KSM-SYN-REG-000001",
      "name": "Труба бесшовная горячедеформированная 530x16 09ГСФ",
      "item_type": "труба",
      "quantity": 19.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 19.0; оценка правил",
      "source_id": "MTR-SYN-REG-000001",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000011",
      "ksm_code": "KSM-SYN-REG-000011",
      "name": "Труба бесшовная горячедеформированная 89x6 13ХФА",
      "item_type": "труба",
      "quantity": 19.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 19.0; оценка правил",
      "source_id": "MTR-SYN-REG-000011",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000030",
      "ksm_code": "KSM-SYN-REG-000030",
      "name": "Труба бесшовная горячедеформированная 530x16 20",
      "item_type": "труба",
      "quantity": 19.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 19.0; оценка правил",
      "source_id": "MTR-SYN-REG-000030",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000034",
      "ksm_code": "KSM-SYN-REG-000034",
      "name": "Труба бесшовная горячедеформированная 273x10 09ГСФ",
      "item_type": "труба",
      "quantity": 18.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 18.0; оценка правил",
      "source_id": "MTR-SYN-REG-000034",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000003",
      "ksm_code": "KSM-SYN-REG-000003",
      "name": "Труба бесшовная горячедеформированная 89x6 09Г2С",
      "item_type": "труба",
      "quantity": 13.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "совпадает по параметрам; на складе: 13.0; оценка правил",
      "source_id": "COMP-SYN-001",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000017",
      "ksm_code": "KSM-SYN-REG-000017",
      "name": "Труба бесшовная горячедеформированная 108x6 09ГСФ",
      "item_type": "труба",
      "quantity": 12.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 12.0; оценка правил",
      "source_id": "MTR-SYN-REG-000017",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000015",
      "ksm_code": "KSM-SYN-REG-000015",
      "name": "Труба бесшовная горячедеформированная 108x6 13ХФА",
      "item_type": "труба",
      "quantity": 11.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 11.0; оценка правил",
      "source_id": "MTR-SYN-REG-000015",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000027",
      "ksm_code": "KSM-SYN-REG-000027",
      "name": "Труба бесшовная горячедеформированная 325x12 13ХФА",
      "item_type": "труба",
      "quantity": 3.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 3.0; оценка правил",
      "source_id": "MTR-SYN-REG-000027",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000038",
      "ksm_code": "KSM-SYN-REG-000038",
      "name": "Труба бесшовная горячедеформированная 377x12 13ХФА",
      "item_type": "труба",
      "quantity": 1.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 1.0; оценка правил",
      "source_id": "MTR-SYN-REG-000038",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000222",
      "ksm_code": "KSM-SYN-REG-000222",
      "name": "ОКШ 45-108x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: отвод нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-002",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000445",
      "ksm_code": "KSM-SYN-REG-000445",
      "name": "Переход концентрический 108x4-76x4 13ХФА",
      "item_type": "переход",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: переход нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-003",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000591",
      "ksm_code": "KSM-SYN-REG-000591",
      "name": "Задвижка клиновая DN80 PN25",
      "item_type": "задвижка",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: задвижка нужна срочно; нет остатков; нет на складе — срочность закупки: критическая",
      "source_id": "COMP-SYN-004",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000742",
      "ksm_code": "KSM-SYN-REG-000742",
      "name": "Заглушка эллиптическая приварная 57x3 20",
      "item_type": "заглушка",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "рекомендуется закупить: заглушка; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-005",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000872",
      "ksm_code": "KSM-SYN-REG-000872",
      "name": "Тройник переходный 426x12-325x10 13ХФА",
      "item_type": "тройник",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: тройник нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-006",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000003",
      "ksm_code": "KSM-SYN-REG-000003",
      "name": "Труба бесшовная горячедеформированная 89x6 09Г2С",
      "item_type": "труба",
      "quantity": 13.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "совпадает по параметрам; на складе: 13.0; оценка правил",
      "source_id": "COMP-SYN-001",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000222",
      "ksm_code": "KSM-SYN-REG-000222",
      "name": "ОКШ 45-108x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: отвод нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-002",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000445",
      "ksm_code": "KSM-SYN-REG-000445",
      "name": "Переход концентрический 108x4-76x4 13ХФА",
      "item_type": "переход",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: переход нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-003",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000591",
      "ksm_code": "KSM-SYN-REG-000591",
      "name": "Задвижка клиновая DN80 PN25",
      "item_type": "задвижка",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: задвижка нужна срочно; нет остатков; нет на складе — срочность закупки: критическая",
      "source_id": "COMP-SYN-004",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000742",
      "ksm_code": "KSM-SYN-REG-000742",
      "name": "Заглушка эллиптическая приварная 57x3 20",
      "item_type": "заглушка",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "рекомендуется закупить: заглушка; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-005",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000872",
      "ksm_code": "KSM-SYN-REG-000872",
      "name": "Тройник переходный 426x12-325x10 13ХФА",
      "item_type": "тройник",
      "quantity": 1.0,
      "status": "установлен на UNIT-SYN-GAS-001",
      "detail": "критично: тройник нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-006",
      "unit_id": "UNIT-SYN-GAS-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    }
  ],
  "warnings": [
    "Расчёт — черновик: нормы запаса требуют утверждения",
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.",
    "Рекомендуемое количество является расчетным до получения норм страхового запаса.",
    "Расчет нужно пересчитать после получения утвержденных норм страхового запаса.",
    "Заявка остается черновиком до утверждения норм запаса и технической пригодности.",
    "Система не заменяет наряд и производственную процедуру безопасного проведения работ.",
    "Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S."
  ],
  "warning_categories": {
    "Планирование и закупка": [
      "Расчёт — черновик: нормы запаса требуют утверждения",
      "Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.",
      "Рекомендуемое количество является расчетным до получения норм страхового запаса.",
      "Расчет нужно пересчитать после получения утвержденных норм страхового запаса."
    ],
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
      "Заявка остается черновиком до утверждения норм запаса и технической пригодности.",
      "Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S."
    ],
    "Экспертная проверка": [
      "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом."
    ],
    "Прочее": [
      "Система не заменяет наряд и производственную процедуру безопасного проведения работ."
    ]
  },
  "purchase_recommendation": null,
  "sources": [
    {
      "kind": "object_graph",
      "id": "gas_pipeline_object.json",
      "fragment": "демо-объект"
    },
    {
      "kind": "project_documentation",
      "id": "gas_pipeline_object.json",
      "fragment": "проектная схема объекта"
    },
    {
      "kind": "maintenance_policy",
      "id": "MTR-TOIR-POLICY-001",
      "fragment": "регламент ТОиР (черновой)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-001",
      "fragment": "UNIT-SYN-GAS-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-001",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-002",
      "fragment": "UNIT-SYN-GAS-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-002",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-003",
      "fragment": "UNIT-SYN-GAS-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-003",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-004",
      "fragment": "UNIT-SYN-GAS-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-004",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-005",
      "fragment": "UNIT-SYN-GAS-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-005",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-006",
      "fragment": "UNIT-SYN-GAS-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-006",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000001",
      "fragment": "Труба бесшовная горячедеформированная 530x16 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000001",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000002",
      "fragment": "Труба бесшовная горячедеформированная 133x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000002",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000003",
      "fragment": "Труба бесшовная горячедеформированная 89x6 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000003",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000004",
      "fragment": "Труба бесшовная горячедеформированная 219x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000004",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000005",
      "fragment": "Труба бесшовная горячедеформированная 89x6 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000005",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000006",
      "fragment": "Труба бесшовная горячедеформированная 377x12 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000006",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000007",
      "fragment": "Труба бесшовная горячедеформированная 530x16 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000007",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000008",
      "fragment": "Труба бесшовная горячедеформированная 108x6 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000008",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000009",
      "fragment": "Труба бесшовная горячедеформированная 89x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000009",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000010",
      "fragment": "Труба бесшовная горячедеформированная 89x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000010",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000011",
      "fragment": "Труба бесшовная горячедеформированная 89x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000011",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000012",
      "fragment": "Труба бесшовная горячедеформированная 219x10 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000012",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000013",
      "fragment": "Труба бесшовная горячедеформированная 57x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000013",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000014",
      "fragment": "Труба бесшовная горячедеформированная 273x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000014",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000015",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000015",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000016",
      "fragment": "Труба бесшовная горячедеформированная 89x6 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000016",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000017",
      "fragment": "Труба бесшовная горячедеформированная 108x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000017",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000018",
      "fragment": "Труба бесшовная горячедеформированная 133x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000018",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000019",
      "fragment": "Труба бесшовная горячедеформированная 76x5 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000019",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000020",
      "fragment": "Труба бесшовная горячедеформированная 159x8 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000020",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000021",
      "fragment": "Труба бесшовная горячедеформированная 426x14 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000021",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000022",
      "fragment": "Труба бесшовная горячедеформированная 325x12 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000022",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000023",
      "fragment": "Труба бесшовная горячедеформированная 133x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000023",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000024",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000024",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000025",
      "fragment": "Труба бесшовная горячедеформированная 159x8 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000025",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000026",
      "fragment": "Труба бесшовная горячедеформированная 530x16 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000026",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000027",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000027",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000028",
      "fragment": "Труба бесшовная горячедеформированная 159x8 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000028",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000029",
      "fragment": "Труба бесшовная горячедеформированная 273x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000029",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000030",
      "fragment": "Труба бесшовная горячедеформированная 530x16 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000030",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000031",
      "fragment": "Труба бесшовная горячедеформированная 89x6 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000031",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000032",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000032",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000033",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000033",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000034",
      "fragment": "Труба бесшовная горячедеформированная 273x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000034",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000035",
      "fragment": "Труба бесшовная горячедеформированная 133x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000035",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000036",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000036",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000037",
      "fragment": "Труба бесшовная горячедеформированная 377x12 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000037",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000038",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000038",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000039",
      "fragment": "Труба бесшовная горячедеформированная 133x6 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000039",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000040",
      "fragment": "Труба бесшовная горячедеформированная 57x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000040",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000001",
      "fragment": "остаток: 19.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000002",
      "fragment": "остаток: 49.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000003",
      "fragment": "остаток: 13.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000004",
      "fragment": "остаток: 52.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000005",
      "fragment": "остаток: 50.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000006",
      "fragment": "остаток: 44.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000007",
      "fragment": "остаток: 37.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000008",
      "fragment": "остаток: 73.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000009",
      "fragment": "остаток: 20.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000010",
      "fragment": "остаток: 47.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000011",
      "fragment": "остаток: 19.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000012",
      "fragment": "остаток: 20.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000013",
      "fragment": "остаток: 60.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000014",
      "fragment": "остаток: 26.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000015",
      "fragment": "остаток: 11.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000016",
      "fragment": "остаток: 20.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000017",
      "fragment": "остаток: 12.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000018",
      "fragment": "остаток: 56.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000019",
      "fragment": "остаток: 41.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000020",
      "fragment": "остаток: 80.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000021",
      "fragment": "остаток: 40.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000022",
      "fragment": "остаток: 35.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000023",
      "fragment": "остаток: 64.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000024",
      "fragment": "остаток: 36.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000025",
      "fragment": "остаток: 20.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000026",
      "fragment": "остаток: 35.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000027",
      "fragment": "остаток: 3.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000028",
      "fragment": "остаток: 79.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000029",
      "fragment": "остаток: 75.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000030",
      "fragment": "остаток: 19.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000031",
      "fragment": "остаток: 38.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000032",
      "fragment": "остаток: 31.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000033",
      "fragment": "остаток: 56.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000034",
      "fragment": "остаток: 18.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000035",
      "fragment": "остаток: 41.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000036",
      "fragment": "остаток: 40.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000037",
      "fragment": "остаток: 57.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000038",
      "fragment": "остаток: 1.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000039",
      "fragment": "остаток: 64.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000040",
      "fragment": "остаток: 58.0"
    },
    {
      "kind": "matching_rules",
      "id": "matching_rules.csv",
      "fragment": null
    },
    {
      "kind": "regulation",
      "id": "regulation_matrix.json",
      "fragment": null
    }
  ],
  "missing_parameters": [],
  "human_review_required": true,
  "status": "требует проверки",
  "recommendations": [
    "Уточните параметры запроса: тип изделия, DN, PN, среда.",
    "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.6400000000000001,
  "parsed_query": {
    "original_query": "Посчитай запас деталей для ремонта трех таких же участков как UNIT-SYN-GAS-001, один полный комплект должен всегда оставаться на складе",
    "operations": [
      "repair",
      "inventory",
      "plan",
      "calculate"
    ],
    "item_types": [],
    "component_ids": [],
    "unit_ids": [
      "UNIT-SYN-GAS-001"
    ],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": null,
      "subtype": null,
      "designation": null,
      "name": null,
      "geometry": {
        "dn": null,
        "d1": null,
        "d2": null,
        "wall_thickness": null,
        "wall_thickness_2": null,
        "angle": null,
        "radius": null
      },
      "pressure": {
        "pn": null,
        "working_pressure_mpa": null,
        "test_pressure_mpa": null,
        "raw_value": null
      },
      "material": {
        "steel_grade": null,
        "strength_class": null,
        "standard": null
      },
      "environment": {
        "medium": null,
        "h2s_confirmed": null,
        "co2_confirmed": null,
        "temperature_min_c": null,
        "climate_version": null
      },
      "coating": null,
      "normative": {
        "gost_tu": null,
        "lnd_sections": []
      },
      "extraction": {
        "confidence": 0.0,
        "method": "hybrid",
        "missing_fields": [
          "item_type",
          "dn",
          "geometry",
          "material",
          "medium"
        ]
      },
      "sources": [
        {
          "type": "user_query",
          "file": null,
          "page": null,
          "row": null,
          "fragment": "Посчитай запас деталей для ремонта трех таких же участков как UNIT-SYN-GAS-001, один полный комплект должен всегда оставаться на складе"
        }
      ]
    },
    "cards": [
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": null,
        "subtype": null,
        "designation": null,
        "name": null,
        "geometry": {
          "dn": null,
          "d1": null,
          "d2": null,
          "wall_thickness": null,
          "wall_thickness_2": null,
          "angle": null,
          "radius": null
        },
        "pressure": {
          "pn": null,
          "working_pressure_mpa": null,
          "test_pressure_mpa": null,
          "raw_value": null
        },
        "material": {
          "steel_grade": null,
          "strength_class": null,
          "standard": null
        },
        "environment": {
          "medium": null,
          "h2s_confirmed": null,
          "co2_confirmed": null,
          "temperature_min_c": null,
          "climate_version": null
        },
        "coating": null,
        "normative": {
          "gost_tu": null,
          "lnd_sections": []
        },
        "extraction": {
          "confidence": 0.0,
          "method": "hybrid",
          "missing_fields": [
            "item_type",
            "dn",
            "geometry",
            "material",
            "medium"
          ]
        },
        "sources": [
          {
            "type": "user_query",
            "file": null,
            "page": null,
            "row": null,
            "fragment": "Посчитай запас деталей для ремонта трех таких же участков как UNIT-SYN-GAS-001, один полный комплект должен всегда оставаться на складе"
          }
        ]
      }
    ],
    "technical_filters": {},
    "stock_filters": {
      "quantity_min": 1,
      "stock_category": "main"
    },
    "quantity": null,
    "units_count": null,
    "length_m": null,
    "limit": null,
    "timeframe": null,
    "urgency": null,
    "sort_by": null,
    "on_stock": null,
    "not_installed": null,
    "proposed_changes": {},
    "impact_analysis": {},
    "unit_context": {
      "unit_id": "UNIT-SYN-GAS-001"
    },
    "component_context": {},
    "references": [
      "UNIT-SYN-GAS-001"
    ],
    "ambiguities": [],
    "required_agents": [
      "inventory",
      "knowledge",
      "plan",
      "rules",
      "search",
      "topology"
    ],
    "required_capabilities": [
      "calculation",
      "inventory",
      "maintenance_planning",
      "repair_planning",
      "topology"
    ],
    "confidence": 0.6400000000000001,
    "confidence_details": {
      "operations": 1.0,
      "card": 0.5,
      "ambiguities": 1.0
    },
    "intents": [
      "PLAN_REPAIR",
      "CHECK_STOCK"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "PLAN_REPAIR": [],
      "CHECK_STOCK": []
    },
    "params": {
      "unit_id": "UNIT-SYN-GAS-001"
    },
    "primary_intent": "PLAN_REPAIR",
    "groups": [
      {
        "group": "СКЛАД",
        "score": 2,
        "confidence": 0.667,
        "matched": [
          "склад",
          "запас"
        ]
      },
      {
        "group": "РЕМОНТ",
        "score": 1,
        "confidence": 0.333,
        "matched": [
          "ремонт"
        ]
      },
      {
        "group": "ПОИСК",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      },
      {
        "group": "ЗАМЕНА",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      },
      {
        "group": "АНАЛИЗ",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      },
      {
        "group": "ОБЪЯСНЕНИЕ",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      },
      {
        "group": "ДОКУМЕНТЫ",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      }
    ]
  },
  "review_verdict": "pass",
  "review_issues": [],
  "verification_verdict": "pass",
  "verification_reasons": [],
  "mode_refined": "auto",
  "llm_refine_failed": null,
  "llm_tokens_used": null
}
========================================================================

>>> Время выполнения: 42162 мс
