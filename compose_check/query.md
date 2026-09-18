Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-17 20:35:25,069 INFO    | mtr.agent.executor               | [Executor] Execute query='Собери заявку на пополнение склада для участка с CO2, включи только позиции с остатком меньше трех штук' mode=auto request_id=cdd94750-9a14-4cdb-91ed-070b22d2e6db
2026-09-17 20:35:25,070 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-17 20:35:25,326 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.64 operations=['inventory', 'assemble'] item_types=[] technical_filters={'medium': 'CO2', 'co2_confirmed': True} ambiguities=[] (256ms)
2026-09-17 20:35:25,343 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=REQUIRES_EXPERT intents=['CHECK_STOCK'] missing={'CHECK_STOCK': ['ksm_code']}
2026-09-17 20:35:25,352 INFO    | mtr.agent.executor               | [Executor] Intent resolved: inventory
2026-09-17 20:35:25,352 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-17 20:35:25,500 INFO    | mtr.agent.tools                  | [graph_search] Found 12 components, 12 targets in 6ms
2026-09-17 20:35:25,501 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-17 20:35:25,524 INFO    | mtr.agent.tools                  | [catalog_search] Found 40 candidates (from 1000 cards) in 23ms
2026-09-17 20:35:25,564 INFO    | mtr.agent.tools                  | [stock_query] Checked 12 items (kept 0) in 39ms
2026-09-17 20:35:25,605 INFO    | mtr.agent.tools                  | [rules_engine] Scored 40 candidates in 1ms
2026-09-17 20:35:25,610 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
2026-09-17 20:35:25,616 INFO    | mtr.agent.executor               | [Executor] Graph finished in 264ms: components=51 sources=122 warnings=3 tools_used=['graph_search', 'catalog_search', 'stock_query', 'inventory_calculator', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-17 20:35:25,616 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-17 20:35:25,642 INFO    | mtr.agent.verify                 | [Verifier] verdict=review gaps=1 max_severity=high reasons=['[high] safety_unconfirmed: пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ']
2026-09-17 20:35:25,642 INFO    | mtr.agent.executor               | [Executor][auto] verdict=review reasons=['[high] safety_unconfirmed: пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ']
2026-09-17 20:35:27,626 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-17 20:35:43,902 INFO    | mtr.agent.verify                 | [Verifier] verdict=review gaps=1 max_severity=high reasons=['[high] safety_unconfirmed: пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ']
2026-09-17 20:35:43,902 INFO    | mtr.agent.llm.refine_loop        | [RefineLoop] iteration 1: verdict=REVIEW gaps=['safety_unconfirmed']
2026-09-17 20:35:44,244 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-17 20:37:07,613 INFO    | mtr.agent.verify                 | [Verifier] verdict=review gaps=1 max_severity=high reasons=['[high] safety_unconfirmed: пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ']
2026-09-17 20:37:07,613 INFO    | mtr.agent.llm.refine_loop        | [RefineLoop] iteration 2: verdict=REVIEW gaps=['safety_unconfirmed']
2026-09-17 20:37:07,613 INFO    | mtr.agent.llm.refine_loop        | [RefineLoop] time limit exceeded after 2 iterations
2026-09-17 20:37:07,613 INFO    | mtr.agent.executor               | [Executor][auto] C1+ loop finished: passed=False iterations=2 final_answer_len=572 verdict=review
2026-09-17 20:37:07,613 INFO    | mtr.agent.executor               | [Executor][auto]   it#1 action=finish tool=None error=None verdict=review (18251ms)
2026-09-17 20:37:07,613 INFO    | mtr.agent.executor               | [Executor][auto]   it#2 action=call_tool tool=search_catalog error="'list' object has no attribute 'get'" verdict=review (83074ms)
2026-09-17 20:37:07,613 INFO    | mtr.agent.executor               | [Executor][auto] escalation recorded: request_id=cdd94750-9a14-4cdb-91ed-070b22d2e6db mode_used=refine_loop_failed_offer_c2 verdict=review gaps=['safety_unconfirmed'] tokens=3826
2026-09-17 20:37:07,619 INFO    | mtr.agent.executor               | [Executor][auto] mode_refined=auto offer_full_llm=True iterations=2

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Собери заявку на пополнение склада для участка с CO2, включи только позиции с остатком меньше трех штук",
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
  "explanation": "Для подтверждения пригодности компонентов к среде CO2 необходимы их идентификаторы (KSM/МТР-коды) либо данные паспорта/ТУ, содержащие информацию о материале, наличии покрытия и сертификатах соответствия. В текущем структурированном ответе такие идентификаторы отсутствуют, поэтому невозможно выполнить проверку совместимости с CO2 для перечисленных позиций. Требуется предоставить KSM-коды компонентов или ссылки на их паспорта/ТУ, после чего можно будет использовать инструмент check_compatibility_batch и получить однозначный вывод о безопасности применения в среде CO2.",
  "components": [
    {
      "mtr_code": null,
      "ksm_code": null,
      "name": "Заявка на пополнение",
      "item_type": null,
      "quantity": 0.0,
      "status": "нет позиций ниже порога",
      "detail": "проверены остатки по 12 установленным позициям; все соответствуют порогу — заявка не требуется",
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
      "mtr_code": "MTR-SYN-REG-000014",
      "ksm_code": "KSM-SYN-REG-000014",
      "name": "Труба бесшовная горячедеформированная 273x10 13ХФА",
      "item_type": "труба",
      "quantity": 26.0,
      "status": "совпадает по параметрам",
      "detail": "остаток: 26.0; оценка правил",
      "source_id": "COMP-SYN-013",
      "unit_id": "UNIT-SYN-CO2-001",
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
      "mtr_code": "MTR-SYN-REG-000231",
      "ksm_code": "KSM-SYN-REG-000231",
      "name": "ОКШ 90-426x10 13ХФА",
      "item_type": "отвод",
      "quantity": 65.0,
      "status": "совпадает по параметрам",
      "detail": "остаток: 65.0; оценка правил",
      "source_id": "COMP-SYN-014",
      "unit_id": "UNIT-SYN-CO2-001",
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
      "mtr_code": "MTR-SYN-REG-000447",
      "ksm_code": "KSM-SYN-REG-000447",
      "name": "Переход концентрический 76x4-57x3 20",
      "item_type": "переход",
      "quantity": 74.0,
      "status": "установлен на UNIT-SYN-CO2-001",
      "detail": "остаток: 74.0",
      "source_id": "COMP-SYN-015",
      "unit_id": "UNIT-SYN-CO2-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000598",
      "ksm_code": "KSM-SYN-REG-000598",
      "name": "Задвижка шиберная DN100 PN40",
      "item_type": "задвижка",
      "quantity": 22.0,
      "status": "установлен на UNIT-SYN-CO2-001",
      "detail": "остаток: 22.0",
      "source_id": "COMP-SYN-016",
      "unit_id": "UNIT-SYN-CO2-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000752",
      "ksm_code": "KSM-SYN-REG-000752",
      "name": "Заглушка эллиптическая приварная 133x5 09ГСФ",
      "item_type": "заглушка",
      "quantity": 69.0,
      "status": "установлен на UNIT-SYN-CO2-001",
      "detail": "остаток: 69.0",
      "source_id": "COMP-SYN-017",
      "unit_id": "UNIT-SYN-CO2-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000874",
      "ksm_code": "KSM-SYN-REG-000874",
      "name": "Тройник равнопроходной 57x3-57x3 09Г2С",
      "item_type": "тройник",
      "quantity": 42.0,
      "status": "установлен на UNIT-SYN-CO2-001",
      "detail": "остаток: 42.0",
      "source_id": "COMP-SYN-018",
      "unit_id": "UNIT-SYN-CO2-001",
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
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "остаток: 19.0",
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
      "quantity": 75.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "остаток: 75.0",
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
      "quantity": 66.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "остаток: 66.0",
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
      "quantity": 50.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "остаток: 50.0",
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
      "quantity": 4.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "остаток: 4.0",
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
      "quantity": 69.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "остаток: 69.0",
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
    "По порогу остатка отфильтровано позиций: 12",
    "Расчёт — черновик: нормы запаса требуют утверждения",
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "Пригодность к CO2 нельзя подтверждать только по совпадению размеров.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.",
    "Рекомендуемое количество является расчетным до получения норм страхового запаса.",
    "Расчет нужно пересчитать после получения утвержденных норм страхового запаса.",
    "Заявка остается черновиком до утверждения норм запаса и технической пригодности.",
    "Без трассы и проектной схемы нельзя определить точное количество деталей.",
    "Место и параметры арматуры нельзя окончательно определить без проектной схемы."
  ],
  "warning_categories": {
    "Прочее": [
      "По порогу остатка отфильтровано позиций: 12",
      "Без трассы и проектной схемы нельзя определить точное количество деталей.",
      "Место и параметры арматуры нельзя окончательно определить без проектной схемы."
    ],
    "Планирование и закупка": [
      "Расчёт — черновик: нормы запаса требуют утверждения",
      "Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.",
      "Рекомендуемое количество является расчетным до получения норм страхового запаса.",
      "Расчет нужно пересчитать после получения утвержденных норм страхового запаса."
    ],
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
      "Пригодность к CO2 нельзя подтверждать только по совпадению размеров.",
      "Заявка остается черновиком до утверждения норм запаса и технической пригодности."
    ],
    "Экспертная проверка": [
      "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом."
    ]
  },
  "purchase_recommendation": "Заявка не требуется: остатки установленных позиций выше порога",
  "excluded_due_to_medium": [],
  "sources": [
    {
      "kind": "object_graph",
      "id": "gas_pipeline_object.json",
      "fragment": "демо-объект",
      "lnd_section": null
    },
    {
      "kind": "project_documentation",
      "id": "gas_pipeline_object.json",
      "fragment": "проектная схема объекта",
      "lnd_section": null
    },
    {
      "kind": "maintenance_policy",
      "id": "MTR-TOIR-POLICY-001",
      "fragment": "регламент ТОиР (черновой)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-013",
      "fragment": "UNIT-SYN-CO2-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-013",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-014",
      "fragment": "UNIT-SYN-CO2-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-014",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-015",
      "fragment": "UNIT-SYN-CO2-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-015",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-016",
      "fragment": "UNIT-SYN-CO2-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-016",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-017",
      "fragment": "UNIT-SYN-CO2-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-017",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-018",
      "fragment": "UNIT-SYN-CO2-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-018",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-019",
      "fragment": "UNIT-SYN-MIX-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-019",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-020",
      "fragment": "UNIT-SYN-MIX-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-020",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-021",
      "fragment": "UNIT-SYN-MIX-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-021",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-022",
      "fragment": "UNIT-SYN-MIX-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-022",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-023",
      "fragment": "UNIT-SYN-MIX-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-023",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-024",
      "fragment": "UNIT-SYN-MIX-001",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-024",
      "fragment": "паспорт изделия (статус в графе требует паспорт)",
      "lnd_section": null
    },
    {
      "kind": "maintenance_history",
      "id": "UNIT-SYN-CO2-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)",
      "lnd_section": null
    },
    {
      "kind": "maintenance_history",
      "id": "UNIT-SYN-MIX-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000014",
      "fragment": "Труба бесшовная горячедеформированная 273x10 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000014",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000015",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000015",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000024",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000024",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000029",
      "fragment": "Труба бесшовная горячедеформированная 273x10 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000029",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000036",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000036",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000037",
      "fragment": "Труба бесшовная горячедеформированная 377x12 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000037",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000039",
      "fragment": "Труба бесшовная горячедеформированная 133x6 20",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000039",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000059",
      "fragment": "Труба бесшовная горячедеформированная 133x6 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000059",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000060",
      "fragment": "Труба бесшовная горячедеформированная 108x6 20",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000060",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000068",
      "fragment": "Труба бесшовная горячедеформированная 76x5 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000068",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000072",
      "fragment": "Труба бесшовная горячедеформированная 219x10 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000072",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000087",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000087",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000096",
      "fragment": "Труба бесшовная горячедеформированная 133x6 20",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000096",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000124",
      "fragment": "Труба электросварная прямошовная 530x10 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000124",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000125",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000125",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000128",
      "fragment": "Труба электросварная спиральношовная 720x12 20",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000128",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000131",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000131",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000137",
      "fragment": "Труба электросварная спиральношовная 820x14 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000137",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000138",
      "fragment": "Труба электросварная спиральношовная 630x12 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000138",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000145",
      "fragment": "Труба электросварная спиральношовная 530x10 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000145",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000149",
      "fragment": "Труба электросварная спиральношовная 530x10 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000149",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000153",
      "fragment": "Труба электросварная спиральношовная 219x8 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000153",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000154",
      "fragment": "Труба электросварная прямошовная 630x12 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000154",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000157",
      "fragment": "Труба электросварная спиральношовная 426x10 20",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000157",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000170",
      "fragment": "Труба электросварная прямошовная 530x10 20",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000170",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000196",
      "fragment": "Труба электросварная спиральношовная 630x12 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000196",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000209",
      "fragment": "Труба электросварная спиральношовная 1020x16 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000209",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000231",
      "fragment": "ОКШ 90-426x10 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000231",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000235",
      "fragment": "ОКШ 45-159x6 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000235",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000239",
      "fragment": "ОКШ 90-219x8 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000239",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000251",
      "fragment": "ОКШ 90-219x8 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000251",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000261",
      "fragment": "ОКШ 45-57x3 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000261",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000281",
      "fragment": "ОКШ 90-108x4 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000281",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000289",
      "fragment": "ОКШ 45-108x4 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000289",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000292",
      "fragment": "ОКШ 45-133x6 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000292",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000294",
      "fragment": "ОКШ 90-108x4 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000294",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000309",
      "fragment": "ОКШ 45-133x6 09Г2С",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000309",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000318",
      "fragment": "ОКШ 90-57x3 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000318",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000344",
      "fragment": "ОКШ 90-325x10 09ГСФ",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000344",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000346",
      "fragment": "ОКШ 90-89x4 13ХФА",
      "lnd_section": null
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000346",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
      "lnd_section": null
    },
    {
      "kind": "matching_rules",
      "id": "matching_rules.csv",
      "fragment": null,
      "lnd_section": null
    },
    {
      "kind": "TU",
      "id": "gas_co2",
      "fragment": "технические условия на изделие",
      "lnd_section": null
    },
    {
      "kind": "internal_lnd",
      "id": "gas_co2",
      "fragment": "внутренний ЛНД по применимости к среде",
      "lnd_section": null
    },
    {
      "kind": "expert_decisions",
      "id": "gas_co2",
      "fragment": "заключение эксперта по среде",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "gas_co2",
      "fragment": "паспорт изделия (требование профиля среды)",
      "lnd_section": null
    },
    {
      "kind": "TU",
      "id": "gas_h2s_co2",
      "fragment": "технические условия на изделие",
      "lnd_section": null
    },
    {
      "kind": "internal_lnd",
      "id": "gas_h2s_co2",
      "fragment": "внутренний ЛНД по применимости к среде",
      "lnd_section": null
    },
    {
      "kind": "expert_decisions",
      "id": "gas_h2s_co2",
      "fragment": "заключение эксперта по среде",
      "lnd_section": null
    },
    {
      "kind": "passport",
      "id": "gas_h2s_co2",
      "fragment": "паспорт изделия (требование профиля среды)",
      "lnd_section": null
    },
    {
      "kind": "standard",
      "id": "RST-GOST-8731-2025",
      "fragment": "Трубы стальные бесшовные горячедеформированные. Технические условия",
      "lnd_section": null
    },
    {
      "kind": "standard",
      "id": "RST-GOST-20295-85",
      "fragment": "Трубы стальные сварные для магистральных газонефтепроводов. Технические условия",
      "lnd_section": null
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17375-2001",
      "fragment": "Детали трубопроводов. Отводы крутоизогнутые типа 3D. Конструкция",
      "lnd_section": null
    },
    {
      "kind": "regulation",
      "id": "regulation_matrix.json",
      "fragment": null,
      "lnd_section": null
    }
  ],
  "missing_parameters": [],
  "human_review_required": true,
  "human_review_reasons": [
    "expert_data",
    "quality_gate"
  ],
  "status": "соответствует",
  "recommendations": [
    "Проверьте предупреждения перед принятием решения."
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.64,
  "parsed_query": {
    "original_query": "Собери заявку на пополнение склада для участка с CO2, включи только позиции с остатком меньше трех штук",
    "operations": [
      "inventory",
      "assemble"
    ],
    "item_types": [],
    "component_ids": [],
    "unit_ids": [],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": null,
      "subtype": null,
      "designation": "CO2",
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
        "medium": "CO2",
        "h2s_confirmed": null,
        "co2_confirmed": true,
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
          "lnd_section": null,
          "fragment": "Собери заявку на пополнение склада для участка с CO2, включи только позиции с остатком меньше трех штук"
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
        "designation": "CO2",
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
          "medium": "CO2",
          "h2s_confirmed": null,
          "co2_confirmed": true,
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
            "lnd_section": null,
            "fragment": "Собери заявку на пополнение склада для участка с CO2, включи только позиции с остатком меньше трех штук"
          }
        ]
      }
    ],
    "technical_filters": {
      "medium": "CO2",
      "co2_confirmed": true
    },
    "stock_filters": {
      "quantity_max": 3,
      "quantity_max_strict": true,
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
      "medium": "CO2"
    },
    "component_context": {},
    "references": [],
    "ambiguities": [],
    "required_agents": [
      "inventory",
      "plan"
    ],
    "required_capabilities": [
      "assembly_planning",
      "inventory"
    ],
    "confidence": 0.64,
    "confidence_details": {
      "operations": 0.6000000000000001,
      "card": 0.6,
      "ambiguities": 1.0
    },
    "intents": [
      "CHECK_STOCK"
    ],
    "status": "REQUIRES_EXPERT",
    "missing_params": {
      "CHECK_STOCK": [
        "ksm_code"
      ]
    },
    "params": {},
    "primary_intent": "CHECK_STOCK",
    "groups": [
      {
        "group": "СКЛАД",
        "score": 2,
        "confidence": 1.0,
        "matched": [
          "склад",
          "штук"
        ]
      },
      {
        "group": "ПОИСК",
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
      },
      {
        "group": "ДОКУМЕНТЫ",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      }
    ],
    "parser_diagnostics": {
      "parse_ms": 94.45905685424805,
      "strategy": "merge",
      "rule_confidence": 0.64,
      "natasha_used": true,
      "stages_ms": {
        "rule": 76.26032829284668,
        "natasha": 18.053531646728516,
        "merge": 0.13971328735351562
      },
      "llm_extractor": {
        "enabled": true,
        "calls": 0,
        "hits": 0,
        "errors": 0,
        "tokens": 0
      }
    }
  },
  "review_verdict": "pass",
  "review_issues": [],
  "verification_verdict": "review",
  "verification_reasons": [
    "[high] safety_unconfirmed: пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ"
  ],
  "mode_refined": "auto",
  "llm_refine_failed": true,
  "llm_tokens_used": 3826,
  "offer_full_llm": true,
  "offer_question": "Полный LLM-анализ может закрыть оставшиеся недостатки ответа. Продолжить? Это займёт больше времени и требует доступа к OpenRouter.",
  "offer_endpoint": "/api/v1/agent/continue",
  "llm": {
    "available": true,
    "used": true,
    "reason": "LLM использовался: 2 вызовов, 5336+2072 токенов (всего 7408), cache 0/2",
    "model": "nvidia/nemotron-3-super-120b-a12b:free",
    "total_calls": 2,
    "cache_hits": 0,
    "cache_misses": 2,
    "prompt_tokens": 5336,
    "completion_tokens": 2072,
    "total_tokens": 7408,
    "duration_ms": 101322.29999999999,
    "cost_estimate_usd": 0.0,
    "refine_iterations": [
      {
        "n": 1,
        "action": "finish",
        "tool_name": null,
        "tool_input": null,
        "error": null,
        "verdict": "review",
        "gaps": [
          {
            "type": "safety_unconfirmed",
            "detail": "пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ",
            "severity": "high"
          }
        ],
        "duration_ms": 18251
      },
      {
        "n": 2,
        "action": "call_tool",
        "tool_name": "search_catalog",
        "tool_input": {
          "params": {
            "item_type": "труба",
            "dn": 273,
            "wall_thickness": 10,
            "steel_grade": "13ХФА"
          },
          "detail_level": "basic"
        },
        "error": "'list' object has no attribute 'get'",
        "verdict": "review",
        "gaps": [
          {
            "type": "safety_unconfirmed",
            "detail": "пригодность к CO2 не подтверждена для 13 позиций ответа; требуется сертификат/ТУ",
            "severity": "high"
          }
        ],
        "duration_ms": 83074
      }
    ],
    "calls": [
      {
        "stage": "refine",
        "mode": "auto",
        "prompt_tokens": 2636,
        "completion_tokens": 946,
        "total_tokens": 3582,
        "duration_ms": 18251.6,
        "cache_hit": false,
        "error": null,
        "ts": "2026-09-17T20:35:43.902259+00:00"
      },
      {
        "stage": "refine",
        "mode": "auto",
        "prompt_tokens": 2700,
        "completion_tokens": 1126,
        "total_tokens": 3826,
        "duration_ms": 83070.7,
        "cache_hit": false,
        "error": null,
        "ts": "2026-09-17T20:37:06.973518+00:00"
      }
    ]
  }
}
========================================================================

>>> Время выполнения: 102550 мс
