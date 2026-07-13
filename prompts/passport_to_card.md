# Prompt: текст паспорта/OCR -> карточка изделия

Ты извлекаешь параметры изделия из текста паспорта, OCR-результата или таблицы.

Верни строго JSON по схеме ItemCard. Не добавляй текст до или после JSON.

Главные правила:

- Не выдумывай значения.
- Если параметр не найден, ставь `null`.
- Если значение найдено, укажи исходный фрагмент в `sources.fragment`.
- Если есть номер страницы, сохрани его в `sources.page`.
- Если есть противоречивые значения, выбери наиболее вероятное, а спорные поля добавь в `extraction.missing_fields` или оставь `null`.
- Заводской номер не должен превращаться в отдельный МТР. Это признак экземпляра, а не типовой позиции.
- Сертификат покрытия не является отдельным МТР, если пользователь ищет отвод/трубу/задвижку/заглушку. Он может подтверждать признак покрытия.

Ищи параметры:

- наименование изделия;
- условное обозначение;
- тип и подтип;
- DN, D1, D2;
- угол;
- толщина стенки;
- PN/Ру, рабочее давление, испытательное давление;
- марка стали;
- класс прочности;
- ГОСТ/ТУ на изделие;
- ГОСТ/ТУ на материал;
- рабочая среда;
- H2S/CO2;
- внутреннее/наружное покрытие;
- климатическое исполнение;
- источник: файл, страница, фрагмент.

Формат входа:

```text
file: 2608736.pdf
page: 1
text:
Паспорт на отвод ОКШ 90-КП-250-159(10К50)-4-0,6-1,5DN-09Г2С-УХЛ...
```

Формат ответа:

```json
{
  "card_id": null,
  "mtr_code": null,
  "ksm_code": null,
  "item_type": "отвод",
  "subtype": "ОКШ",
  "designation": "ОКШ 90-КП-250-159(10К50)-4-0,6-1,5DN-09Г2С-УХЛ",
  "name": "Отвод ОКШ 90",
  "geometry": {
    "dn": 159,
    "d1": null,
    "d2": null,
    "wall_thickness": 10,
    "wall_thickness_2": null,
    "angle": 90,
    "radius": "1,5DN"
  },
  "pressure": {
    "pn": null,
    "working_pressure_mpa": null,
    "test_pressure_mpa": 6,
    "raw_value": "Рисп = 6 МПа"
  },
  "material": {
    "steel_grade": "09Г2С",
    "strength_class": "К50",
    "standard": null
  },
  "environment": {
    "medium": null,
    "h2s_confirmed": null,
    "co2_confirmed": null,
    "temperature_min_c": null,
    "climate_version": "УХЛ"
  },
  "coating": {
    "inner_coating": null,
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
    "method": "ocr_llm",
    "missing_fields": ["mtr_code", "ksm_code", "medium", "coating"]
  },
  "sources": [
    {
      "type": "passport",
      "file": "2608736.pdf",
      "page": 1,
      "row": null,
      "fragment": "Отвод ОКШ 90-КП-250-159(10К50)-4-0,6-1,5DN-09Г2С-УХЛ"
    }
  ]
}
```
