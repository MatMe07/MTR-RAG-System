Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 16:24:06,658 INFO    | mtr.agent.executor               | [Executor] Execute query='Найди паспорта и ТУ для всех деталей участка UNIT-SYN-H2S-001 и покажи чего не хватает' mode=auto request_id=None
2026-09-09 16:24:06,658 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 16:24:06,932 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.59 operations=['check', 'search', 'document'] item_types=[] technical_filters={'medium': 'H2S', 'h2s_confirmed': True} ambiguities=[] (273ms)
2026-09-09 16:24:06,947 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['CHECK_STOCK', 'FIND_DOCUMENTS', 'FIND_STANDARDS'] missing={'CHECK_STOCK': [], 'FIND_DOCUMENTS': [], 'FIND_STANDARDS': []}
2026-09-09 16:24:06,957 INFO    | mtr.agent.executor               | [Executor] Intent resolved: document_search
2026-09-09 16:24:06,957 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 16:24:07,373 INFO    | mtr.agent.tools                  | [graph_search] Found 6 components, 6 targets in 161ms
2026-09-09 16:24:07,374 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 16:24:07,393 INFO    | mtr.agent.tools                  | [catalog_search] Found 40 candidates (from 1000 cards) in 19ms
2026-09-09 16:24:07,395 INFO    | mtr.agent.tools                  | [rules_engine] Scored 40 candidates in 1ms
2026-09-09 16:24:07,401 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 4ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['PN', 'угол', 'стенка', 'материал', 'среда', 'DN', 'тип изделия', 'марка стали']
Запрос: Найди паспорта и ТУ для всех деталей участка UNIT-SYN-H2S-001 и покажи чего не хватает
Найденные детали:
- Труба бесшовная горячедеформированная 89x6 13ХФА: 100% (соответствует)
- Труба бесшовная горячедеформированная 57x4 13ХФА: 100% (соответствует)
- Труба бесшовная горячедеформированная 273x10 13ХФА: 100% (соответствует)
- Труба бесшовная горячедеформированная 108x6 13ХФА: 100% (соответствует)
- Труба бесшовная горячедеформированная 108x6 13ХФА: 100% (соответствует)
Результаты проверок: Совпало: среда
Предупреждения: ['Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'Наличие позиции на складе не подтверждает ее пригодность для H2S.', 'В демонстрационном наборе паспорта могут отсутствовать, это нужно сообщать явно.']
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
2026-09-09 16:24:09,392 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-09 16:24:25,672 INFO    | mtr.agent.executor               | [Executor] Graph finished in 18715ms: components=46 sources=106 warnings=1 tools_used=['graph_search', 'catalog_search', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 16:24:25,672 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 16:24:25,707 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 16:24:25,707 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Найди паспорта и ТУ для всех деталей участка UNIT-SYN-H2S-001 и покажи чего не хватает",
  "intent": "document_search",
  "intent_label": "Поиск документов",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "catalog_search",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "Среди всех критических параметров (PN, угол, стенка, DN, тип изделия, марка стали) подтверждено только соответствие среды; остальные показатели пока не проверены. Необходимо запросить паспорта и технические условия на каждую трубу, убедиться в их PN, толщине стенки, диаметре и марке стали, а также уточнить наличие H₂S‑устойчивого покрытия или материала. Без такой проверки существует риск применения труб, не рассчитанных на работу в сероводородной среде, что может привести к коррозионному растрескиванию и аварийным отказам. Обратите внимание, что в демонстрационном наборе паспорта могут отсутствовать — этот факт следует указать явно при оформлении документации.",
  "components": [
    {
      "mtr_code": "MTR-SYN-REG-000011",
      "ksm_code": "KSM-SYN-REG-000011",
      "name": "Труба бесшовная горячедеформированная 89x6 13ХФА",
      "item_type": "труба",
      "quantity": 19.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000011",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000013",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000014",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000015",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000024",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000027",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000029",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000032",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000033",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000036",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "среда"
      ],
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "mtr_code": "MTR-SYN-REG-000008",
      "ksm_code": "KSM-SYN-REG-000008",
      "name": "Труба бесшовная горячедеформированная 108x6 20",
      "item_type": "труба",
      "quantity": null,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
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
      "detail": null,
      "source_id": "COMP-SYN-012",
      "unit_id": "UNIT-SYN-H2S-001",
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
    "Наличие позиции на складе не подтверждает ее пригодность для H2S.",
    "В демонстрационном наборе паспорта могут отсутствовать, это нужно сообщать явно."
  ],
  "warning_categories": {
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
      "Наличие позиции на складе не подтверждает ее пригодность для H2S."
    ],
    "Достоверность данных": [
      "В демонстрационном наборе паспорта могут отсутствовать, это нужно сообщать явно."
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
      "kind": "maintenance_history",
      "id": "UNIT-SYN-H2S-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)"
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
      "id": "MTR-SYN-REG-000046",
      "fragment": "Труба бесшовная горячедеформированная 76x5 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000046",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000061",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000061",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000087",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000087",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000093",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000093",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000098",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000098",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000103",
      "fragment": "Труба бесшовная горячедеформированная 426x14 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000103",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000105",
      "fragment": "Труба бесшовная горячедеформированная 530x16 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000105",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000116",
      "fragment": "Труба электросварная спиральношовная 219x8 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000116",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000125",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000125",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000131",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000131",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000135",
      "fragment": "Труба электросварная прямошовная 159x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000135",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000146",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000146",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000149",
      "fragment": "Труба электросварная спиральношовная 530x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000149",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000154",
      "fragment": "Труба электросварная прямошовная 630x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000154",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000179",
      "fragment": "Труба электросварная прямошовная 426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000179",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000195",
      "fragment": "Труба электросварная спиральношовная 820x14 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000195",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000208",
      "fragment": "Труба электросварная спиральношовная 426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000208",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000209",
      "fragment": "Труба электросварная спиральношовная 1020x16 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000209",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000226",
      "fragment": "ОКШ 90-57x3 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000226",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000229",
      "fragment": "ОКШ 45-273x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000229",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
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
      "id": "MTR-SYN-REG-000232",
      "fragment": "ОКШ 90-57x3 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000232",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000237",
      "fragment": "ОКШ 90-76x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000237",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000241",
      "fragment": "ОКШ 90-325x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000241",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000242",
      "fragment": "ОКШ 45-219x8 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000242",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000245",
      "fragment": "ОКШ 90-133x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000245",
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
      "id": "MTR-SYN-REG-000283",
      "fragment": "ОКШ 90-76x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000283",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000289",
      "fragment": "ОКШ 45-108x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000289",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
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
  "expert_review_id": "req-2026-09-09-0bb3",
  "parsed_confidence": 0.5900000000000001,
  "parsed_query": {
    "original_query": "Найди паспорта и ТУ для всех деталей участка UNIT-SYN-H2S-001 и покажи чего не хватает",
    "operations": [
      "check",
      "search",
      "document"
    ],
    "item_types": [],
    "component_ids": [],
    "unit_ids": [
      "UNIT-SYN-H2S-001"
    ],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": null,
      "subtype": null,
      "designation": "H2S",
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
        "method": "hybrid",
        "missing_fields": [
          "item_type",
          "dn",
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
          "fragment": "Найди паспорта и ТУ для всех деталей участка UNIT-SYN-H2S-001 и покажи чего не хватает"
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
        "designation": "H2S",
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
          "method": "hybrid",
          "missing_fields": [
            "item_type",
            "dn",
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
            "fragment": "Найди паспорта и ТУ для всех деталей участка UNIT-SYN-H2S-001 и покажи чего не хватает"
          }
        ]
      }
    ],
    "technical_filters": {
      "medium": "H2S",
      "h2s_confirmed": true
    },
    "stock_filters": {},
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
      "unit_id": "UNIT-SYN-H2S-001",
      "medium": "H2S"
    },
    "component_context": {},
    "references": [
      "UNIT-SYN-H2S-001"
    ],
    "ambiguities": [],
    "required_agents": [
      "knowledge",
      "rules",
      "search",
      "topology"
    ],
    "required_capabilities": [
      "compatibility_check",
      "document_search",
      "search",
      "topology"
    ],
    "confidence": 0.5900000000000001,
    "confidence_details": {
      "operations": 0.8,
      "card": 0.6,
      "ambiguities": 1.0
    },
    "intents": [
      "CHECK_STOCK",
      "FIND_DOCUMENTS",
      "FIND_STANDARDS"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "CHECK_STOCK": [],
      "FIND_DOCUMENTS": [],
      "FIND_STANDARDS": []
    },
    "params": {
      "unit_id": "UNIT-SYN-H2S-001"
    },
    "primary_intent": "CHECK_STOCK",
    "groups": [
      {
        "group": "ДОКУМЕНТЫ",
        "score": 4,
        "confidence": 0.667,
        "matched": [
          "паспорт",
          "context:найди+паспорт"
        ]
      },
      {
        "group": "ПОИСК",
        "score": 2,
        "confidence": 0.333,
        "matched": [
          "найди",
          "покажи"
        ]
      },
      {
        "group": "СКЛАД",
        "score": 0,
        "confidence": 0.0,
        "matched": []
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

>>> Время выполнения: 19049 мс
