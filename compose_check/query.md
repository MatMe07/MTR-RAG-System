Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-13 13:25:15,143 INFO    | mtr.agent.executor               | [Executor] Execute query='Сколько отводов 90 426 на 10 есть на складе и какие из них подходят для H2S' mode=auto request_id=None
2026-09-13 13:25:15,143 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-13 13:25:15,491 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.97 operations=['inventory', 'check'] item_types=['отвод'] technical_filters={'item_type': 'отвод', 'dn': 426.0, 'wall_thickness': 10.0, 'angle': 90.0, 'medium': 'H2S', 'h2s_confirmed': True} ambiguities=[] (348ms)
2026-09-13 13:25:15,504 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['FIND_BY_PARAMS', 'CHECK_STOCK'] missing={'FIND_BY_PARAMS': [], 'CHECK_STOCK': []}
2026-09-13 13:25:15,513 INFO    | mtr.agent.executor               | [Executor] Intent resolved: inventory
2026-09-13 13:25:15,513 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-13 13:25:15,661 INFO    | mtr.repository                   | DbRepository: loaded 1000 MTR items from DB
2026-09-13 13:25:15,675 INFO    | mtr.repository                   | DbRepository: loaded 1000 CandidateItems for stock lookup
2026-09-13 13:25:15,734 INFO    | mtr.repository                   | DbRepository: catalog built with 1000 cards
2026-09-13 13:25:15,736 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-13 13:25:15,750 INFO    | mtr.agent.tools                  | [catalog_search] Found 4 candidates (from 1000 cards) in 14ms
2026-09-13 13:25:15,770 INFO    | mtr.agent.tools                  | [stock_query] Checked 4 items (kept 4) in 19ms
2026-09-13 13:25:15,772 INFO    | mtr.agent.tools                  | [rules_engine] Scored 4 candidates in 0ms
2026-09-13 13:25:15,776 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
2026-09-13 13:25:15,780 INFO    | mtr.agent.executor               | [Executor] Graph finished in 267ms: components=4 sources=23 warnings=2 tools_used=['catalog_search', 'stock_query', 'inventory_calculator', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-13 13:25:15,780 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-13 13:25:15,808 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-13 13:25:15,808 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Сколько отводов 90 426 на 10 есть на складе и какие из них подходят для H2S",
  "intent": "inventory",
  "intent_label": "Склад и запас",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "catalog_search",
    "stock_query",
    "inventory_calculator",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "Проверены остатки по 4 позициям складского учёта.",
  "components": [
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
    }
  ],
  "warnings": [
    "Расчёт — черновик: нормы запаса требуют утверждения",
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "Нельзя суммировать как подходящие позиции без подтверждения их работы в H2S.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.",
    "Рекомендуемое количество является расчетным до получения норм страхового запаса.",
    "Расчет нужно пересчитать после получения утвержденных норм страхового запаса.",
    "Заявка остается черновиком до утверждения норм запаса и технической пригодности.",
    "Для типа «отвод» не указаны обязательные параметры: марка стали. Уточните их для точного подбора."
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
      "Нельзя суммировать как подходящие позиции без подтверждения их работы в H2S.",
      "Заявка остается черновиком до утверждения норм запаса и технической пригодности."
    ],
    "Экспертная проверка": [
      "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом."
    ],
    "Прочее": [
      "Для типа «отвод» не указаны обязательные параметры: марка стали. Уточните их для точного подбора."
    ]
  },
  "purchase_recommendation": null,
  "sources": [
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
      "kind": "standard",
      "id": "RST-GOST-17375-2001",
      "fragment": "Детали трубопроводов. Отводы крутоизогнутые типа 3D. Конструкция"
    },
    {
      "kind": "regulation",
      "id": "regulation_matrix.json",
      "fragment": null
    }
  ],
  "missing_parameters": [],
  "human_review_required": true,
  "human_review_reasons": [
    "expert_data"
  ],
  "status": "соответствует",
  "recommendations": [
    "Проверьте предупреждения перед принятием решения."
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.97,
  "parsed_query": {
    "original_query": "Сколько отводов 90 426 на 10 есть на складе и какие из них подходят для H2S",
    "operations": [
      "inventory",
      "check"
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
          "fragment": "Сколько отводов 90 426 на 10 есть на складе и какие из них подходят для H2S"
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
            "fragment": "Сколько отводов 90 426 на 10 есть на складе и какие из них подходят для H2S"
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
      "rules"
    ],
    "required_capabilities": [
      "compatibility_check",
      "inventory"
    ],
    "confidence": 0.97,
    "confidence_details": {
      "operations": 0.6000000000000001,
      "card": 0.9,
      "ambiguities": 1.0
    },
    "intents": [
      "FIND_BY_PARAMS",
      "CHECK_STOCK"
    ],
    "status": "COMPLETE",
    "missing_params": {
      "FIND_BY_PARAMS": [],
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
        "group": "СКЛАД",
        "score": 2,
        "confidence": 1.0,
        "matched": [
          "склад",
          "сколько"
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

>>> Время выполнения: 665 мс
