# План исправления проблем из analysis_40_questions.md

Статус: ВЫПОЛНЯЕТСЯ. Обновлять после каждого шага.

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
- [ ] Хелпер apply_stock_filters(stock_rows, parsed): quantity_min/max/on_stock
- [ ] Применить в stock_query / stock_node / inventory_calculator / builder._to_components
- [ ] Парсер: поддержать `> N`, `< N`, `>=`, `<=` (parser.py:385)
- [ ] Тесты: apply_stock_filters юнит + e2e AQ014 (>50), AQ015 (<3)

## Шаг 3 — Не запускать лишние тулы + ранние answer-ветки (средний)
- [ ] router(): equipment_guidance → лёгкий маршрут catalog → answer
- [ ] Ранние answer-ветки в catalog_router/stock_router/rules_router/maintenance_router
- [ ] graph_router: не гнать equipment_guidance → catalog после graph
- [ ] Тест: справочный запрос запускает <=2 инструмента

## Шаг 4 — Разумность аналитики (средний)
- [ ] inventory_calculator: множитель units_count (×3), дефицит, limit (AQ011/012)
- [ ] duplicate_detector: группировка результата (AQ013)
- [ ] maintenance_planner: текстовый план + перечень запчастей (AQ016-20)
- [ ] impact_analyzer: затронутые соседи/несовместимые (AQ036-38)

## Шаг 5 — Офлайн-шаблоны ответов (средний)
- [ ] answer/builder.py + explanation.py: шаблоны по интентам/категориям
      (EXPLAIN_TERM/DIF, PLAN_REPAIR/BUILD_REPAIR_KIT, IMPACT_*)
- [ ] AQ001/006/007: mandatory_warning попадает в answer.warnings

## Шаг 6 — LLM-путь + авто-эскалация (средний)
- [ ] Настроить LLM (OpenRouter/LLM_API_KEY)
- [ ] auto-эскалация C1 refine / C2 full LLM для сложных категорий
- [ ] Держать deterministic без поломок

## Шаг 7 — Локальные дефекты парсера/материала/DN (по кейсам)
- [ ] AQ007: парсер среды H2S↔CORR (не переопределять явную среду участка)
- [ ] AQ002/AQ004: жёсткий фильтр steel_grade/medium для H2S
- [ ] AQ006: переход 219→159 — проверять оба DN (ужесточить tolerance)
- [ ] AQ022/023/024: классификация intent → equipment_guidance
- [ ] AQ025: правила не требуют параметры уже заданные в карточке
- [ ] AQ039/040: regulation_lookup — расшифровка найденных/отсутствующих ГОСТ

## Шаг 8 — Верификация (обязательно после каждого шага)
- [ ] Полный pytest (стек 300+)
- [ ] e2e AQ014/AQ015 + точечные
- [ ] Ре-прогон eval_40_auto.py, фиксация метрик (PASS/REVIEW, tools_ok, sources_ok,
      среднее число инструментов на запрос)

## Метрики цели (из анализа)
- tools на справочный запрос: 5 → ≤2
- AQ014: только quantity>50; AQ015: только quantity<3
- completed=True на всех 40
- Текстовые answer_text без LLM по всем категориям
