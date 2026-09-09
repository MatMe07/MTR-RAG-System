Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-07 18:29:10,772 INFO    | mtr.agent.executor               | [Executor] Execute query='Какой аналог отвода 90 426 на 10 подойдет для H2S, покажи сначала то, что есть на складе' mode=auto request_id=None
2026-09-07 18:29:10,772 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-07 18:29:10,994 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.97 operations=['replace', 'inventory', 'check', 'search'] item_types=['отвод'] technical_filters={'item_type': 'отвод', 'dn': 426.0, 'wall_thickness': 10.0, 'angle': 90.0, 'medium': 'H2S', 'h2s_confirmed': True} ambiguities=[] (222ms)
2026-09-07 18:29:11,006 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['FIND_BY_PARAMS', 'FIND_ALTERNATIVE', 'CHECK_STOCK'] missing={'FIND_BY_PARAMS': [], 'FIND_ALTERNATIVE': ['pn'], 'CHECK_STOCK': []}
2026-09-07 18:29:11,013 INFO    | mtr.agent.executor               | [Executor] Intent resolved: replacement
2026-09-07 18:29:11,014 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-07 18:29:11,213 INFO    | mtr.repository                   | DbRepository: loaded 1000 MTR items from DB
2026-09-07 18:29:11,227 INFO    | mtr.repository                   | DbRepository: loaded 1000 CandidateItems for stock lookup
2026-09-07 18:29:11,274 INFO    | mtr.repository                   | DbRepository: catalog built with 1000 cards
2026-09-07 18:29:11,513 INFO    | mtr.agent.tools                  | [graph_search] Found 12 components, 12 targets in 237ms
2026-09-07 18:29:11,514 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-07 18:29:11,528 INFO    | mtr.agent.tools                  | [catalog_search] Found 11 candidates (from 1000 cards) in 13ms
2026-09-07 18:29:11,580 INFO    | mtr.agent.tools                  | [stock_query] Checked 11 items (kept 11) in 51ms
2026-09-07 18:29:11,584 INFO    | mtr.agent.tools                  | [rules_engine] Scored 11 candidates in 0ms
2026-09-07 18:29:11,589 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 4ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['марка стали', 'среда']
Запрос: Какой аналог отвода 90 426 на 10 подойдет для H2S, покажи сначала то, что есть на складе
Найденные детали:
- ОКШ 90-426x10 13ХФА: 100% (соответствует)
- ОКШ 90-426x10 13ХФА: 100% (соответствует)
- ОКШ 90-426x10 13ХФА: 100% (соответствует)
- ОКШ 90-426x10 13ХФА: 100% (соответствует)
- ОКШ 90-426x10 09ГСФ: 83% (потенциальный аналог)
Результаты проверок: Совпало: тип изделия, DN, стенка, угол, среда
Предупреждения: ['Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'Для типа «отвод» не указаны обязательные параметры: марка стали. Уточните их для точного подбора.']
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
2026-09-07 18:29:13,444 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-07 18:29:31,775 INFO    | mtr.agent.executor               | [Executor] Graph finished in 20761ms: components=27 sources=85 warnings=3 tools_used=['graph_search', 'catalog_search', 'stock_query', 'impact_analyzer', 'maintenance_planner', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-07 18:29:31,775 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-07 18:29:31,823 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-07 18:29:31,824 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Какой аналог отвода 90 426 на 10 подойдет для H2S, покажи сначала то, что есть на складе",
  "intent": "replacement",
  "intent_label": "Подбор замены",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "catalog_search",
    "stock_query",
    "impact_analyzer",
    "maintenance_planner",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "На складе имеется отвод ОКШ 90‑426х10 марки 13ХФА, который полностью совпадает по геометрии (тип, DN, стенка, угол) и заявленной среде. Однако в предоставленных данных не указана марка стали – один из критических параметров, необходимый для точного подбора аналога в среде H₂S, поэтому его следует уточнить в паспорте, ТУ или проектной документации изделия. Рекомендуем взять этот отвод, но перед установкой обязательно проверить документацию на подтверждение устойчивости к H₂S и наличие защитного покрытия. Если марка окажется несоответствующей, потребуется поиск другого аналога с подтверждённой коррозионной стойкостью.",
  "components": [
    {
      "mtr_code": null,
      "ksm_code": null,
      "name": "Проверка",
      "item_type": null,
      "quantity": null,
      "status": "required",
      "detail": "проверить совместимость материалов и уплотнений со средой H2S",
      "source_id": null,
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": null,
      "ksm_code": null,
      "name": "материал деталей",
      "item_type": null,
      "quantity": null,
      "status": "затронуто",
      "detail": "соседний узел при замене",
      "source_id": null,
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": null,
      "ksm_code": null,
      "name": "уплотнения",
      "item_type": null,
      "quantity": null,
      "status": "затронуто",
      "detail": "соседний узел при замене",
      "source_id": null,
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": null,
      "ksm_code": null,
      "name": "Расходные материалы",
      "item_type": null,
      "quantity": null,
      "status": "комплект",
      "detail": "прокладки, крепёж, материалы по регламенту ТОиР",
      "source_id": null,
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000231",
      "ksm_code": "KSM-SYN-REG-000231",
      "name": "ОКШ 90-426x10 13ХФА",
      "item_type": "отвод",
      "quantity": 65.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 65.0; оценка правил",
      "source_id": "MTR-SYN-REG-000231",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000249",
      "ksm_code": "KSM-SYN-REG-000249",
      "name": "ОКШ 90-426x10 13ХФА",
      "item_type": "отвод",
      "quantity": 58.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 58.0; оценка правил",
      "source_id": "MTR-SYN-REG-000249",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000330",
      "ksm_code": "KSM-SYN-REG-000330",
      "name": "ОКШ 90-426x10 13ХФА",
      "item_type": "отвод",
      "quantity": 52.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 52.0; оценка правил",
      "source_id": "MTR-SYN-REG-000330",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000372",
      "ksm_code": "KSM-SYN-REG-000372",
      "name": "ОКШ 90-426x10 13ХФА",
      "item_type": "отвод",
      "quantity": 26.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 26.0; оценка правил",
      "source_id": "MTR-SYN-REG-000372",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000323",
      "ksm_code": "KSM-SYN-REG-000323",
      "name": "ОКШ 90-426x10 09ГСФ",
      "item_type": "отвод",
      "quantity": 71.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 71.0; оценка правил",
      "source_id": "MTR-SYN-REG-000323",
      "unit_id": null,
      "match_score": 0.8333333333333334,
      "match_percent": 83,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000358",
      "ksm_code": "KSM-SYN-REG-000358",
      "name": "ОКШ 90-426x10 09Г2С",
      "item_type": "отвод",
      "quantity": 68.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 68.0; оценка правил",
      "source_id": "MTR-SYN-REG-000358",
      "unit_id": null,
      "match_score": 0.8333333333333334,
      "match_percent": 83,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000404",
      "ksm_code": "KSM-SYN-REG-000404",
      "name": "ОКШ 90-426x10 13ХФА",
      "item_type": "отвод",
      "quantity": 18.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 18.0; оценка правил",
      "source_id": "MTR-SYN-REG-000404",
      "unit_id": null,
      "match_score": 0.8333333333333334,
      "match_percent": 83,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000430",
      "ksm_code": "KSM-SYN-REG-000430",
      "name": "ОКШ 90-426x10 09ГСФ",
      "item_type": "отвод",
      "quantity": 35.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 35.0; оценка правил",
      "source_id": "MTR-SYN-REG-000430",
      "unit_id": null,
      "match_score": 0.8333333333333334,
      "match_percent": 83,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000287",
      "ksm_code": "KSM-SYN-REG-000287",
      "name": "ОКШ 90-426x10 09ГСФ",
      "item_type": "отвод",
      "quantity": 7.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 7.0; оценка правил",
      "source_id": "MTR-SYN-REG-000287",
      "unit_id": null,
      "match_score": 0.6666666666666666,
      "match_percent": 67,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000354",
      "ksm_code": "KSM-SYN-REG-000354",
      "name": "ОКШ 90-426x10 09ГСФ",
      "item_type": "отвод",
      "quantity": 51.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 51.0; оценка правил",
      "source_id": "MTR-SYN-REG-000354",
      "unit_id": null,
      "match_score": 0.6666666666666666,
      "match_percent": 67,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000405",
      "ksm_code": "KSM-SYN-REG-000405",
      "name": "ОКШ 90-426x10 09Г2С",
      "item_type": "отвод",
      "quantity": 38.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 38.0; оценка правил",
      "source_id": "MTR-SYN-REG-000405",
      "unit_id": null,
      "match_score": 0.6666666666666666,
      "match_percent": 67,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000008",
      "ksm_code": "KSM-SYN-REG-000008",
      "name": "Труба бесшовная горячедеформированная 108x6 20",
      "item_type": "труба",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-007",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000223",
      "ksm_code": "KSM-SYN-REG-000223",
      "name": "ОКШ 90-76x4 09ГСФ",
      "item_type": "отвод",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-008",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000444",
      "ksm_code": "KSM-SYN-REG-000444",
      "name": "Переход концентрический 108x4-76x4 13ХФА",
      "item_type": "переход",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-009",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000593",
      "ksm_code": "KSM-SYN-REG-000593",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-010",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000746",
      "ksm_code": "KSM-SYN-REG-000746",
      "name": "Заглушка эллиптическая приварная 377x12 13ХФА",
      "item_type": "заглушка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-011",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000876",
      "ksm_code": "KSM-SYN-REG-000876",
      "name": "Тройник переходный 426x12-325x10 13ХФА",
      "item_type": "тройник",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-012",
      "unit_id": "UNIT-SYN-H2S-001",
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
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-019",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000225",
      "ksm_code": "KSM-SYN-REG-000225",
      "name": "ОКШ 90-133x6 09ГСФ",
      "item_type": "отвод",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-020",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000441",
      "ksm_code": "KSM-SYN-REG-000441",
      "name": "Переход эксцентрический 133x5-89x4 20",
      "item_type": "переход",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-021",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000594",
      "ksm_code": "KSM-SYN-REG-000594",
      "name": "Задвижка шиберная DN250 PN100",
      "item_type": "задвижка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-022",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000741",
      "ksm_code": "KSM-SYN-REG-000741",
      "name": "Заглушка эллиптическая приварная 76x4 09ГСФ",
      "item_type": "заглушка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": null,
      "source_id": "COMP-SYN-023",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000880",
      "ksm_code": "KSM-SYN-REG-000880",
      "name": "Тройник переходный 89x4-57x3 20",
      "item_type": "тройник",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": null,
      "source_id": "COMP-SYN-024",
      "unit_id": "UNIT-SYN-MIX-001",
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
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-007",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000223",
      "ksm_code": "KSM-SYN-REG-000223",
      "name": "ОКШ 90-76x4 09ГСФ",
      "item_type": "отвод",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-008",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000444",
      "ksm_code": "KSM-SYN-REG-000444",
      "name": "Переход концентрический 108x4-76x4 13ХФА",
      "item_type": "переход",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-009",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000593",
      "ksm_code": "KSM-SYN-REG-000593",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-010",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000746",
      "ksm_code": "KSM-SYN-REG-000746",
      "name": "Заглушка эллиптическая приварная 377x12 13ХФА",
      "item_type": "заглушка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-011",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000876",
      "ksm_code": "KSM-SYN-REG-000876",
      "name": "Тройник переходный 426x12-325x10 13ХФА",
      "item_type": "тройник",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-012",
      "unit_id": "UNIT-SYN-H2S-001",
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
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-019",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000225",
      "ksm_code": "KSM-SYN-REG-000225",
      "name": "ОКШ 90-133x6 09ГСФ",
      "item_type": "отвод",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-020",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000441",
      "ksm_code": "KSM-SYN-REG-000441",
      "name": "Переход эксцентрический 133x5-89x4 20",
      "item_type": "переход",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-021",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000594",
      "ksm_code": "KSM-SYN-REG-000594",
      "name": "Задвижка шиберная DN250 PN100",
      "item_type": "задвижка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "работа: обслуживание/проверка",
      "source_id": "COMP-SYN-022",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000741",
      "ksm_code": "KSM-SYN-REG-000741",
      "name": "Заглушка эллиптическая приварная 76x4 09ГСФ",
      "item_type": "заглушка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": null,
      "source_id": "COMP-SYN-023",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000880",
      "ksm_code": "KSM-SYN-REG-000880",
      "name": "Тройник переходный 89x4-57x3 20",
      "item_type": "тройник",
      "quantity": null,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": null,
      "source_id": "COMP-SYN-024",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    }
  ],
  "warnings": [
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "Для типа «отвод» не указаны обязательные параметры: марка стали. Уточните их для точного подбора."
  ],
  "warning_categories": {
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД."
    ],
    "Прочее": [
      "Для типа «отвод» не указаны обязательные параметры: марка стали. Уточните их для точного подбора."
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
      "id": "COMP-SYN-007",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-007",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-008",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-008",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-009",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-009",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-010",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-010",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-011",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-011",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-012",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-012",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-019",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-019",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-020",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-020",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-021",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-021",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-022",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-022",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-023",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-023",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-024",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-024",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "maintenance_history",
      "id": "UNIT-SYN-H2S-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)"
    },
    {
      "kind": "maintenance_history",
      "id": "UNIT-SYN-MIX-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000231",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000231",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000249",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000249",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000330",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000330",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000372",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000372",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000323",
      "fragment": "ОКШ 90-426x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000323",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000358",
      "fragment": "ОКШ 90-426x10 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000358",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000404",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000404",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000430",
      "fragment": "ОКШ 90-426x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000430",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000287",
      "fragment": "ОКШ 90-426x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000287",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000354",
      "fragment": "ОКШ 90-426x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000354",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000405",
      "fragment": "ОКШ 90-426x10 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000405",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000231",
      "fragment": "остаток: 65.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000249",
      "fragment": "остаток: 58.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000330",
      "fragment": "остаток: 52.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000372",
      "fragment": "остаток: 26.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000323",
      "fragment": "остаток: 71.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000358",
      "fragment": "остаток: 68.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000404",
      "fragment": "остаток: 18.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000430",
      "fragment": "остаток: 35.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000287",
      "fragment": "остаток: 7.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000354",
      "fragment": "остаток: 51.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000405",
      "fragment": "остаток: 38.0"
    },
    {
      "kind": "project_documentation",
      "id": null,
      "fragment": "оценка влияния требует проектной схемы"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-007",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-008",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-009",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-010",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-011",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-012",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-019",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-020",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-021",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-022",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "maintenance_policy",
      "id": "MTR-TOIR-POLICY-001",
      "fragment": "регламент ТОиР (черновой)"
    },
    {
      "kind": "maintenance_history",
      "id": "MTR-TOIR-HISTORY-001",
      "fragment": "история эксплуатации участка (МВП: расчётно)"
    },
    {
      "kind": "matching_rules",
      "id": "matching_rules.csv",
      "fragment": null
    },
    {
      "kind": "TU",
      "id": "gas_h2s",
      "fragment": "технические условия на изделие"
    },
    {
      "kind": "internal_lnd",
      "id": "gas_h2s",
      "fragment": "внутренний ЛНД по применимости к среде"
    },
    {
      "kind": "expert_decisions",
      "id": "gas_h2s",
      "fragment": "заключение эксперта по среде"
    },
    {
      "kind": "passport",
      "id": "gas_h2s",
      "fragment": "паспорт изделия (требование профиля среды)"
    },
    {
      "kind": "TU",
      "id": "gas_h2s_co2",
      "fragment": "технические условия на изделие"
    },
    {
      "kind": "internal_lnd",
      "id": "gas_h2s_co2",
      "fragment": "внутренний ЛНД по применимости к среде"
    },
    {
      "kind": "expert_decisions",
      "id": "gas_h2s_co2",
      "fragment": "заключение эксперта по среде"
    },
    {
      "kind": "passport",
      "id": "gas_h2s_co2",
      "fragment": "паспорт изделия (требование профиля среды)"
    },
    {
      "kind": "regulation",
      "id": "regulation_matrix.json",
      "fragment": null
    }
  ],
  "missing_parameters": [],
  "human_review_required": true,
  "status": "требует экспертной проверки",
  "recommendations": [
    "Требуется экспертная проверка: критические параметры не подтверждены.",
    "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
  ],
  "expert_review_id": "req-2026-09-07-3d9a",
  "parsed_confidence": 0.97,
  "parsed_query": {
    "original_query": "Какой аналог отвода 90 426 на 10 подойдет для H2S, покажи сначала то, что есть на складе",
    "operations": [
      "replace",
      "inventory",
      "check",
      "search"
    ],
    "item_types": [
      "отвод"
    ],
    "component_ids": [],
    "unit_ids": [],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": "отвод",
      "subtype": null,
      "designation": "DN426 δ10 90° H2S",
      "name": "отвод 90° DN426",
      "geometry": {
        "dn": 426.0,
        "d1": null,
        "d2": null,
        "wall_thickness": 10.0,
        "wall_thickness_2": null,
        "angle": 90.0,
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
        "medium": "H2S",
        "h2s_confirmed": true,
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
        "method": "user_query",
        "missing_fields": [
          "material"
        ]
      },
      "sources": [
        {
          "type": "user_query",
          "file": null,
          "page": null,
          "row": null,
          "fragment": "Какой аналог отвода 90 426 на 10 подойдет для H2S, покажи сначала то, что есть на складе"
        }
      ]
    },
    "cards": [
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "отвод",
        "subtype": null,
        "designation": "DN426 δ10 90° H2S",
        "name": "отвод 90° DN426",
        "geometry": {
          "dn": 426.0,
          "d1": null,
          "d2": null,
          "wall_thickness": 10.0,
          "wall_thickness_2": null,
          "angle": 90.0,
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
          "medium": "H2S",
          "h2s_confirmed": true,
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
          "method": "user_query",
          "missing_fields": [
            "material"
          ]
        },
        "sources": [
          {
            "type": "user_query",
            "file": null,
            "page": null,
            "row": null,
            "fragment": "Какой аналог отвода 90 426 на 10 подойдет для H2S, покажи сначала то, что есть на складе"
          }
        ]
      }
    ],
    "technical_filters": {
      "item_type": "отвод",
      "dn": 426.0,
      "wall_thickness": 10.0,
      "angle": 90.0,
      "medium": "H2S",
      "h2s_confirmed": true
    },
    "stock_filters": {
      "stock_category": "main"
    },
    "quantity": null,
    "units_count": null,
    "length_m": null,
    "limit": null,
    "timeframe": null,
    "urgency": null,
    "sort_by": null,
    "on_stock": true,
    "not_installed": null,
    "proposed_changes": {},
    "impact_analysis": {
      "required_checks": [
        "проверить совместимость со средой"
      ]
    },
    "unit_context": {
      "medium": "H2S"
    },
    "component_context": {},
    "references": [],
    "ambiguities": [],
    "required_agents": [
      "inventory",
      "rules",
      "search"
    ],
    "required_capabilities": [
      "compatibility_check",
      "inventory",
      "replacement_matching",
      "search"
    ],
    "confidence": 0.97,
    "confidence_details": {
      "operations": 1.0,
      "card": 0.9,
      "ambiguities": 1.0
    },
    "intents": [
      "FIND_BY_PARAMS",
      "FIND_ALTERNATIVE",
      "CHECK_STOCK"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "FIND_BY_PARAMS": [],
      "FIND_ALTERNATIVE": [
        "pn"
      ],
      "CHECK_STOCK": []
    },
    "params": {
      "item_type": "отвод",
      "dn": 426.0,
      "angle": 90.0,
      "medium": "H2S"
    },
    "primary_intent": "FIND_BY_PARAMS",
    "groups": [
      {
        "group": "ПОИСК",
        "score": 2,
        "confidence": 0.5,
        "matched": [
          "покажи",
          "какой"
        ]
      },
      {
        "group": "СКЛАД",
        "score": 1,
        "confidence": 0.25,
        "matched": [
          "склад"
        ]
      },
      {
        "group": "ЗАМЕНА",
        "score": 1,
        "confidence": 0.25,
        "matched": [
          "аналог"
        ]
      },
      {
        "group": "РЕМОНТ",
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
  "llm_refine_failed": null
}
========================================================================

>>> Время выполнения: 21052 мс
