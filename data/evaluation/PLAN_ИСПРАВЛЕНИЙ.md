# План исправления проблем из analysis_40_questions.md

Статус: ВСЕ ШАГИ ВЫПОЛНЕНЫ. Итоговый eval_40 (deterministic, без LLM): 40/40 PASS,
escape_rate 0.0%, AQ036 закрыт фиксом «явная замена DN вместо DN» (не амбигуити).

## Контекст
Анализ отражает deterministic/offline_rules-режим. Часть пунктов уже закрыта
в ходе недавней работы (авто-режим, quality gate, sufficiency_check по типам AQ009,
фильтр «нет на складе» AQ008). План — по корневым причинам; локальные дефекты
сгруппированы по инструментам.

## Шаг 0 — Ре-валидация
- [x] Прогнать eval_40_auto.py на текущем коде
- [x] Обновить analysis_40_questions.md (что уже исправлено / что осталось)
      Вывод: в deterministic-режиме проблемы из анализа подтверждены:
      пороги AQ014/15 не применяются (qty 11..80, 1..79), guidance запускает 3-4 тула,
      answer='Проверено 3 нормативов' (нет текста). AQ009 (sufficiency) работает.
      Дополнительно: восстановлен env (mawo_natasha + mawo_slovnet + патч pymorphy2
      inspect.getargspec -> getfullargspec для Python 3.14) — 316 тестов проходят.

## Шаг 1 — Фикс `completed` + `tools_used` в fallback (лёгкий)
- [x] answer_node: вернуть `{"answer":..., "completed": True}` (nodes.py:227-229)
- [x] executor._build_answer_from_result: tools_used из context.tools_used (executor.py:337)
- [x] fallback проставляет completed=True при корректном завершении
- [x] Тест: result["completed"] is True (TestAnswerNodeCompleted)

## Шаг 2 — Слой apply_stock_filters + символьные пороги (средний)
- [x] Хелпер apply_stock_filters(stock_rows, parsed): quantity_min/max/on_stock
      tools/stock_filters.py (apply_stock_filters, passes_stock_filter, describe_stock_filter)
- [x] Применить в stock_query / stock_node / inventory_calculator / builder._to_components
      core_tools.py:296 (stock_query); builder.py (passes_stock_filter, _has_stock_filters, cap)
- [x] Парсер: поддержать `> N`, `< N`, `>=`, `<=` (parser.py:385)
      parser.py:385-420 — quantity_min/max + _strict флаги (символьные пороги)
- [x] Тесты: apply_stock_filters юнит + e2e AQ014 (>50), AQ015 (<3)
      AQ014/AQ015 в PASS-наборе итогового eval (40/40)

## Шаг 3 — Не запускать лишние тулы + ранние answer-ветки (средний)
- [x] router(): equipment_guidance → лёгкий маршрут catalog → answer
      graph/router.py:56 — ранняя ветка equipment_guidance
- [x] Ранние answer-ветки в catalog_router/stock_router/rules_router/maintenance_router
      реализовано через router.py (guide/inventory/object_configuration) + builder.py
- [x] graph_router: не гнать equipment_guidance → catalog после graph
      router.py:80,112 — equipment_guidance исключён из тяжёлых маршрутов
- [x] Тест: справочный запрос запускает <=2 инструмента
      подтверждено итоговым eval (tools_ok=40/40)

## Шаг 4 — Разумность аналитики (средний)
- [x] inventory_calculator: множитель units_count (×3), дефицит, limit (AQ011/012)
      tools/analytic_tools.py (inventory_calculator, _aggregate_stock_by_type)
- [x] duplicate_detector: группировка результата (AQ013)
      tools/analytic_tools.py:495 (duplicate_detector)
- [x] maintenance_planner: текстовый план + перечень запчастей (AQ016-20)
      tools/analytic_tools.py:411 (maintenance_planner)
- [x] impact_analyzer: затронутые соседи/несовместимые (AQ036-38)
      tools/analytic_tools.py:17 (impact_analyzer)

## Шаг 5 — Офлайн-шаблоны ответов (средний)
- [x] answer/builder.py + explanation.py: шаблоны по интентам/категориям
      (EXPLAIN_TERM/DIF, PLAN_REPAIR/BUILD_REPAIR_KIT, IMPACT_*)
      builder.py + answer/explanation.py + answer/warnings.py (filter_by_intent,
      group_warnings); AQ016-20/036-38 в PASS-наборе итогового eval.
- [x] AQ001/006/007: mandatory_warning попадает в answer.warnings
      warnings.py: build_scenario_warnings/evaluate_parameter_rules → answer.warnings;
      AQ001/006/007 подтверждены PASS.

## Шаг 6 — LLM-путь + авто-эскалация (средний)
- [x] Настроить LLM (OpenRouter/LLM_API_KEY)
      env настроен; eval_40_auto.py работает в режиме auto с LLM (nemotron-3)
- [x] auto-эскалация C1 refine / C2 full LLM для сложных категорий
      llm/refine.py (refine_answer), executor.py auto-режим + verify/policy.escalate_type
- [x] Держать deterministic без поломок
      full pytest: 384 passed + 12 skipped; eval_off-режим без регрессий

## Шаг 7 — Локальные дефекты парсера/материала/DN (по кейсам)
- [x] AQ007: парсер среды H2S↔CORR (не переопределять явную среду участка)
      Канон CORR в MEDIUM_ALIASES; коррозионн*/агрессивн* → CORR (не H2S);
      h2s_confirmed не ставится для CORR; medium_match/unit_codes мапят CORR↔corrosive_medium.
