# Prompt: пользовательский запрос -> карточка изделия

Ты извлекаешь инженерные параметры изделия из пользовательского запроса.

Верни строго JSON по схеме ItemCard. Не добавляй текст до или после JSON.

Правила:

- Не выдумывай значения.
- Если параметр не указан, ставь `null`.
- Если параметр указан неявно, запиши нормализованное значение и добавь исходный фрагмент в `sources`.
- Считай `ДУ`, `DU` и «условный проход» синонимами `DN`.
- Считай `Ру`, `PY` и `PU` синонимами `PN`.
- Запись `426 на 10`, `426х10` или `426x10` означает наружный диаметр 426 и толщину стенки 10, а не `DN426`.
- В трубопроводном контексте «колено» нормализуется как тип `отвод`.
- Если пользователь говорит "сероводород", "H2S", "кислая среда" - это относится к `environment.medium` и может требовать `h2s_confirmed = null`, если подтверждения нет.
- Если пользователь говорит "внутреннее покрытие" или "наружное покрытие", заполни блок `coating`.
- Если запрос неполный, всё равно верни карточку с пропусками в `extraction.missing_fields`.

Поля, которые нужно искать:

- тип изделия: отвод, труба, задвижка, заглушка, переход, тройник;
- подтип: ОКШ, ОГ и т.д.;
- DN / диаметр;
- D1/D2 для переходов и тройников;
- угол для отводов;
- толщина стенки;
- PN/Ру или давление;
- марка стали;
- класс прочности;
- среда: H2S, CO2, газ, вода, нефть;
- внутреннее/наружное покрытие;
- ГОСТ/ТУ;
- климатическое исполнение.

Пример входа:

```text
Нужен отвод 90 DN159 стенка 10 К48 для H2S с внутренним покрытием.
```

Пример ответа:

```json
{
  "card_id": null,
  "mtr_code": null,
  "ksm_code": null,
  "item_type": "отвод",
  "subtype": null,
  "designation": null,
  "name": null,
  "geometry": {
    "dn": 159,
    "d1": null,
    "d2": null,
    "wall_thickness": 10,
    "wall_thickness_2": null,
    "angle": 90,
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
    "strength_class": "К48",
    "standard": null
  },
  "environment": {
    "medium": "H2S",
    "h2s_confirmed": null,
    "co2_confirmed": null,
    "temperature_min_c": null,
    "climate_version": null
  },
  "coating": {
    "inner_coating": true,
    "outer_coating": null,
    "coating_type": null,
    "coating_standard": null
  },
  "normative": {
    "gost_tu": null,
    "lnd_sections": []
  },
  "extraction": {
    "confidence": null,
    "method": "user_query",
    "missing_fields": ["subtype", "pn", "steel_grade", "gost_tu"]
  },
  "sources": [
    {
      "type": "user_query",
      "file": null,
      "page": null,
      "row": null,
      "fragment": "Нужен отвод 90 DN159 стенка 10 К48 для H2S с внутренним покрытием"
    }
  ]
}
```
