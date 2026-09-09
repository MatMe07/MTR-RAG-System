Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 15:48:13,016 INFO    | mtr.agent.executor               | [Executor] Execute query='Найди замену задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет' mode=auto request_id=None
2026-09-09 15:48:13,017 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 15:48:13,299 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.94 operations=['replace', 'inventory', 'search'] item_types=['задвижка'] technical_filters={'item_type': 'задвижка', 'dn': 150, 'pn': 40.0, 'working_pressure_mpa': 4.0, 'raw_value': 'PN40', 'medium': 'H2S', 'h2s_confirmed': True} ambiguities=[] (282ms)
2026-09-09 15:48:13,313 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['FIND_ALTERNATIVE', 'FIND_BY_PARAMS', 'CHECK_STOCK'] missing={'FIND_ALTERNATIVE': [], 'FIND_BY_PARAMS': [], 'CHECK_STOCK': []}
2026-09-09 15:48:13,322 INFO    | mtr.agent.executor               | [Executor] Intent resolved: replacement
2026-09-09 15:48:13,322 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 15:48:13,553 INFO    | mtr.repository                   | DbRepository: loaded 1000 MTR items from DB
2026-09-09 15:48:13,571 INFO    | mtr.repository                   | DbRepository: loaded 1000 CandidateItems for stock lookup
2026-09-09 15:48:13,624 INFO    | mtr.repository                   | DbRepository: catalog built with 1000 cards
2026-09-09 15:48:13,875 INFO    | mtr.agent.tools                  | [graph_search] Found 12 components, 12 targets in 250ms
2026-09-09 15:48:13,876 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 15:48:13,890 INFO    | mtr.agent.tools                  | [catalog_search] Found 9 candidates (from 1000 cards) in 14ms
2026-09-09 15:48:13,923 INFO    | mtr.agent.tools                  | [stock_query] Checked 9 items (kept 9) in 32ms
2026-09-09 15:48:13,926 INFO    | mtr.agent.tools                  | [rules_engine] Scored 9 candidates in 0ms
2026-09-09 15:48:13,930 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['DN', 'PN', 'среда', 'марка стали']
Запрос: Найди замену задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет
Найденные детали:
- Задвижка клиновая DN150 PN40: 80% (потенциальный аналог)
- Задвижка шиберная DN150 PN40: 80% (потенциальный аналог)
- Задвижка шиберная DN150 PN40: 80% (потенциальный аналог)
- Задвижка шиберная DN150 PN40: 60% (не соответствует)
- Задвижка шиберная DN150 PN40: 60% (не соответствует)
Результаты проверок: Совпало: тип изделия, DN, PN, среда
Предупреждения: ['Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.', 'Большее значение PN не гарантирует совместимость задвижки с фланцами и соседними деталями.', 'Изменение DN является изменением узла и не должно утверждаться автоматически.', 'Для типа «задвижка» не указаны обязательные параметры: марка стали. Уточните их для точного подбора.']
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
2026-09-09 15:48:16,167 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-09 15:48:22,620 INFO    | mtr.agent.executor               | [Executor] Graph finished in 9298ms: components=25 sources=79 warnings=3 tools_used=['graph_search', 'catalog_search', 'stock_query', 'impact_analyzer', 'maintenance_planner', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 15:48:22,620 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 15:48:22,663 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 15:48:22,663 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Найди замену задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет",
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
  "explanation": "Рекомендую рассмотреть клиновую или шиберную задвижку DN150 PN40 из найденных вариантов как геометрический аналог. Перед установкой необходимо уточнить марку стали и получить паспорт/ТУ, подтверждающие стойкость к H₂S и коррозионной среде. Основные риски — невозможность гарантировать устойчивость к сероводороду только по совпадению DN и PN, а также возможная несовместимость фланцев из‑за различий в PN или отсутствия защитного покрытия. Поскольку критический параметр «марка стали» не подтверждён, замену можно утверждать только после предоставления соответствующей документации.",
  "components": [
    {
      "mtr_code": "MTR-SYN-REG-000615",
      "ksm_code": "KSM-SYN-REG-000615",
      "name": "Задвижка клиновая DN150 PN40",
      "item_type": "задвижка",
      "quantity": 77.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 77.0; оценка правил",
      "source_id": "MTR-SYN-REG-000615",
      "unit_id": null,
      "match_score": 0.8,
      "match_percent": 80,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000673",
      "ksm_code": "KSM-SYN-REG-000673",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 78.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 78.0; оценка правил",
      "source_id": "MTR-SYN-REG-000673",
      "unit_id": null,
      "match_score": 0.8,
      "match_percent": 80,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000686",
      "ksm_code": "KSM-SYN-REG-000686",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 80.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 80.0; оценка правил",
      "source_id": "MTR-SYN-REG-000686",
      "unit_id": null,
      "match_score": 0.8,
      "match_percent": 80,
      "tz_status": "потенциальный аналог",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN",
        "среда"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000648",
      "ksm_code": "KSM-SYN-REG-000648",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 64.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 64.0; оценка правил",
      "source_id": "MTR-SYN-REG-000648",
      "unit_id": null,
      "match_score": 0.6,
      "match_percent": 60,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000692",
      "ksm_code": "KSM-SYN-REG-000692",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 15.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 15.0; оценка правил",
      "source_id": "MTR-SYN-REG-000692",
      "unit_id": null,
      "match_score": 0.6,
      "match_percent": 60,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000706",
      "ksm_code": "KSM-SYN-REG-000706",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 24.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 24.0; оценка правил",
      "source_id": "MTR-SYN-REG-000706",
      "unit_id": null,
      "match_score": 0.6,
      "match_percent": 60,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000716",
      "ksm_code": "KSM-SYN-REG-000716",
      "name": "Задвижка клиновая DN150 PN40",
      "item_type": "задвижка",
      "quantity": 65.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 65.0; оценка правил",
      "source_id": "MTR-SYN-REG-000716",
      "unit_id": null,
      "match_score": 0.6,
      "match_percent": 60,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000729",
      "ksm_code": "KSM-SYN-REG-000729",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 65.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 65.0; оценка правил",
      "source_id": "MTR-SYN-REG-000729",
      "unit_id": null,
      "match_score": 0.6,
      "match_percent": 60,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000732",
      "ksm_code": "KSM-SYN-REG-000732",
      "name": "Задвижка шиберная DN150 PN40",
      "item_type": "задвижка",
      "quantity": 26.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 26.0; оценка правил",
      "source_id": "MTR-SYN-REG-000732",
      "unit_id": null,
      "match_score": 0.6,
      "match_percent": 60,
      "tz_status": "не соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "PN"
      ],
      "mismatched_params": [
        "среда"
      ],
      "missing_params": []
    },
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
    "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
    "Большее значение PN не гарантирует совместимость задвижки с фланцами и соседними деталями.",
    "Изменение DN является изменением узла и не должно утверждаться автоматически.",
    "Для типа «задвижка» не указаны обязательные параметры: марка стали. Уточните их для точного подбора."
  ],
  "warning_categories": {
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
      "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN."
    ],
    "Прочее": [
      "Большее значение PN не гарантирует совместимость задвижки с фланцами и соседними деталями.",
      "Изменение DN является изменением узла и не должно утверждаться автоматически.",
      "Для типа «задвижка» не указаны обязательные параметры: марка стали. Уточните их для точного подбора."
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
      "id": "MTR-SYN-REG-000615",
      "fragment": "Задвижка клиновая DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000615",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000673",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000673",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000686",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000686",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000648",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000648",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000692",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000692",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000706",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000706",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000716",
      "fragment": "Задвижка клиновая DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000716",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000729",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000729",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000732",
      "fragment": "Задвижка шиберная DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000732",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000615",
      "fragment": "остаток: 77.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000673",
      "fragment": "остаток: 78.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000686",
      "fragment": "остаток: 80.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000648",
      "fragment": "остаток: 64.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000692",
      "fragment": "остаток: 15.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000706",
      "fragment": "остаток: 24.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000716",
      "fragment": "остаток: 65.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000729",
      "fragment": "остаток: 65.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000732",
      "fragment": "остаток: 26.0"
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
  "expert_review_id": "req-2026-09-09-36fb",
  "parsed_confidence": 0.94,
  "parsed_query": {
    "original_query": "Найди замену задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет",
    "operations": [
      "replace",
      "inventory",
      "search"
    ],
    "item_types": [
      "задвижка"
    ],
    "component_ids": [],
    "unit_ids": [],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": "задвижка",
      "subtype": null,
      "designation": "DN150 PN40 H2S",
      "name": "задвижка DN150 PN40",
      "geometry": {
        "dn": 150.0,
        "d1": null,
        "d2": null,
        "wall_thickness": null,
        "wall_thickness_2": null,
        "angle": null,
        "radius": null
      },
      "pressure": {
        "pn": 40.0,
        "working_pressure_mpa": 4.0,
        "test_pressure_mpa": null,
        "raw_value": "PN40"
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
          "geometry",
          "material"
        ]
      },
      "sources": [
        {
          "type": "user_query",
          "file": null,
          "page": null,
          "row": null,
          "fragment": "Найди замену задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет"
        }
      ]
    },
    "cards": [
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "задвижка",
        "subtype": null,
        "designation": "DN150 PN40 H2S",
        "name": "задвижка DN150 PN40",
        "geometry": {
          "dn": 150.0,
          "d1": null,
          "d2": null,
          "wall_thickness": null,
          "wall_thickness_2": null,
          "angle": null,
          "radius": null
        },
        "pressure": {
          "pn": 40.0,
          "working_pressure_mpa": 4.0,
          "test_pressure_mpa": null,
          "raw_value": "PN40"
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
            "geometry",
            "material"
          ]
        },
        "sources": [
          {
            "type": "user_query",
            "file": null,
            "page": null,
            "row": null,
            "fragment": "Найди замену задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет"
          }
        ]
      }
    ],
    "technical_filters": {
      "item_type": "задвижка",
      "dn": 150,
      "pn": 40.0,
      "working_pressure_mpa": 4.0,
      "raw_value": "PN40",
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
    "on_stock": null,
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
      "search"
    ],
    "required_capabilities": [
      "inventory",
      "replacement_matching",
      "search"
    ],
    "confidence": 0.94,
    "confidence_details": {
      "operations": 0.8,
      "card": 0.8,
      "ambiguities": 1.0
    },
    "intents": [
      "FIND_ALTERNATIVE",
      "FIND_BY_PARAMS",
      "CHECK_STOCK"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "FIND_ALTERNATIVE": [],
      "FIND_BY_PARAMS": [],
      "CHECK_STOCK": []
    },
    "params": {
      "item_type": "задвижка",
      "dn": 150,
      "pn": 40.0,
      "medium": "H2S"
    },
    "primary_intent": "FIND_ALTERNATIVE",
    "groups": [
      {
        "group": "ПОИСК",
        "score": 1,
        "confidence": 0.5,
        "matched": [
          "найди"
        ]
      },
      {
        "group": "СКЛАД",
        "score": 1,
        "confidence": 0.5,
        "matched": [
          "склад"
        ]
      },
      {
        "group": "РЕМОНТ",
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

>>> Время выполнения: 9647 мс