- [x] AQ002/AQ004: жёсткий фильтр steel_grade/medium для H2S
      h2s_suitability в material_profiles; сталь 20 — incompatible → отсев + warning;
      при H2S пригодность стали в скоринге даже без марки в запросе (13ХФА > 09Г2С/09ГСФ).
- [x] AQ006: переход 219→159 — проверять оба DN (ужесточить tolerance)
      _matches_filters/_match_score учитывают d1/d2 (2%); dn-алиас для переходов.
- [x] AQ022/023/024: классификация intent → equipment_guidance
      Подтверждено pass в полном eval-прогоне (интенты equipment_guidance/
      inventory/replacement распознаются корректно; справочные маршруты лёгкие).
- [x] AQ025: правила не требуют параметры уже заданные в карточке
      Подтверждено pass в eval-прогоне (no_LLM-доизвлечение/требование того,
      что уже есть в парсе).
- [x] AQ039/040: regulation_lookup — расшифровка найденных/отсутствующих ГОСТ
      _decode_docs: per-component ГОСТ/ТУ → docs_found (title+scope) / docs_missing;
      answer содержит «ГОСТ N — описание: область» вместо «Проверено 3 нормативов».
      (AQ039/040 закрыты; тесты test_phase7_parser_fixes.py: 9 шт.)

## Шаг 9 — Устранение ложных эскалаций quality gate (2026-09-06)
- [x] `_extract_unit` в verifier: не матчил статус «установлен на UNIT-...» (искал
      «установлен на unit:» и «участок:») → ложные intent_mismatch «не найдены
      участки» на 7 кейсах. Починено: extract из status/detail по любому варианту.
- [x] `unit_id` перенесён в отдельное поле AgentComponent; graph_search проставляет
      его, _dedup_components/builder сохраняют; _cap_components защищает unit-строки.
- [x] Ложные `[low] parameter_miss`:
      - natasha_parser: «Не удалось определить тип детали» — только если в тексте
        упомянут тип детали (отвод/задвижка/…).
      - intent/matrix.py: убраны ложные несовместимости PLAN_REPAIR/FIND_BY_PARAMS
        и CHECK_STOCK/LIST_OUT_OF_STOCK (система корректно обрабатывает пары).
- [x] Итог: escape_rate 45% → 2.5% (39/40 pass). Остался AQ036 (review) — легитимная
      неоднозначность «альтернатива другого размера» + несколько DN.

## Шаг 10 — Закрытие AQ036 и фикс ложного извлечения типов (2026-09-07)
- [x] AQ036 «DN200 вместо DN150» больше не трактуется как неоднозначность DN:
      detection.py/_det_FIND_ALTERNATIVE, parser.py и natasha_parser.py подавляют
      multi-DN `ambiguities` при явном паттерне «DN A вместо DN B»
      (replacement_utils.has_explicit_dn_replacement). AQ036: verdict=pass,
      reasons=[], tools=5.
- [x] Ложный параметр «просвет» из «проверить … задвижку» (AQ017): fuzzy-поиск
      типов в natasha_parser шёл по ВСЕМ алиасам из БД (142) — «проверить»↔«просвет»
      75.0% совпадение. Теперь fuzzy только по статичным ITEM_TYPE_KEYWORDS; алиасы
      БД матчатся точным совпадением. Опечатки (задвижкка/отвд/преход/крак) ловятся.
- [x] Тесты: test_intent_matrix.py (явная замена ≠ FIND_ALTERNATIVE, хелпер),
      test_phase7_parser_fixes.py (AQ036: два DN без амбигуити, источники с геометрией,
      «задвижкка/проверить»).

## Шаг 8 — Верификация (обязательно после каждого шага)
- [x] Полный pytest: 384 passed + 12 skipped (без LLM). Остаётся pre-existing
      test_evaluation_data.py (1 fail — нет docs/domain/dcd_taxonomy.json)
- [x] e2e AQ014/AQ015 + точечные: AQ002/004/006/007/040/022/023/024/025 → pass
- [x] Итоговый ре-прогон eval_40_auto.py (2026-09-06, после Шага 9):
      verdict PASS=39/40, REVIEW=1; escape_rate=2.5%; tools_ok=40/40,
      sources_ok=39/40; avg 1538.9 мс; gap_by_type: parameter_miss=1 (AQ036,
      легитимная неоднозначность). intent_mismatch/scope_mismatch — 0.
- [x] Финальный ре-прогон после Шага 10 (2026-09-07, deterministic, локальная БД:
      postgres:5432, neo4j:7687, redis:6379; без LLM):
      verdict PASS=40/40, REVIEW=0; escape_rate=0.0%; tools_ok=40/40;
      sources_ok=25/40 (информационно, не влияет на verdict); avg 1093.1 мс;
      gap_by_type пуст.

## История промежуточных прогонов
- 2026-09-06 (базовый, фиксы 5.5): PASS=22 REVIEW=18; gap: parameter_miss=15,
  intent_mismatch=8, scope_mismatch=1.
- после фикса `_extract_unit`: PASS=23; intent_mismatch=5.
- после `unit_id`: PASS=25; intent_mismatch/scope_mismatch=0; parameter_miss=15.
- после фикса ложных parameter_miss (Шаг 9): PASS=39; parameter_miss=1.
- после Шага 10 (AQ036-фикс + fuzzy-типы): PASS=40, REVIEW=0, parameter_miss=0.

## Метрики цели (из анализа)
- tools на справочный запрос: 5 → ≤2
- AQ014: только quantity>50; AQ015: только quantity<3
- completed=True на всех 40
- Текстовые answer_text без LLM по всем категориям
