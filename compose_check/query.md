2026-09-15 23:54:14,172 INFO    | pymorphy2.opencorpora_dict.wrapper | Loading dictionaries from /home/artur/.local/lib/python3.14/site-packages/pymorphy2_dicts_ru/data
2026-09-15 23:54:14,197 INFO    | pymorphy2.opencorpora_dict.wrapper | format: 2.4, revision: 417127, updated: 2020-10-11T15:05:51.070345
Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-15 23:54:14,726 INFO    | mtr.agent.executor               | [Executor] Execute query='Сколько отводов 90 426 на 10 есть на складе и какие из них подходят для H2S' mode=auto request_id=297fd908-60ce-4e3f-ba5e-12a30a81e5ae
2026-09-15 23:54:14,726 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-15 23:54:14,749 INFO    | pymorphy2.opencorpora_dict.wrapper | Loading dictionaries from /home/artur/.local/lib/python3.14/site-packages/pymorphy2_dicts_ru/data
2026-09-15 23:54:14,773 INFO    | pymorphy2.opencorpora_dict.wrapper | format: 2.4, revision: 417127, updated: 2020-10-11T15:05:51.070345
2026-09-15 23:54:15,568 WARNING | mtr.agent.dynamic_rules          | DynamicRules: БД недоступна, дефолты кода: (psycopg2.OperationalError) could not translate host name "db" to address: Name or service not known

