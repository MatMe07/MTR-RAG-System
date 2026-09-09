Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 16:21:28,143 INFO    | mtr.agent.executor               | [Executor] Execute query='В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры' mode=auto request_id=None
2026-09-09 16:21:28,143 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 16:21:28,387 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.89 operations=['replace', 'assemble'] item_types=['тройник', 'труба', 'отвод', 'заглушка', 'переход', 'задвижка'] technical_filters={} ambiguities=[] (245ms)
2026-09-09 16:21:28,400 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['ADD_COMPONENT'] missing={'ADD_COMPONENT': []}
2026-09-09 16:21:28,407 INFO    | mtr.agent.executor               | [Executor] Intent resolved: object_configuration
2026-09-09 16:21:28,407 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 16:21:28,532 INFO    | mtr.agent.tools                  | [graph_search] Found 6 components, 6 targets in 5ms
2026-09-09 16:21:28,536 INFO    | mtr.agent.tools                  | [catalog_search] ADD_COMPONENT target types: ['задвижка']
2026-09-09 16:21:28,536 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 16:21:28,539 INFO    | mtr.agent.tools                  | [catalog_search] Found 40 candidates (from 1000 cards) in 5ms
2026-09-09 16:21:28,603 INFO    | mtr.agent.tools                  | [stock_query] Checked 40 items (kept 40) in 64ms
2026-09-09 16:21:28,605 INFO    | mtr.agent.tools                  | [rules_engine] Scored 40 candidates in 1ms
2026-09-09 16:21:28,609 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['DN', 'PN', 'марка стали']
Запрос: В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры
Найденные детали:
- Труба бесшовная горячедеформированная 159x8 09ГСФ: установлен на UNIT-SYN-WATER-001
- ОКШ 45-377x12 09Г2С: установлен на UNIT-SYN-WATER-001
- Переход концентрический 133x5-89x4 20: установлен на UNIT-SYN-WATER-001
- Задвижка клиновая DN150 PN40: установлен на UNIT-SYN-WATER-001
- Заглушка эллиптическая приварная 57x3 09ГСФ: установлен на UNIT-SYN-WATER-001
Результаты проверок: —
Предупреждения: ['Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.', 'Закрытая задвижка не должна автоматически считаться заменой физической заглушки.', 'Без трассы и проектной схемы нельзя определить точное количество деталей.', 'Место и параметры арматуры нельзя окончательно определить без проектной схемы.', 'Для типа «задвижка» не указаны обязательные параметры: DN, PN, марка стали. Уточните их для точного подбора.']
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
2026-09-09 16:21:29,921 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-09 16:21:39,597 INFO    | mtr.agent.executor               | [Executor] Graph finished in 11189ms: components=45 sources=138 warnings=1 tools_used=['graph_search', 'catalog_search', 'stock_query', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 16:21:39,597 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 16:21:39,629 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 16:21:39,629 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры",
  "intent": "object_configuration",
  "intent_label": "Сборка участка",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "catalog_search",
    "stock_query",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "Рекомендую установить клиновую задвижку с условным проходом DN 150 и номинальным давлением PN 40, уточнив марку стали (например, 09ГСФ или 09Г2С) так, чтобы она соответствовала материалу трубопровода. Перед монтажом необходимо проверить паспорт, технические условия и проектную документацию, подтверждающие устойчивость стали к среде H₂S/CO₂ и наличие требуемого защитного покрытия. Основной риск заключается в том, что без подтверждённой марки стали задвижка может подвергаться коррозии или механическому отказу, а её закрытое положение не заменяет физическую заглушку для полной изоляции участка. Критический параметр «марка стали» для данной арматуры пока не указан и должен быть уточнён перед окончательным выбором.",
  "components": [
    {
      "mtr_code": "MTR-SYN-REG-000025",
      "ksm_code": "KSM-SYN-REG-000025",
      "name": "Труба бесшовная горячедеформированная 159x8 09ГСФ",
      "item_type": "труба",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-031",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000234",
      "ksm_code": "KSM-SYN-REG-000234",
      "name": "ОКШ 45-377x12 09Г2С",
      "item_type": "отвод",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-032",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000443",
      "ksm_code": "KSM-SYN-REG-000443",
      "name": "Переход концентрический 133x5-89x4 20",
      "item_type": "переход",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-033",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000595",
      "ksm_code": "KSM-SYN-REG-000595",
      "name": "Задвижка клиновая DN150 PN40",
      "item_type": "задвижка",
      "quantity": 11.0,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": "совпадает по параметрам; на складе: 11.0; оценка правил",
      "source_id": "COMP-SYN-034",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000744",
      "ksm_code": "KSM-SYN-REG-000744",
      "name": "Заглушка эллиптическая приварная 57x3 09ГСФ",
      "item_type": "заглушка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-035",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000871",
      "ksm_code": "KSM-SYN-REG-000871",
      "name": "Тройник равнопроходной 57x3-57x3 09Г2С",
      "item_type": "тройник",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-036",
      "unit_id": "UNIT-SYN-WATER-001",
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
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-031",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000234",
      "ksm_code": "KSM-SYN-REG-000234",
      "name": "ОКШ 45-377x12 09Г2С",
      "item_type": "отвод",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-032",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000443",
      "ksm_code": "KSM-SYN-REG-000443",
      "name": "Переход концентрический 133x5-89x4 20",
      "item_type": "переход",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-033",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000595",
      "ksm_code": "KSM-SYN-REG-000595",
      "name": "Задвижка клиновая DN150 PN40",
      "item_type": "задвижка",
      "quantity": 11.0,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": "совпадает по параметрам; на складе: 11.0; оценка правил",
      "source_id": "COMP-SYN-034",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000744",
      "ksm_code": "KSM-SYN-REG-000744",
      "name": "Заглушка эллиптическая приварная 57x3 09ГСФ",
      "item_type": "заглушка",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-035",
      "unit_id": "UNIT-SYN-WATER-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000871",
      "ksm_code": "KSM-SYN-REG-000871",
      "name": "Тройник равнопроходной 57x3-57x3 09Г2С",
      "item_type": "тройник",
      "quantity": null,
      "status": "установлен на UNIT-SYN-WATER-001",
      "detail": null,
      "source_id": "COMP-SYN-036",
      "unit_id": "UNIT-SYN-WATER-001",
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
      "quantity": 4.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 4.0; оценка правил",
      "source_id": "MTR-SYN-REG-000591",
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
      "mtr_code": "MTR-SYN-REG-000592",
      "ksm_code": "KSM-SYN-REG-000592",
      "name": "Задвижка клиновая DN300 PN160",
      "item_type": "задвижка",
      "quantity": 25.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 25.0; оценка правил",
      "source_id": "MTR-SYN-REG-000592",
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
      "mtr_code": "MTR-SYN-REG-000593",
      "ksm_code": "KSM-SYN-REG-000593",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": 38.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 38.0; оценка правил",
      "source_id": "MTR-SYN-REG-000593",
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
      "mtr_code": "MTR-SYN-REG-000594",
      "ksm_code": "KSM-SYN-REG-000594",
      "name": "Задвижка шиберная DN250 PN100",
      "item_type": "задвижка",
      "quantity": 50.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 50.0; оценка правил",
      "source_id": "MTR-SYN-REG-000594",
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
      "mtr_code": "MTR-SYN-REG-000596",
      "ksm_code": "KSM-SYN-REG-000596",
      "name": "Задвижка клиновая DN80 PN25",
      "item_type": "задвижка",
      "quantity": 14.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 14.0; оценка правил",
      "source_id": "MTR-SYN-REG-000596",
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
      "mtr_code": "MTR-SYN-REG-000597",
      "ksm_code": "KSM-SYN-REG-000597",
      "name": "Задвижка шиберная DN80 PN25",
      "item_type": "задвижка",
      "quantity": 61.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 61.0; оценка правил",
      "source_id": "MTR-SYN-REG-000597",
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
      "mtr_code": "MTR-SYN-REG-000598",
      "ksm_code": "KSM-SYN-REG-000598",
      "name": "Задвижка шиберная DN100 PN40",
      "item_type": "задвижка",
      "quantity": 22.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 22.0; оценка правил",
      "source_id": "MTR-SYN-REG-000598",
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
      "mtr_code": "MTR-SYN-REG-000599",
      "ksm_code": "KSM-SYN-REG-000599",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": 72.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 72.0; оценка правил",
      "source_id": "MTR-SYN-REG-000599",
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
      "mtr_code": "MTR-SYN-REG-000600",
      "ksm_code": "KSM-SYN-REG-000600",
      "name": "Задвижка клиновая DN25 PN16",
      "item_type": "задвижка",
      "quantity": 15.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 15.0; оценка правил",
      "source_id": "MTR-SYN-REG-000600",
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
      "mtr_code": "MTR-SYN-REG-000601",
      "ksm_code": "KSM-SYN-REG-000601",
      "name": "Задвижка клиновая DN250 PN100",
      "item_type": "задвижка",
      "quantity": 25.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 25.0; оценка правил",
      "source_id": "MTR-SYN-REG-000601",
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
      "mtr_code": "MTR-SYN-REG-000602",
      "ksm_code": "KSM-SYN-REG-000602",
      "name": "Задвижка шиберная DN25 PN16",
      "item_type": "задвижка",
      "quantity": 72.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 72.0; оценка правил",
      "source_id": "MTR-SYN-REG-000602",
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
      "mtr_code": "MTR-SYN-REG-000603",
      "ksm_code": "KSM-SYN-REG-000603",
      "name": "Задвижка клиновая DN150 PN40",
      "item_type": "задвижка",
      "quantity": 20.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 20.0; оценка правил",
      "source_id": "MTR-SYN-REG-000603",
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
      "mtr_code": "MTR-SYN-REG-000604",
      "ksm_code": "KSM-SYN-REG-000604",
      "name": "Задвижка клиновая DN50 PN16",
      "item_type": "задвижка",
      "quantity": 23.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 23.0; оценка правил",
      "source_id": "MTR-SYN-REG-000604",
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
      "mtr_code": "MTR-SYN-REG-000605",
      "ksm_code": "KSM-SYN-REG-000605",
      "name": "Задвижка клиновая DN300 PN160",
      "item_type": "задвижка",
      "quantity": 37.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 37.0; оценка правил",
      "source_id": "MTR-SYN-REG-000605",
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
      "mtr_code": "MTR-SYN-REG-000606",
      "ksm_code": "KSM-SYN-REG-000606",
      "name": "Задвижка шиберная DN100 PN40",
      "item_type": "задвижка",
      "quantity": 10.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 10.0; оценка правил",
      "source_id": "MTR-SYN-REG-000606",
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
      "mtr_code": "MTR-SYN-REG-000607",
      "ksm_code": "KSM-SYN-REG-000607",
      "name": "Задвижка клиновая DN250 PN100",
      "item_type": "задвижка",
      "quantity": 42.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 42.0; оценка правил",
      "source_id": "MTR-SYN-REG-000607",
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
      "mtr_code": "MTR-SYN-REG-000608",
      "ksm_code": "KSM-SYN-REG-000608",
      "name": "Задвижка клиновая DN50 PN16",
      "item_type": "задвижка",
      "quantity": 29.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 29.0; оценка правил",
      "source_id": "MTR-SYN-REG-000608",
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
      "mtr_code": "MTR-SYN-REG-000609",
      "ksm_code": "KSM-SYN-REG-000609",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": 80.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 80.0; оценка правил",
      "source_id": "MTR-SYN-REG-000609",
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
      "mtr_code": "MTR-SYN-REG-000610",
      "ksm_code": "KSM-SYN-REG-000610",
      "name": "Задвижка клиновая DN80 PN25",
      "item_type": "задвижка",
      "quantity": 26.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 26.0; оценка правил",
      "source_id": "MTR-SYN-REG-000610",
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
      "mtr_code": "MTR-SYN-REG-000611",
      "ksm_code": "KSM-SYN-REG-000611",
      "name": "Задвижка клиновая DN300 PN160",
      "item_type": "задвижка",
      "quantity": 65.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 65.0; оценка правил",
      "source_id": "MTR-SYN-REG-000611",
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
      "mtr_code": "MTR-SYN-REG-000612",
      "ksm_code": "KSM-SYN-REG-000612",
      "name": "Задвижка клиновая DN400 PN160",
      "item_type": "задвижка",
      "quantity": 41.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 41.0; оценка правил",
      "source_id": "MTR-SYN-REG-000612",
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
      "mtr_code": "MTR-SYN-REG-000613",
      "ksm_code": "KSM-SYN-REG-000613",
      "name": "Задвижка клиновая DN50 PN16",
      "item_type": "задвижка",
      "quantity": 80.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 80.0; оценка правил",
      "source_id": "MTR-SYN-REG-000613",
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
      "mtr_code": "MTR-SYN-REG-000614",
      "ksm_code": "KSM-SYN-REG-000614",
      "name": "Задвижка клиновая DN400 PN160",
      "item_type": "задвижка",
      "quantity": 51.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 51.0; оценка правил",
      "source_id": "MTR-SYN-REG-000614",
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
      "mtr_code": "MTR-SYN-REG-000615",
      "ksm_code": "KSM-SYN-REG-000615",
      "name": "Задвижка клиновая DN150 PN40",
      "item_type": "задвижка",
      "quantity": 77.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 77.0; оценка правил",
      "source_id": "MTR-SYN-REG-000615",
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
      "mtr_code": "MTR-SYN-REG-000616",
      "ksm_code": "KSM-SYN-REG-000616",
      "name": "Задвижка клиновая DN80 PN25",
      "item_type": "задвижка",
      "quantity": 8.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 8.0; оценка правил",
      "source_id": "MTR-SYN-REG-000616",
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
      "mtr_code": "MTR-SYN-REG-000617",
      "ksm_code": "KSM-SYN-REG-000617",
      "name": "Задвижка клиновая DN300 PN160",
      "item_type": "задвижка",
      "quantity": 8.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 8.0; оценка правил",
      "source_id": "MTR-SYN-REG-000617",
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
      "mtr_code": "MTR-SYN-REG-000618",
      "ksm_code": "KSM-SYN-REG-000618",
      "name": "Задвижка клиновая DN25 PN16",
      "item_type": "задвижка",
      "quantity": 9.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 9.0; оценка правил",
      "source_id": "MTR-SYN-REG-000618",
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
      "mtr_code": "MTR-SYN-REG-000619",
      "ksm_code": "KSM-SYN-REG-000619",
      "name": "Задвижка клиновая DN300 PN160",
      "item_type": "задвижка",
      "quantity": 68.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 68.0; оценка правил",
      "source_id": "MTR-SYN-REG-000619",
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
      "mtr_code": "MTR-SYN-REG-000620",
      "ksm_code": "KSM-SYN-REG-000620",
      "name": "Задвижка шиберная DN400 PN160",
      "item_type": "задвижка",
      "quantity": 13.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 13.0; оценка правил",
      "source_id": "MTR-SYN-REG-000620",
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
      "mtr_code": "MTR-SYN-REG-000621",
      "ksm_code": "KSM-SYN-REG-000621",
      "name": "Задвижка клиновая DN50 PN16",
      "item_type": "задвижка",
      "quantity": 13.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 13.0; оценка правил",
      "source_id": "MTR-SYN-REG-000621",
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
      "mtr_code": "MTR-SYN-REG-000622",
      "ksm_code": "KSM-SYN-REG-000622",
      "name": "Задвижка клиновая DN25 PN16",
      "item_type": "задвижка",
      "quantity": 29.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 29.0; оценка правил",
      "source_id": "MTR-SYN-REG-000622",
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
      "mtr_code": "MTR-SYN-REG-000623",
      "ksm_code": "KSM-SYN-REG-000623",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 48.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 48.0; оценка правил",
      "source_id": "MTR-SYN-REG-000623",
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
      "mtr_code": "MTR-SYN-REG-000624",
      "ksm_code": "KSM-SYN-REG-000624",
      "name": "Задвижка шиберная DN400 PN160",
      "item_type": "задвижка",
      "quantity": 22.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 22.0; оценка правил",
      "source_id": "MTR-SYN-REG-000624",
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
      "mtr_code": "MTR-SYN-REG-000625",
      "ksm_code": "KSM-SYN-REG-000625",
      "name": "Задвижка клиновая DN50 PN16",
      "item_type": "задвижка",
      "quantity": 58.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 58.0; оценка правил",
      "source_id": "MTR-SYN-REG-000625",
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
      "mtr_code": "MTR-SYN-REG-000626",
      "ksm_code": "KSM-SYN-REG-000626",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 9.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 9.0; оценка правил",
      "source_id": "MTR-SYN-REG-000626",
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
      "mtr_code": "MTR-SYN-REG-000627",
      "ksm_code": "KSM-SYN-REG-000627",
      "name": "Задвижка шиберная DN300 PN160",
      "item_type": "задвижка",
      "quantity": 12.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 12.0; оценка правил",
      "source_id": "MTR-SYN-REG-000627",
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
      "mtr_code": "MTR-SYN-REG-000628",
      "ksm_code": "KSM-SYN-REG-000628",
      "name": "Задвижка клиновая DN250 PN100",
      "item_type": "задвижка",
      "quantity": 71.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 71.0; оценка правил",
      "source_id": "MTR-SYN-REG-000628",
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
      "mtr_code": "MTR-SYN-REG-000629",
      "ksm_code": "KSM-SYN-REG-000629",
      "name": "Задвижка клиновая DN80 PN25",
      "item_type": "задвижка",
      "quantity": 56.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 56.0; оценка правил",
      "source_id": "MTR-SYN-REG-000629",
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
      "mtr_code": "MTR-SYN-REG-000630",
      "ksm_code": "KSM-SYN-REG-000630",
      "name": "Задвижка шиберная DN300 PN160",
      "item_type": "задвижка",
      "quantity": 51.0,
      "status": "совпадает по параметрам",
      "detail": "на складе: 51.0; оценка правил",
      "source_id": "MTR-SYN-REG-000630",
      "unit_id": null,
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [
        "тип изделия"
      ],
      "mismatched_params": [],
      "missing_params": []
    }
  ],
  "warnings": [
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Закрытая задвижка не должна автоматически считаться заменой физической заглушки.",
    "Без трассы и проектной схемы нельзя определить точное количество деталей.",
    "Место и параметры арматуры нельзя окончательно определить без проектной схемы.",
    "Для типа «задвижка» не указаны обязательные параметры: DN, PN, марка стали. Уточните их для точного подбора."
  ],
  "warning_categories": {
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД."
    ],
    "Экспертная проверка": [
      "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом."
    ],
    "Прочее": [
      "Закрытая задвижка не должна автоматически считаться заменой физической заглушки.",
      "Без трассы и проектной схемы нельзя определить точное количество деталей.",
      "Место и параметры арматуры нельзя окончательно определить без проектной схемы.",
      "Для типа «задвижка» не указаны обязательные параметры: DN, PN, марка стали. Уточните их для точного подбора."
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
      "id": "COMP-SYN-031",
      "fragment": "UNIT-SYN-WATER-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-031",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-032",
      "fragment": "UNIT-SYN-WATER-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-032",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-033",
      "fragment": "UNIT-SYN-WATER-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-033",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-034",
      "fragment": "UNIT-SYN-WATER-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-034",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-035",
      "fragment": "UNIT-SYN-WATER-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-035",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-036",
      "fragment": "UNIT-SYN-WATER-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-036",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000591",
      "fragment": "Задвижка клиновая DN80 PN25"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000591",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000592",
      "fragment": "Задвижка клиновая DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000592",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000593",
      "fragment": "Задвижка шиберная DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000593",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000594",
      "fragment": "Задвижка шиберная DN250 PN100"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000594",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000595",
      "fragment": "Задвижка клиновая DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000595",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000596",
      "fragment": "Задвижка клиновая DN80 PN25"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000596",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000597",
      "fragment": "Задвижка шиберная DN80 PN25"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000597",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000598",
      "fragment": "Задвижка шиберная DN100 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000598",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000599",
      "fragment": "Задвижка шиберная DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000599",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000600",
      "fragment": "Задвижка клиновая DN25 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000600",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000601",
      "fragment": "Задвижка клиновая DN250 PN100"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000601",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000602",
      "fragment": "Задвижка шиберная DN25 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000602",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000603",
      "fragment": "Задвижка клиновая DN150 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000603",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000604",
      "fragment": "Задвижка клиновая DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000604",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000605",
      "fragment": "Задвижка клиновая DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000605",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000606",
      "fragment": "Задвижка шиберная DN100 PN40"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000606",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000607",
      "fragment": "Задвижка клиновая DN250 PN100"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000607",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000608",
      "fragment": "Задвижка клиновая DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000608",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000609",
      "fragment": "Задвижка шиберная DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000609",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000610",
      "fragment": "Задвижка клиновая DN80 PN25"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000610",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000611",
      "fragment": "Задвижка клиновая DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000611",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000612",
      "fragment": "Задвижка клиновая DN400 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000612",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000613",
      "fragment": "Задвижка клиновая DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000613",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000614",
      "fragment": "Задвижка клиновая DN400 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000614",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
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
      "id": "MTR-SYN-REG-000616",
      "fragment": "Задвижка клиновая DN80 PN25"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000616",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000617",
      "fragment": "Задвижка клиновая DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000617",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000618",
      "fragment": "Задвижка клиновая DN25 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000618",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000619",
      "fragment": "Задвижка клиновая DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000619",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000620",
      "fragment": "Задвижка шиберная DN400 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000620",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000621",
      "fragment": "Задвижка клиновая DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000621",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000622",
      "fragment": "Задвижка клиновая DN25 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000622",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000623",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000623",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000624",
      "fragment": "Задвижка шиберная DN400 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000624",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000625",
      "fragment": "Задвижка клиновая DN50 PN16"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000625",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000626",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000626",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000627",
      "fragment": "Задвижка шиберная DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000627",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000628",
      "fragment": "Задвижка клиновая DN250 PN100"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000628",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000629",
      "fragment": "Задвижка клиновая DN80 PN25"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000629",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000630",
      "fragment": "Задвижка шиберная DN300 PN160"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000630",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000591",
      "fragment": "остаток: 4.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000592",
      "fragment": "остаток: 25.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000593",
      "fragment": "остаток: 38.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000594",
      "fragment": "остаток: 50.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000595",
      "fragment": "остаток: 11.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000596",
      "fragment": "остаток: 14.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000597",
      "fragment": "остаток: 61.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000598",
      "fragment": "остаток: 22.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000599",
      "fragment": "остаток: 72.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000600",
      "fragment": "остаток: 15.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000601",
      "fragment": "остаток: 25.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000602",
      "fragment": "остаток: 72.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000603",
      "fragment": "остаток: 20.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000604",
      "fragment": "остаток: 23.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000605",
      "fragment": "остаток: 37.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000606",
      "fragment": "остаток: 10.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000607",
      "fragment": "остаток: 42.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000608",
      "fragment": "остаток: 29.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000609",
      "fragment": "остаток: 80.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000610",
      "fragment": "остаток: 26.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000611",
      "fragment": "остаток: 65.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000612",
      "fragment": "остаток: 41.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000613",
      "fragment": "остаток: 80.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000614",
      "fragment": "остаток: 51.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000615",
      "fragment": "остаток: 77.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000616",
      "fragment": "остаток: 8.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000617",
      "fragment": "остаток: 8.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000618",
      "fragment": "остаток: 9.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000619",
      "fragment": "остаток: 68.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000620",
      "fragment": "остаток: 13.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000621",
      "fragment": "остаток: 13.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000622",
      "fragment": "остаток: 29.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000623",
      "fragment": "остаток: 48.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000624",
      "fragment": "остаток: 22.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000625",
      "fragment": "остаток: 58.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000626",
      "fragment": "остаток: 9.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000627",
      "fragment": "остаток: 12.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000628",
      "fragment": "остаток: 71.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000629",
      "fragment": "остаток: 56.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000630",
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
  "human_review_required": false,
  "status": "требует проверки",
  "recommendations": [
    "Уточните параметры запроса: тип изделия, DN, PN, среда.",
    "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.89,
  "parsed_query": {
    "original_query": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры",
    "operations": [
      "replace",
      "assemble"
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
      "item_type": "тройник",
      "subtype": null,
      "designation": null,
      "name": "тройник",
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
        "method": "user_query",
        "missing_fields": [
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
          "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
        }
      ]
    },
    "cards": [
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "тройник",
        "subtype": null,
        "designation": null,
        "name": "тройник",
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
          "method": "user_query",
          "missing_fields": [
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
            "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
          }
        ]
      },
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "труба",
        "subtype": null,
        "designation": null,
        "name": "труба",
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
          "method": "user_query",
          "missing_fields": [
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
            "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
          }
        ]
      },
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
          "method": "user_query",
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
            "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
          }
        ]
      },
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "заглушка",
        "subtype": null,
        "designation": null,
        "name": "заглушка",
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
          "method": "user_query",
          "missing_fields": [
            "dn",
            "geometry",
            "pn",
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
            "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
          }
        ]
      },
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "переход",
        "subtype": null,
        "designation": null,
        "name": "переход",
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
          "method": "user_query",
          "missing_fields": [
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
            "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
          }
        ]
      },
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": "задвижка",
        "subtype": null,
        "designation": null,
        "name": "задвижка",
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
          "method": "user_query",
          "missing_fields": [
            "dn",
            "geometry",
            "pn",
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
            "fragment": "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока и подбери ее параметры"
          }
        ]
      }
    ],
    "technical_filters": {},
    "stock_filters": {},
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
    "impact_analysis": {},
    "unit_context": {},
    "component_context": {},
    "references": [],
    "ambiguities": [],
    "required_agents": [
      "plan",
      "search"
    ],
    "required_capabilities": [
      "assembly_planning",
      "replacement_matching"
    ],
    "confidence": 0.89,
    "confidence_details": {
      "operations": 0.6000000000000001,
      "card": 0.7,
      "ambiguities": 1.0
    },
    "intents": [
      "ADD_COMPONENT"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "ADD_COMPONENT": []
    },
    "params": {
      "item_type": "тройник"
    },
    "primary_intent": "ADD_COMPONENT",
    "groups": [
      {
        "group": "ПОИСК",
        "score": 1,
        "confidence": 1.0,
        "matched": [
          "подбери"
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

>>> Время выполнения: 11486 мс
