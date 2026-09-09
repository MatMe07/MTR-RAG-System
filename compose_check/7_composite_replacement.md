Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 16:22:28,441 INFO    | mtr.agent.executor               | [Executor] Execute query='У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ' mode=auto request_id=None
2026-09-09 16:22:28,441 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 16:22:28,678 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.79 operations=['repair', 'replace', 'plan', 'assemble'] item_types=['отвод'] technical_filters={'item_type': 'отвод'} ambiguities=[] (237ms)
2026-09-09 16:22:28,690 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['FIND_BY_COMPONENT', 'PLAN_REPAIR'] missing={'FIND_BY_COMPONENT': [], 'PLAN_REPAIR': []}
2026-09-09 16:22:28,698 INFO    | mtr.agent.executor               | [Executor] Intent resolved: maintenance
2026-09-09 16:22:28,699 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 16:22:28,826 INFO    | mtr.agent.tools                  | [graph_search] Found 1 components, 1 targets in 3ms
2026-09-09 16:22:28,828 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 16:22:28,831 INFO    | mtr.agent.tools                  | [catalog_search] Found 40 candidates (from 1000 cards) in 3ms
2026-09-09 16:22:28,947 INFO    | mtr.agent.tools                  | [stock_query] Checked 40 items (kept 40) in 115ms
2026-09-09 16:22:28,948 INFO    | mtr.agent.tools                  | [rules_engine] Scored 40 candidates in 1ms
2026-09-09 16:22:28,953 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['марка стали', 'DN', 'угол']
Запрос: У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ
Найденные детали:
- Расходные материалы: комплект
- ОКШ 90-426x10 20: совпадает по параметрам
- ОКШ 45-108x4 09ГСФ: совпадает по параметрам
- ОКШ 90-377x12 13ХФА: совпадает по параметрам
- ОКШ 90-133x6 09ГСФ: совпадает по параметрам
Результаты проверок: —
Предупреждения: ['Черновик: периодичность и состав работ утверждает служба ТОиР', 'Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.', 'Без истории отказов и утвержденного регламента план остается предварительным.', 'Без фактической статистики отказов риск оценивается только по доступным признакам.', 'Система не заменяет наряд и производственную процедуру безопасного проведения работ.', 'Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S.', 'Без трассы и проектной схемы нельзя определить точное количество деталей.', 'Место и параметры арматуры нельзя окончательно определить без проектной схемы.', 'Для типа «отвод» не указаны обязательные параметры: DN, угол, марка стали. Уточните их для точного подбора.']
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
2026-09-09 16:22:30,562 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-09 16:23:01,253 INFO    | mtr.agent.executor               | [Executor] Graph finished in 32554ms: components=41 sources=131 warnings=2 tools_used=['graph_search', 'maintenance_planner', 'catalog_search', 'stock_query', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 16:23:01,253 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 16:23:01,289 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 16:23:01,289 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ",
  "intent": "maintenance",
  "intent_label": "План ТОиР",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "maintenance_planner",
    "catalog_search",
    "stock_query",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "Уточните обязательные параметры отвода — диаметр (DN), угол поворота и марку стали, так как без них подбор детали невозможен. После уточнения выберите подходящий ОКШ из списка, соответствующий этим параметрам, и проверьте его паспорт/ТУ на соответствие среде H₂S/CO₂ и наличие защитного покрытия. Основные риски — установка несоответствующего элемента может привести к утечкам, ускоренной коррозии и нарушению безопасности в агрессивной среде. План работ должен быть согласован со службой ТОиР и ответственным за ремонт экспертом, а также подтверждён нарядом и проектной схемой трассы.",
  "components": [
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
      "mtr_code": "MTR-SYN-REG-000221",
      "ksm_code": "KSM-SYN-REG-000221",
      "name": "ОКШ 90-426x10 20",
      "item_type": "отвод",
      "quantity": 46.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 46.0; оценка правил",
      "source_id": "MTR-SYN-REG-000221",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000222",
      "ksm_code": "KSM-SYN-REG-000222",
      "name": "ОКШ 45-108x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 1.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 1.0; оценка правил",
      "source_id": "MTR-SYN-REG-000222",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000224",
      "ksm_code": "KSM-SYN-REG-000224",
      "name": "ОКШ 90-377x12 13ХФА",
      "item_type": "отвод",
      "quantity": 2.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 2.0; оценка правил",
      "source_id": "MTR-SYN-REG-000224",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000225",
      "ksm_code": "KSM-SYN-REG-000225",
      "name": "ОКШ 90-133x6 09ГСФ",
      "item_type": "отвод",
      "quantity": 75.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 75.0; оценка правил",
      "source_id": "MTR-SYN-REG-000225",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000226",
      "ksm_code": "KSM-SYN-REG-000226",
      "name": "ОКШ 90-57x3 13ХФА",
      "item_type": "отвод",
      "quantity": 41.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 41.0; оценка правил",
      "source_id": "MTR-SYN-REG-000226",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000227",
      "ksm_code": "KSM-SYN-REG-000227",
      "name": "ОКШ 45-57x3 09ГСФ",
      "item_type": "отвод",
      "quantity": 5.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 5.0; оценка правил",
      "source_id": "MTR-SYN-REG-000227",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000228",
      "ksm_code": "KSM-SYN-REG-000228",
      "name": "ОКШ 90-325x10 09ГСФ",
      "item_type": "отвод",
      "quantity": 76.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 76.0; оценка правил",
      "source_id": "MTR-SYN-REG-000228",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000229",
      "ksm_code": "KSM-SYN-REG-000229",
      "name": "ОКШ 45-273x10 13ХФА",
      "item_type": "отвод",
      "quantity": 73.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 73.0; оценка правил",
      "source_id": "MTR-SYN-REG-000229",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000230",
      "ksm_code": "KSM-SYN-REG-000230",
      "name": "ОКШ 90-57x3 20",
      "item_type": "отвод",
      "quantity": 67.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 67.0; оценка правил",
      "source_id": "MTR-SYN-REG-000230",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000223",
      "ksm_code": "KSM-SYN-REG-000223",
      "name": "ОКШ 90-76x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 47.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка; совпадает по параметрам; на складе: 47.0; оценка правил",
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
      "mtr_code": "MTR-SYN-REG-000223",
      "ksm_code": "KSM-SYN-REG-000223",
      "name": "ОКШ 90-76x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 47.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "работа: обслуживание/проверка; совпадает по параметрам; на складе: 47.0; оценка правил",
      "source_id": "COMP-SYN-008",
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
    "Черновик: периодичность и состав работ утверждает служба ТОиР",
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Без истории отказов и утвержденного регламента план остается предварительным.",
    "Без фактической статистики отказов риск оценивается только по доступным признакам.",
    "Система не заменяет наряд и производственную процедуру безопасного проведения работ.",
    "Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S.",
    "Без трассы и проектной схемы нельзя определить точное количество деталей.",
    "Место и параметры арматуры нельзя окончательно определить без проектной схемы.",
    "Для типа «отвод» не указаны обязательные параметры: DN, угол, марка стали. Уточните их для точного подбора."
  ],
  "warning_categories": {
    "Планирование и закупка": [
      "Черновик: периодичность и состав работ утверждает служба ТОиР",
      "Без истории отказов и утвержденного регламента план остается предварительным."
    ],
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
      "Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S."
    ],
    "Экспертная проверка": [
      "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом."
    ],
    "Прочее": [
      "Без фактической статистики отказов риск оценивается только по доступным признакам.",
      "Система не заменяет наряд и производственную процедуру безопасного проведения работ.",
      "Без трассы и проектной схемы нельзя определить точное количество деталей.",
      "Место и параметры арматуры нельзя окончательно определить без проектной схемы.",
      "Для типа «отвод» не указаны обязательные параметры: DN, угол, марка стали. Уточните их для точного подбора."
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
      "id": "COMP-SYN-008",
      "fragment": "UNIT-SYN-H2S-001"
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
      "kind": "catalog",
      "id": "MTR-SYN-REG-000221",
      "fragment": "ОКШ 90-426x10 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000221",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000222",
      "fragment": "ОКШ 45-108x4 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000222",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000223",
      "fragment": "ОКШ 90-76x4 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000223",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000224",
      "fragment": "ОКШ 90-377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000224",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000225",
      "fragment": "ОКШ 90-133x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000225",
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
      "id": "MTR-SYN-REG-000227",
      "fragment": "ОКШ 45-57x3 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000227",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000228",
      "fragment": "ОКШ 90-325x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000228",
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
      "id": "MTR-SYN-REG-000230",
      "fragment": "ОКШ 90-57x3 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000230",
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
      "id": "MTR-SYN-REG-000233",
      "fragment": "ОКШ 45-133x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000233",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000234",
      "fragment": "ОКШ 45-377x12 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000234",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000235",
      "fragment": "ОКШ 45-159x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000235",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000236",
      "fragment": "ОКШ 90-325x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000236",
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
      "id": "MTR-SYN-REG-000238",
      "fragment": "ОКШ 45-133x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000238",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000239",
      "fragment": "ОКШ 90-219x8 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000239",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000240",
      "fragment": "ОКШ 90-159x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000240",
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
      "id": "MTR-SYN-REG-000243",
      "fragment": "ОКШ 45-159x6 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000243",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000244",
      "fragment": "ОКШ 45-57x3 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000244",
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
      "id": "MTR-SYN-REG-000246",
      "fragment": "ОКШ 45-159x6 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000246",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000247",
      "fragment": "ОКШ 45-108x4 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000247",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000248",
      "fragment": "ОКШ 90-108x4 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000248",
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
      "id": "MTR-SYN-REG-000250",
      "fragment": "ОКШ 45-377x12 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000250",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000251",
      "fragment": "ОКШ 90-219x8 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000251",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000252",
      "fragment": "ОКШ 45-89x4 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000252",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000253",
      "fragment": "ОКШ 45-273x10 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000253",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000254",
      "fragment": "ОКШ 90-76x4 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000254",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000255",
      "fragment": "ОКШ 90-325x10 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000255",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000256",
      "fragment": "ОКШ 90-76x4 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000256",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000257",
      "fragment": "ОКШ 90-219x8 20"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000257",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000258",
      "fragment": "ОКШ 90-89x4 09ГСФ"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000258",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000259",
      "fragment": "ОКШ 45-273x10 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000259",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000260",
      "fragment": "ОКШ 90-76x4 09Г2С"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000260",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000221",
      "fragment": "остаток: 46.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000222",
      "fragment": "остаток: 1.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000223",
      "fragment": "остаток: 47.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000224",
      "fragment": "остаток: 2.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000225",
      "fragment": "остаток: 75.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000226",
      "fragment": "остаток: 41.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000227",
      "fragment": "остаток: 5.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000228",
      "fragment": "остаток: 76.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000229",
      "fragment": "остаток: 73.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000230",
      "fragment": "остаток: 67.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000231",
      "fragment": "остаток: 65.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000232",
      "fragment": "остаток: 30.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000233",
      "fragment": "остаток: 41.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000234",
      "fragment": "остаток: 31.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000235",
      "fragment": "остаток: 6.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000236",
      "fragment": "остаток: 47.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000237",
      "fragment": "остаток: 16.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000238",
      "fragment": "остаток: 48.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000239",
      "fragment": "остаток: 37.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000240",
      "fragment": "остаток: 15.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000241",
      "fragment": "остаток: 5.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000242",
      "fragment": "остаток: 47.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000243",
      "fragment": "остаток: 28.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000244",
      "fragment": "остаток: 70.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000245",
      "fragment": "остаток: 75.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000246",
      "fragment": "остаток: 9.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000247",
      "fragment": "остаток: 31.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000248",
      "fragment": "остаток: 74.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000249",
      "fragment": "остаток: 58.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000250",
      "fragment": "остаток: 64.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000251",
      "fragment": "остаток: 4.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000252",
      "fragment": "остаток: 20.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000253",
      "fragment": "остаток: 35.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000254",
      "fragment": "остаток: 31.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000255",
      "fragment": "остаток: 8.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000256",
      "fragment": "остаток: 37.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000257",
      "fragment": "остаток: 8.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000258",
      "fragment": "остаток: 37.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000259",
      "fragment": "остаток: 24.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000260",
      "fragment": "остаток: 51.0"
    },
    {
      "kind": "matching_rules",
      "id": "matching_rules.csv",
      "fragment": null
    },
    {
      "kind": "passport",
      "id": "process_water",
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
  "status": "требует проверки",
  "recommendations": [
    "Уточните параметры запроса: тип изделия, DN, PN, среда.",
    "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.79,
  "parsed_query": {
    "original_query": "У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ",
    "operations": [
      "repair",
      "replace",
      "plan",
      "assemble"
    ],
    "item_types": [
      "отвод"
    ],
    "component_ids": [
      "COMP-SYN-008"
    ],
    "unit_ids": [],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": "отвод",
      "subtype": null,
      "designation": null,
      "name": "отвод",
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
          "dn",
          "geometry",
          "angle",
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
          "fragment": "У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ"
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
        "designation": null,
        "name": "отвод",
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
            "dn",
            "geometry",
            "angle",
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
            "fragment": "У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ"
          }
        ]
      }
    ],
    "technical_filters": {
      "item_type": "отвод"
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
    "impact_analysis": {},
    "unit_context": {},
    "component_context": {
      "component_id": "COMP-SYN-008"
    },
    "references": [
      "COMP-SYN-008"
    ],
    "ambiguities": [],
    "required_agents": [
      "knowledge",
      "plan",
      "search",
      "topology"
    ],
    "required_capabilities": [
      "assembly_planning",
      "maintenance_planning",
      "repair_planning",
      "replacement_matching",
      "topology"
    ],
    "confidence": 0.79,
    "confidence_details": {
      "operations": 1.0,
      "card": 0.5,
      "ambiguities": 1.0
    },
    "intents": [
      "FIND_BY_COMPONENT",
      "PLAN_REPAIR"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "FIND_BY_COMPONENT": [],
      "PLAN_REPAIR": []
    },
    "params": {
      "component_id": "COMP-SYN-008"
    },
    "primary_intent": "FIND_BY_COMPONENT",
    "groups": [
      {
        "group": "РЕМОНТ",
        "score": 1,
        "confidence": 1.0,
        "matched": [
          "сломался"
        ]
      },
      {
        "group": "ПОИСК",
        "score": 0,
        "confidence": 0.0,
        "matched": []
      },
      {
        "group": "СКЛАД",
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

>>> Время выполнения: 32848 мс
