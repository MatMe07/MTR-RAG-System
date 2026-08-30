# План Фазы 1 — качество детерминированного пути поиска

Дата: 2026-08-30
Статус: завершено

## Контекст
9 прогонов app_console по complex_questions_40.jsonl (AQ001/008/012/016/021/028/030/036/039,
файлы compose_check/1*.txt…9*.txt) показали системные дефекты детерминированного режима:

| Симптом | Кейсы | Причина |
|---|---|---|
| Все кандидаты «не соответствует», H2S-кандидаты не в топе | AQ001 | PN-единицы: каталог хранит PN40 как 40, парсер превращал в 4.0 МПа |
| Ответ = дамп 120–132 компонент, коды продублированы | AQ008, 012, 016, 021, 028, 030, 036, 039 | `_merge_result` конкатенировал: каталог 40 + склад 40 + правила 40 |
| Неверный интент: план обслуживания → inventory, добавь деталь → replacement | AQ016, AQ028 | `_resolve_intent` брал первую операцию, intents игнорировались |
| expert=False в H2S/CO2/replacement-сценариях | AQ012, 028, 030, 039 | `determine_status` не эскалировал среда→эксперт |
| Фильтры не учитывали PN/среду/mark | AQ001, AQ008 | `_matches_filters` только dn/angle/стенка/тип |

## Решения (зафиксированы)
1. **Канон PN = «PN-класс»** (число 40, а не МПа): PN40→40, `working_pressure_mpa` отдельно (/10).
   - `parsing/normalizers/normalizers.py::normalize_pn_from_text` — не делить на 10.
   - `parsing/parsers/pressure_parser.py` — `pn`=40, `working_pressure_mpa`=/10.
2. **Фильтры/веса catalog_search**: `_matches_filters` + pn (число); `_match_score` + medium (подстрока),
   steel_grade, material; score=None при отсутствии параметров (иначе липовые 50% → «не соответствует»).
   H2S/CO2-кандидаты в топе. None-безопасная сортировка в `catalog_search` и `tool_dal.search_catalog`.
3. **Дедуп ответа**: `_dedup_components`/`_merge_rows` — каталог+правила+склад = одна запись
   (ключ mtr_code/ksm_code; бескодовые — по name/item_type/status). builder: топ-10 кандидатов + ≤25 вспомогательных.
4. **Интент по семантике**: новый `intent/resolver.py` — приоритет maintenance > object_configuration >
   document_search > impact_analysis > replacement > inventory > equipment_guidance > duplicates > search;
   используются parsed.intents; новый гранулярный `ADD_COMPONENT` (§1B) для «добавь/укомплектуй деталь»;
   `_det_PLAN_REPAIR` по плановой лексике (план/обслуживание/запчасти/перечисли); при конфликте
   maintenance/inventory решает лексика («составь план обслуживания» → maintenance, «посчитай запас» → inventory).
5. **Статус/эксперт**: best-счёт только по компонентам со score; без скоринга → «требует проверки»;
   intent∈{replacement, maintenance, object_configuration, document_search} + medium H2S/CO2/коррозионный
   → STATUS_EXPERT; `evaluate_candidate`: среда сравнивается по подстроке.

## Проверка
- pytest (без REPtest_ocr.py): **221 passed, 12 skipped**.
- Прогон 9 AQ: интенты AQ008/012→inventory, AQ016/030→maintenance, AQ028→object_configuration,
  AQ036→impact_analysis, AQ039→document_search; AQ001→задвижки DN150 PN40 в топе и статус «требует эксперта»;
  компонентов 14–35 против 120–132, коды не дублируются.

## Осталось на Фазу 2 (вне объёма Фазы 1)
- Сбор комплекта (соседние детали/REMKIT) для AQ028/030 — сейчас список из общего каталога.
- `search_by_passport`: нулевые параметры паспорта → score None.
- `FIND_BY_CODE`: каталожный поиск по mtr/ksm коду (сейчас каталог фильтруется только по параметрам).
- Proposed-changes → impact (`impact_analysis`) для AQ036-сценариев с заменой диаметра (частично уже учитывается).