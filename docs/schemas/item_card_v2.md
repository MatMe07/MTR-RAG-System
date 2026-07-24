# Карточка изделия v2

## Назначение

`item_card.schema.json` описывает единый контракт между PostgreSQL, API, rules engine, Qdrant, LLM и интерфейсом эксперта.

Карточка разделена на две части:

1. Строгая шапка содержит поля, общие для всех изделий.
2. `properties` содержит изменяемый набор характеристик и сохраняется в PostgreSQL как `JSONB`.

Так труба, отвод, переход и задвижка могут иметь разные характеристики без добавления новых колонок в таблицу `items`.

## Строгая шапка

Обязательные поля:

- `schema_version` - версия JSON-контракта, сейчас `2.0`;
- `card_id` - постоянный идентификатор изделия или `null` для ещё не сохранённого запроса;
- `card_version` - версия конкретной карточки;
- `lifecycle_status` - общий статус карточки;
- `item_type`, `subtype`, `name`, `designation` - идентификация изделия;
- `codes.mtr_code`, `codes.ksm_code` - бизнес-коды;
- `dcd` - положение карточки в структуре поиска;
- `properties` - динамические характеристики;
- `sources` - источники и подтверждающие фрагменты.

## DCD

Блок `dcd` используется для предварительного ограничения области поиска:

- `domain` - верхняя предметная область, например `gas_pipeline`;
- `collection` - однородная группа, например `pipes` или `shutoff_valves`;
- `document` - основной документ, по которому создана карточка.

Если карточка собрана из нескольких документов, основной документ указывается в `dcd.document`, а все использованные документы перечисляются в `sources`.

## Динамические характеристики

Каждый ключ в `properties` является кодом характеристики:

```json
{
  "dn": {
    "value": 159,
    "value_type": "number",
    "raw_value": "DN 159",
    "unit": "mm",
    "status": "normalized",
    "confidence": 0.98,
    "source_fragment_ids": ["fragment-001"]
  }
}
```

Rules engine должен использовать `value` и `value_type`. Поля `raw_value`, `status`, `confidence` и `source_fragment_ids` нужны для объяснения результата и аудита.

## Источники

`source_fragment` хранит точное место, откуда получено значение:

- `fragment_id` - идентификатор фрагмента;
- `text` - исходный текст;
- `page` - страница PDF;
- `row` - строка Excel;
- `bbox` - координаты области на странице.

Значение `properties.<parameter>.source_fragment_ids` должно ссылаться на существующий `sources[].source_fragment.fragment_id`.

## Три состояния

Для логических параметров обязательно различаются:

- `true` - наличие или применимость подтверждены;
- `false` - отсутствие или неприменимость подтверждены;
- `null` - информации нет.

Пример неизвестного покрытия:

```json
{
  "inner_coating": {
    "value": null,
    "value_type": "boolean",
    "raw_value": null,
    "unit": null,
    "status": "unknown",
    "confidence": null,
    "source_fragment_ids": []
  }
}
```

Rules engine не должен превращать `null` в `false`. Неизвестное покрытие или неподтверждённая H2S/CO2-среда получают статус `требует проверки`.

## Перенос карточек v1

Соответствие старых и новых полей:

| Карточка v1 | Карточка v2 |
|---|---|
| `card_id` | `card_id` |
| `mtr_code` | `codes.mtr_code` |
| `ksm_code` | `codes.ksm_code` |
| `geometry.dn` | `properties.dn` |
| `geometry.d1` | `properties.d1` |
| `geometry.d2` | `properties.d2` |
| `geometry.wall_thickness` | `properties.wall_thickness` |
| `geometry.angle` | `properties.angle` |
| `pressure.pn` | `properties.pn` |
| `material.steel_grade` | `properties.steel_grade` |
| `material.strength_class` | `properties.strength_class` |
| `environment.h2s_confirmed` | `properties.h2s_confirmed` |
| `environment.co2_confirmed` | `properties.co2_confirmed` |
| `coating.inner_coating` | `properties.inner_coating` |
| `coating.outer_coating` | `properties.outer_coating` |
| `normative.gost_tu` | `properties.gost_tu` |

Старый `expected_item_cards.jsonl` остаётся в формате v1 до выполнения миграции backend. Смешивать v1 и v2 в одной таблице без `schema_version` нельзя.

## Примеры

- `examples/item_card_v2_pipe.json` - труба, включая `true`, `false` и `null`;
- `examples/item_card_v2_elbow.json` - отвод;
- `examples/item_card_v2_reducer.json` - переход с двумя диаметрами;
- `examples/item_card_v2_valve.json` - задвижка со специфическими характеристиками.

## Проверка готовности

- схема соответствует JSON Schema Draft 2020-12;
- все четыре примера проходят валидацию;
- неизвестные значения сохранены как `null`;
- каждая подтверждённая характеристика ссылается на источник;
- произвольные новые характеристики добавляются без изменения схемы.