(Background on this error at: https://sqlalche.me/e/20/e3q8)
2026-09-15 23:54:15,604 WARNING | mtr.repository.redis_cache       | RedisCache: Redis недоступен, кеш отключён: Error -2 connecting to redis:6379. Name or service not known.
2026-09-15 23:54:15,696 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.97 operations=['inventory', 'check'] item_types=['отвод'] technical_filters={'item_type': 'отвод', 'dn': 426.0, 'wall_thickness': 10.0, 'angle': 90.0, 'medium': 'H2S', 'h2s_confirmed': True} ambiguities=[] (969ms)
2026-09-15 23:54:15,712 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=COMPLETE intents=['FIND_BY_PARAMS', 'CHECK_STOCK'] missing={'FIND_BY_PARAMS': [], 'CHECK_STOCK': []}
2026-09-15 23:54:15,722 INFO    | mtr.agent.executor               | [Executor] Intent resolved: inventory
2026-09-15 23:54:15,722 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-15 23:54:15,890 WARNING | mtr.repository                   | DbRepository.get_catalog failed: (psycopg2.OperationalError) could not translate host name "db" to address: Name or service not known

(Background on this error at: https://sqlalche.me/e/20/e3q8), using JSON fallback
2026-09-15 23:54:16,162 INFO    | mtr.repository                   | JsonRepository fallback loaded 1000 cards
2026-09-15 23:54:16,162 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-15 23:54:16,177 INFO    | mtr.agent.tools                  | [catalog_search] Found 4 candidates (from 1000 cards) in 15ms
2026-09-15 23:54:16,275 INFO    | mtr.agent.tools                  | [stock_query] Checked 4 items (kept 4) in 96ms
2026-09-15 23:54:16,277 INFO    | mtr.agent.tools                  | [rules_engine] Scored 4 candidates in 0ms
2026-09-15 23:54:16,281 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
2026-09-15 23:54:16,287 INFO    | mtr.agent.executor               | [Executor] Graph finished in 565ms: components=4 sources=37 warnings=2 tools_used=['catalog_search', 'stock_query', 'inventory_calculator', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-15 23:54:16,287 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-15 23:54:16,319 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-15 23:54:16,319 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

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
      "detail": "на складе: 58; оценка правил",
      "source_id": "SYN-REG-CARD-000249",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда",
        "H2S-совместимость стали"
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
      "detail": "на складе: 52; оценка правил",
      "source_id": "SYN-REG-CARD-000330",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда",
        "H2S-совместимость стали"
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
      "detail": "на складе: 26; оценка правил",
      "source_id": "SYN-REG-CARD-000372",
      "unit_id": null,
      "match_score": 1.0,
      "match_percent": 100,
      "tz_status": "соответствует",
      "matched_params": [
        "тип изделия",
        "DN",
        "стенка",
        "угол",
        "среда",
        "H2S-совместимость стали"
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
      "detail": "на складе: 71; оценка правил",
      "source_id": "SYN-REG-CARD-000323",
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
      "mismatched_params": [
        "H2S-совместимость стали"
      ],
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
      "id": "SYN-REG-CARD-000249",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17375-2001",
      "fragment": "Бесшовные приварные отводы из углеродистой и низколегированной стали типа 3D с R=1,5 DN; область применения определяется совместно с ГОСТ 17380-2001."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17380-2001",
      "fragment": "Общие технические условия для отводов, тройников, переходов и заглушек при PN до 16 МПа и температуре от -70 до +450 °C. Конкретные условия применения задаются проектной или конструкторской документацией с учётом транспортируемого вещества и внешней среды."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-28338-89",
      "fragment": "Устанавливает ряды значений номинальных диаметров DN и их обозначения для соединений трубопроводов и арматуры."
    },
    {
      "kind": "passport_or_tu",
      "id": "SYN-REG-CARD-000249",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "SYN-REG-CARD-000330",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17375-2001",
      "fragment": "Бесшовные приварные отводы из углеродистой и низколегированной стали типа 3D с R=1,5 DN; область применения определяется совместно с ГОСТ 17380-2001."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17380-2001",
      "fragment": "Общие технические условия для отводов, тройников, переходов и заглушек при PN до 16 МПа и температуре от -70 до +450 °C. Конкретные условия применения задаются проектной или конструкторской документацией с учётом транспортируемого вещества и внешней среды."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-28338-89",
      "fragment": "Устанавливает ряды значений номинальных диаметров DN и их обозначения для соединений трубопроводов и арматуры."
    },
    {
      "kind": "passport_or_tu",
      "id": "SYN-REG-CARD-000330",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "SYN-REG-CARD-000372",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17375-2001",
      "fragment": "Бесшовные приварные отводы из углеродистой и низколегированной стали типа 3D с R=1,5 DN; область применения определяется совместно с ГОСТ 17380-2001."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17380-2001",
      "fragment": "Общие технические условия для отводов, тройников, переходов и заглушек при PN до 16 МПа и температуре от -70 до +450 °C. Конкретные условия применения задаются проектной или конструкторской документацией с учётом транспортируемого вещества и внешней среды."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-28338-89",
      "fragment": "Устанавливает ряды значений номинальных диаметров DN и их обозначения для соединений трубопроводов и арматуры."
    },
    {
      "kind": "passport_or_tu",
      "id": "SYN-REG-CARD-000372",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "SYN-REG-CARD-000323",
      "fragment": "ОКШ 90-426x10 09ГСФ"
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17375-2001",
      "fragment": "Бесшовные приварные отводы из углеродистой и низколегированной стали типа 3D с R=1,5 DN; область применения определяется совместно с ГОСТ 17380-2001."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17380-2001",
      "fragment": "Общие технические условия для отводов, тройников, переходов и заглушек при PN до 16 МПа и температуре от -70 до +450 °C. Конкретные условия применения задаются проектной или конструкторской документацией с учётом транспортируемого вещества и внешней среды."
    },
    {
      "kind": "standard",
      "id": "RST-GOST-28338-89",
      "fragment": "Устанавливает ряды значений номинальных диаметров DN и их обозначения для соединений трубопроводов и арматуры."
    },
    {
      "kind": "passport_or_tu",
      "id": "SYN-REG-CARD-000323",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000249",
      "fragment": "остаток: 58"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000330",
      "fragment": "остаток: 52"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000372",
      "fragment": "остаток: 26"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000323",
      "fragment": "остаток: 71"
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
      "kind": "standard",
      "id": "RST-GOST-28338-89",
      "fragment": "Соединения трубопроводов и арматура. Номинальные диаметры. Ряды"
    },
    {
      "kind": "standard",
      "id": "RST-GOST-17380-2001",
      "fragment": "Детали трубопроводов бесшовные приварные. Общие технические условия"
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
    ],
    "parser_diagnostics": {
      "parse_ms": 91.04156494140625,
      "strategy": "enrich",
      "rule_confidence": 0.97,
      "natasha_used": true,
      "stages_ms": {
        "rule": 61.310529708862305,
        "natasha": 29.584169387817383,
        "merge": 0.13709068298339844
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
  "verification_verdict": "pass",
  "verification_reasons": [],
  "mode_refined": "auto",
  "llm_refine_failed": null,
  "llm_tokens_used": null,
  "offer_full_llm": false,
  "offer_question": "",
  "offer_endpoint": null,
  "llm": {
    "available": true,
    "used": false,
    "reason": "LLM не вызывался: детерминированный auto-ответ прошёл quality gate (verdict=pass)",
    "model": "inclusionai/ling-3.0-flash-vl:free",
    "total_calls": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "duration_ms": 0.0,
    "cost_estimate_usd": 0.0,
    "refine_iterations": [],
    "calls": []
  }
}
========================================================================

>>> Время выполнения: 1593 мс
