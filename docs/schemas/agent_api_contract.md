# Контракт API агента

Этот документ отделяет работу интерфейса и проверки качества от реализации
парсера, PostgreSQL, Qdrant и инструментов агента. Backend может менять
внутреннее устройство, но поля публичного ответа меняются только после
согласования обеими ветками.

## POST /route

Запрос:

```json
{
  "query": "Найди замену задвижке DN150 PN40 и покажи остатки"
}
```

Обязательные поля ответа:

```json
{
  "route": "agent",
  "intent": "replacement",
  "intent_label": "Подбор замены",
  "mode": "inventory_and_match",
  "reasons": ["Нужно проверить каталог, правила и склад"],
  "required_tools": ["catalog_search", "rules_engine", "stock_query"],
  "exact_codes": [],
  "missing_parameters": [],
  "llm_refined": false,
  "router_confidence": null
}
```

`route` принимает только `ordinary`, `agent` или `clarification`.
`missing_parameters` должен содержать машинные названия полей, например
`angle`, `wall_thickness`, `pn`.

## POST /agent

Запрос совпадает с `/route`. Обязательные поля ответа:

```json
{
  "query": "Найди замену задвижке DN150 PN40 и покажи остатки",
  "route": "agent",
  "intent": "replacement",
  "intent_label": "Подбор замены",
  "mode": "offline_rules",
  "tools_used": ["catalog_search", "rules_engine", "stock_query"],
  "answer": "Найдены кандидаты. Итоговое решение принимает эксперт.",
  "components": [
    {
      "mtr_code": "MTR-SYN-000001",
      "ksm_code": "KSM-SYN-000001",
      "name": "Задвижка DN150 PN40",
      "item_type": "задвижка",
      "quantity": 4,
      "status": "требует проверки",
      "detail": "Совпали DN и PN",
      "source_id": "CARD-000001"
    }
  ],
  "warnings": ["Пригодность к H2S нужно подтвердить по паспорту или ТУ"],
  "sources": [
    {
      "kind": "catalog",
      "id": "CARD-000001",
      "fragment": "Задвижка DN150 PN40"
    }
  ],
  "missing_parameters": [],
  "human_review_required": true,
  "parsed_confidence": 0.94,
  "review_verdict": "needs_review",
  "review_issues": []
}
```

`sources.kind` использует согласованные значения: `catalog`, `stock`,
`object_graph`, `passport`, `tu`, `lnd`, `standard`, `regulation`,
`expert_decisions`. Неизвестное значение разрешено показать в UI, но оно
не засчитывается как требуемый источник в приёмочных тестах.

## Извлечённая карточка

Для проверки парсера и показа пользователю `/route` и `/agent` возвращают
поле `parsed_query`. Оно использует существующую Pydantic-модель `ParsedQuery`
из `backend/app/schemas.py`. В схеме поле оставлено необязательным для обратной
совместимости, но штатные endpoint заполняют его всегда.

```json
{
  "parsed_query": {
    "card": {
      "item_type": "задвижка",
      "geometry": {"dn": 150},
      "pressure": {"pn": 40},
      "environment": {
        "medium": "H2S",
        "h2s_confirmed": null
      },
      "coating": {
        "inner_coating": true,
        "outer_coating": null
      }
    },
    "operations": ["replace", "inventory"],
    "unit_ids": [],
    "component_ids": [],
    "on_stock": true,
    "confidence": 0.94
  }
}
```

Здесь `null` означает «неизвестно», а `false` означает подтверждённое
отсутствие признака. Интерфейс и тесты не должны смешивать эти значения.

## Совместимость веток

- Напарник владеет реализацией `/route`, `/agent`, parser, agents и хранилищами.
- Ветка интерфейса владеет отображением, стресс-набором и black-box проверкой.
- Новые поля можно добавлять без согласования, если старые поля сохраняются.
- Переименование или удаление поля требует одновременного обновления контракта,
  интерфейса и тестов.
- Ошибка одного инструмента должна быть отражена в `warnings`; весь ответ не
  должен превращаться в HTTP 500, если можно показать частичный результат.

## Запуск стресс-проверки

При запущенном backend из корня проекта:

```powershell
python -m frontend.agent_eval_cli
```

Ограниченный прогон и сохранение отчёта:

```powershell
python -m frontend.agent_eval_cli --limit 5 --output artifacts/agent-report.json
```

Набор находится в `data/evaluation/agent_stress_cases_50.jsonl`. Он отдельно
проверяет отрицания, неопределённость, опечатки, конфликты, несколько действий
в одном запросе и неполные запросы.
