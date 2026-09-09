Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 16:23:22,972 INFO    | mtr.agent.executor               | [Executor] Execute query='Хотим поставить задвижку DN200 вместо DN150, покажи какие соседние детали придется заменить или проверить' mode=auto request_id=None
2026-09-09 16:23:22,972 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 16:23:23,251 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.84 operations=['replace', 'check', 'impact', 'search'] item_types=['задвижка'] technical_filters={'item_type': 'задвижка', 'dn': 200} ambiguities=[] (278ms)
2026-09-09 16:23:23,264 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['FIND_BY_PARAMS', 'REPLACE_WITH_DIFFERENT_SIZE', 'CHECK_STOCK', 'IMPACT_DIAMETER_CHANGE'] missing={'FIND_BY_PARAMS': [], 'REPLACE_WITH_DIFFERENT_SIZE': ['unit_id'], 'CHECK_STOCK': [], 'IMPACT_DIAMETER_CHANGE': []}
2026-09-09 16:23:23,272 INFO    | mtr.agent.executor               | [Executor] Intent resolved: impact_analysis
2026-09-09 16:23:23,272 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 16:23:23,412 INFO    | mtr.agent.tools                  | [graph_search] No unit_ids/component_ids provided; object sources only
2026-09-09 16:23:23,413 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 16:23:23,419 INFO    | mtr.agent.tools                  | [catalog_search] Found 16 candidates (from 1000 cards) in 6ms
2026-09-09 16:23:23,421 INFO    | mtr.agent.tools                  | [rules_engine] Scored 16 candidates in 0ms
2026-09-09 16:23:23,425 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
2026-09-09 16:23:23,430 INFO    | mtr.agent.executor               | [Executor] Graph finished in 158ms: components=23 sources=38 warnings=2 tools_used=['graph_search', 'catalog_search', 'impact_analyzer', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 16:23:23,430 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 16:23:23,459 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 16:23:23,459 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Хотим поставить задвижку DN200 вместо DN150, покажи какие соседние детали придется заменить или проверить",
  "intent": "impact_analysis",
  "intent_label": "Анализ влияния",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "catalog_search",
    "impact_analyzer",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "• ГОСТ 5762-2002 — Арматура трубопроводная промышленная. Задвижки на номинальное давление не более PN 250. Общие технические условия: Задвижки общепромышленного назначения на номинальное давление не более PN 250; стандарт не распространяется на неметаллические и футерованные задвижки.\n• ГОСТ 5762-2002 — Арматура трубопроводная промышленная. Задвижки на номинальное давление не более PN 250. Общие технические условия: Задвижки общепромышленного назначения на номинальное давление не более PN 250; стандарт не распространяется на неметаллические и футерованные задвижки.",
  "components": [
    {
      "mtr_code": "MTR-SYN-REG-000623",
      "ksm_code": "KSM-SYN-REG-000623",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 48.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000623",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
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
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000626",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000632",
      "ksm_code": "KSM-SYN-REG-000632",
      "name": "Задвижка шиберная DN200 PN63",
      "item_type": "задвижка",
      "quantity": 49.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000632",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000634",
      "ksm_code": "KSM-SYN-REG-000634",
      "name": "Задвижка шиберная DN200 PN63",
      "item_type": "задвижка",
      "quantity": 6.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000634",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000642",
      "ksm_code": "KSM-SYN-REG-000642",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 48.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000642",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000654",
      "ksm_code": "KSM-SYN-REG-000654",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 4.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000654",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000674",
      "ksm_code": "KSM-SYN-REG-000674",
      "name": "Задвижка шиберная DN200 PN63",
      "item_type": "задвижка",
      "quantity": 35.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000674",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000676",
      "ksm_code": "KSM-SYN-REG-000676",
      "name": "Задвижка шиберная DN200 PN63",
      "item_type": "задвижка",
      "quantity": 7.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000676",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000681",
      "ksm_code": "KSM-SYN-REG-000681",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 36.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000681",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000693",
      "ksm_code": "KSM-SYN-REG-000693",
      "name": "Задвижка клиновая DN200 PN63",
      "item_type": "задвижка",
      "quantity": 70.0,
      "status": "совпадает по параметрам",
      "detail": "оценка правил",
      "source_id": "MTR-SYN-REG-000693",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN"
      ],
      "mismatched_params": [],
      "missing_params": []
    }
  ],
  "warnings": [
    "Изменение DN является изменением узла и не должно утверждаться автоматически.",
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Система не заменяет наряд и производственную процедуру безопасного проведения работ.",
    "Точный состав узла определяется проектной схемой, которой может не быть в MVP.",
    "Большее значение PN не гарантирует совместимость задвижки с фланцами и соседними деталями.",
    "Для типа «задвижка» не указаны обязательные параметры: PN, марка стали. Уточните их для точного подбора."
  ],
  "warning_categories": {
    "Прочее": [
      "Изменение DN является изменением узла и не должно утверждаться автоматически.",
      "Система не заменяет наряд и производственную процедуру безопасного проведения работ.",
      "Точный состав узла определяется проектной схемой, которой может не быть в MVP.",
      "Большее значение PN не гарантирует совместимость задвижки с фланцами и соседними деталями.",
      "Для типа «задвижка» не указаны обязательные параметры: PN, марка стали. Уточните их для точного подбора."
    ],
    "Совместимость со средой": [
      "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД."
    ],
    "Экспертная проверка": [
      "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом."
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
      "id": "MTR-SYN-REG-000632",
      "fragment": "Задвижка шиберная DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000632",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000634",
      "fragment": "Задвижка шиберная DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000634",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000642",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000642",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000654",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000654",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000674",
      "fragment": "Задвижка шиберная DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000674",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000676",
      "fragment": "Задвижка шиберная DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000676",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000681",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000681",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000693",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000693",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000698",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000698",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000705",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000705",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000708",
      "fragment": "Задвижка шиберная DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000708",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000714",
      "fragment": "Задвижка шиберная DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000714",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000722",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000722",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000730",
      "fragment": "Задвижка клиновая DN200 PN63"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000730",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "project_documentation",
      "id": null,
      "fragment": "оценка влияния требует проектной схемы"
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
  "status": "соответствует",
  "recommendations": [
    "Проверьте предупреждения перед принятием решения."
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.84,
  "parsed_query": {
    "original_query": "Хотим поставить задвижку DN200 вместо DN150, покажи какие соседние детали придется заменить или проверить",
    "operations": [
      "replace",
      "check",
      "impact",
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
      "designation": "DN200",
      "name": "задвижка DN200",
      "geometry": {
        "dn": 200.0,
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
          "fragment": "Хотим поставить задвижку DN200 вместо DN150, покажи какие соседние детали придется заменить или проверить"
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
        "designation": "DN200",
        "name": "задвижка DN200",
        "geometry": {
          "dn": 200.0,
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
            "fragment": "Хотим поставить задвижку DN200 вместо DN150, покажи какие соседние детали придется заменить или проверить"
          }
        ]
      }
    ],
    "technical_filters": {
      "item_type": "задвижка",
      "dn": 200
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
    "proposed_changes": {
      "dn_to": 200.0,
      "dn_from": 150.0
    },
    "impact_analysis": {
      "required_checks": [
        "проверить совместимость с соседними деталями"
      ],
      "affected_components": [
        "фланцы",
        "прокладки",
        "болты"
      ]
    },
    "unit_context": {},
    "component_context": {
      "connections": [
        "соседние детали"
      ]
    },
    "references": [],
    "ambiguities": [],
    "required_agents": [
      "impact",
      "rules",
      "search"
    ],
    "required_capabilities": [
      "compatibility_check",
      "impact_analysis",
      "replacement_matching",
      "search"
    ],
    "confidence": 0.84,
    "confidence_details": {
      "operations": 1.0,
      "card": 0.6,
      "ambiguities": 1.0
    },
    "intents": [
      "FIND_BY_PARAMS",
      "REPLACE_WITH_DIFFERENT_SIZE",
      "CHECK_STOCK",
      "IMPACT_DIAMETER_CHANGE"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "FIND_BY_PARAMS": [],
      "REPLACE_WITH_DIFFERENT_SIZE": [
        "unit_id"
      ],
      "CHECK_STOCK": [],
      "IMPACT_DIAMETER_CHANGE": []
    },
    "params": {
      "item_type": "задвижка",
      "dn": 200
    },
    "primary_intent": "FIND_BY_PARAMS",
    "groups": [
      {
        "group": "ЗАМЕНА",
        "score": 3,
        "confidence": 0.6,
        "matched": [
          "замени",
          "заменить",
          "вместо"
        ]
      },
      {
        "group": "ПОИСК",
        "score": 1,
        "confidence": 0.2,
        "matched": [
          "покажи"
        ]
      },
      {
        "group": "АНАЛИЗ",
        "score": 1,
        "confidence": 0.2,
        "matched": [
          "проверить"
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

>>> Время выполнения: 487 мс
