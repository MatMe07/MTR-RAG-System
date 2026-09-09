Запрос: Метод поиска (0 - deterministic, 1 - llm, 2 - auto): 
>>> Режим: auto

2026-09-09 15:52:05,398 INFO    | mtr.agent.executor               | [Executor] Execute query='Покажи все детали для H2S, которых сейчас нет на складе, и расставь их по срочности закупки' mode=auto request_id=None
2026-09-09 15:52:05,398 INFO    | mtr.agent.executor               | [Executor] No parsed query, running HybridParser...
2026-09-09 15:52:05,603 INFO    | mtr.agent.executor               | [Executor] Parsed: confidence=0.64 operations=['inventory', 'plan', 'search'] item_types=[] technical_filters={'medium': 'H2S', 'h2s_confirmed': True} ambiguities=[] (205ms)
2026-09-09 15:52:05,633 INFO    | mtr.agent.executor               | [Executor] Parsed enriched: status=PARTIAL intents=['CHECK_STOCK', 'LIST_OUT_OF_STOCK'] missing={'CHECK_STOCK': ['ksm_code'], 'LIST_OUT_OF_STOCK': []}
2026-09-09 15:52:05,641 INFO    | mtr.agent.executor               | [Executor] Intent resolved: inventory
2026-09-09 15:52:05,641 INFO    | mtr.agent.executor               | [Executor] Invoking graph...
2026-09-09 15:52:05,832 INFO    | mtr.agent.tools                  | [graph_search] Found 12 components, 12 targets in 7ms
2026-09-09 15:52:05,833 INFO    | mtr.agent.tools                  | [catalog_search] Loaded 1000 cards from repository
2026-09-09 15:52:05,850 INFO    | mtr.agent.tools                  | [catalog_search] Found 40 candidates (from 1000 cards) in 17ms
2026-09-09 15:52:05,978 INFO    | mtr.agent.tools                  | [stock_query] Checked 40 items (kept 40) in 127ms
2026-09-09 15:52:05,979 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=3 для KSM-SYN-REG-000008: тип=труба(база=1), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000223: тип=отвод(база=2), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000444: тип=переход(база=2), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=5 для KSM-SYN-REG-000593: тип=задвижка(база=3), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=3 для KSM-SYN-REG-000746: тип=заглушка(база=1), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000876: тип=тройник(база=2), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=3 для KSM-SYN-REG-000001: тип=труба(база=1), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000225: тип=отвод(база=2), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000441: тип=переход(база=2), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=5 для KSM-SYN-REG-000594: тип=задвижка(база=3), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=3 для KSM-SYN-REG-000741: тип=заглушка(база=1), нет на складе(+2)
2026-09-09 15:52:05,980 INFO    | mtr.agent.tools                  | [inventory_calculator] urgency=4 для KSM-SYN-REG-000880: тип=тройник(база=2), нет на складе(+2)
2026-09-09 15:52:05,982 INFO    | mtr.agent.tools                  | [rules_engine] Scored 40 candidates in 1ms
2026-09-09 15:52:05,986 INFO    | mtr.agent.tools                  | [regulation_lookup] Checked 1 regulations in 3ms
Ты — технический эксперт по МТР. На основе следующих данных составь понятное объяснение для инженера.

Критические параметры (нельзя менять, они должны совпадать): ['среда']
Запрос: Покажи все детали для H2S, которых сейчас нет на складе, и расставь их по срочности закупки
Найденные детали:
- Труба бесшовная горячедеформированная 108x6 20: установлен на UNIT-SYN-H2S-001
- ОКШ 90-76x4 09ГСФ: установлен на UNIT-SYN-H2S-001
- Переход концентрический 108x4-76x4 13ХФА: установлен на UNIT-SYN-H2S-001
- Задвижка шиберная DN50 PN16: установлен на UNIT-SYN-H2S-001
- Заглушка эллиптическая приварная 377x12 13ХФА: установлен на UNIT-SYN-H2S-001
Результаты проверок: —
Предупреждения: ['Расчёт — черновик: нормы запаса требуют утверждения', 'Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.', 'Указанная среда не является доказательством стойкости каждого установленного компонента.', 'План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.', 'Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.', 'Рекомендуемое количество является расчетным до получения норм страхового запаса.', 'Расчет нужно пересчитать после получения утвержденных норм страхового запаса.', 'Заявка остается черновиком до утверждения норм запаса и технической пригодности.']
Ошибки: —

Твой ответ должен быть:
1. Кратким (3–5 предложений).
2. Содержать рекомендацию (какую деталь выбрать, что проверить).
3. Если есть риски — указать их.
4. Не повторять сухие технические данные — переформулировать их.
5. Если хотя бы один критический параметр не совпал — явно указать это.

Ответ:
🔍 API Key resolved: OK
🔍 Base URL: https://openrouter.ai/api/v1/
🔍 Model: nvidia/nemotron-3-super-120b-a12b:free
2026-09-09 15:52:07,511 INFO    | httpx2                           | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
2026-09-09 15:52:32,337 INFO    | mtr.agent.executor               | [Executor] Graph finished in 26697ms: components=52 sources=159 warnings=2 tools_used=['graph_search', 'catalog_search', 'stock_query', 'inventory_calculator', 'rules_engine', 'regulation_lookup'] completed=True
2026-09-09 15:52:32,338 INFO    | mtr.agent.executor               | [Executor] Answer found in state, returning directly
2026-09-09 15:52:32,370 INFO    | mtr.agent.verify                 | [Verifier] verdict=pass gaps=0 max_severity=none reasons=[]
2026-09-09 15:52:32,370 INFO    | mtr.agent.executor               | [Executor][auto] verdict=pass, no LLM escalation needed

========================================================================
>>> ОТВЕТ (как возвращает агент):
{
  "query": "Покажи все детали для H2S, которых сейчас нет на складе, и расставь их по срочности закупки",
  "intent": "inventory",
  "intent_label": "Склад и запас",
  "route": "agent",
  "mode": "auto",
  "tools_used": [
    "graph_search",
    "catalog_search",
    "stock_query",
    "inventory_calculator",
    "rules_engine",
    "regulation_lookup"
  ],
  "explanation": "Критический параметр «среда» (H₂S) совпадает с запросом, поэтому дальнейший анализ корректен. На складе отсутствуют сведения о недостающих позициях – все перечисленные детали уже смонтированы на UNIT‑SYN‑H2S‑001, поэтому срочная закупка пока не требуется. Рекомендую уточнить фактические остатки на складе и запросить паспорта/ТУ на эти изделия, чтобы подтвердить их стойкость к H₂S, CO₂ и коррозионной среде. Риск заключается в том, что reliance только на геометрические ГОСТы не гарантирует материальную пригодность; без документации возможен преждевременный отказ компонентов. После получения утверждённых норм страхового запаса следует пересчитать потребности и оформить заявку на закупку только тех позиций, которых действительно не хватает.",
  "components": [
    {
      "mtr_code": "MTR-SYN-REG-000008",
      "ksm_code": "KSM-SYN-REG-000008",
      "name": "Труба бесшовная горячедеформированная 108x6 20",
      "item_type": "труба",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "рекомендуется закупить: труба; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-007",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000223",
      "ksm_code": "KSM-SYN-REG-000223",
      "name": "ОКШ 90-76x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: отвод нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-008",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000444",
      "ksm_code": "KSM-SYN-REG-000444",
      "name": "Переход концентрический 108x4-76x4 13ХФА",
      "item_type": "переход",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: переход нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-009",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000593",
      "ksm_code": "KSM-SYN-REG-000593",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: задвижка нужна срочно; нет остатков; нет на складе — срочность закупки: критическая",
      "source_id": "COMP-SYN-010",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000746",
      "ksm_code": "KSM-SYN-REG-000746",
      "name": "Заглушка эллиптическая приварная 377x12 13ХФА",
      "item_type": "заглушка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "рекомендуется закупить: заглушка; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-011",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000876",
      "ksm_code": "KSM-SYN-REG-000876",
      "name": "Тройник переходный 426x12-325x10 13ХФА",
      "item_type": "тройник",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: тройник нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-012",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000001",
      "ksm_code": "KSM-SYN-REG-000001",
      "name": "Труба бесшовная горячедеформированная 530x16 09ГСФ",
      "item_type": "труба",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "рекомендуется закупить: труба; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-019",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000225",
      "ksm_code": "KSM-SYN-REG-000225",
      "name": "ОКШ 90-133x6 09ГСФ",
      "item_type": "отвод",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: отвод нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-020",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000441",
      "ksm_code": "KSM-SYN-REG-000441",
      "name": "Переход эксцентрический 133x5-89x4 20",
      "item_type": "переход",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: переход нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-021",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000594",
      "ksm_code": "KSM-SYN-REG-000594",
      "name": "Задвижка шиберная DN250 PN100",
      "item_type": "задвижка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: задвижка нужна срочно; нет остатков; нет на складе — срочность закупки: критическая",
      "source_id": "COMP-SYN-022",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000741",
      "ksm_code": "KSM-SYN-REG-000741",
      "name": "Заглушка эллиптическая приварная 76x4 09ГСФ",
      "item_type": "заглушка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "рекомендуется закупить: заглушка; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-023",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000880",
      "ksm_code": "KSM-SYN-REG-000880",
      "name": "Тройник переходный 89x4-57x3 20",
      "item_type": "тройник",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: тройник нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-024",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000008",
      "ksm_code": "KSM-SYN-REG-000008",
      "name": "Труба бесшовная горячедеформированная 108x6 20",
      "item_type": "труба",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "рекомендуется закупить: труба; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-007",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000223",
      "ksm_code": "KSM-SYN-REG-000223",
      "name": "ОКШ 90-76x4 09ГСФ",
      "item_type": "отвод",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: отвод нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-008",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000444",
      "ksm_code": "KSM-SYN-REG-000444",
      "name": "Переход концентрический 108x4-76x4 13ХФА",
      "item_type": "переход",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: переход нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-009",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000593",
      "ksm_code": "KSM-SYN-REG-000593",
      "name": "Задвижка шиберная DN50 PN16",
      "item_type": "задвижка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: задвижка нужна срочно; нет остатков; нет на складе — срочность закупки: критическая",
      "source_id": "COMP-SYN-010",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000746",
      "ksm_code": "KSM-SYN-REG-000746",
      "name": "Заглушка эллиптическая приварная 377x12 13ХФА",
      "item_type": "заглушка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "рекомендуется закупить: заглушка; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-011",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000876",
      "ksm_code": "KSM-SYN-REG-000876",
      "name": "Тройник переходный 426x12-325x10 13ХФА",
      "item_type": "тройник",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-H2S-001",
      "detail": "критично: тройник нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-012",
      "unit_id": "UNIT-SYN-H2S-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000001",
      "ksm_code": "KSM-SYN-REG-000001",
      "name": "Труба бесшовная горячедеформированная 530x16 09ГСФ",
      "item_type": "труба",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "рекомендуется закупить: труба; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-019",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000225",
      "ksm_code": "KSM-SYN-REG-000225",
      "name": "ОКШ 90-133x6 09ГСФ",
      "item_type": "отвод",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: отвод нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-020",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000441",
      "ksm_code": "KSM-SYN-REG-000441",
      "name": "Переход эксцентрический 133x5-89x4 20",
      "item_type": "переход",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: переход нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-021",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000594",
      "ksm_code": "KSM-SYN-REG-000594",
      "name": "Задвижка шиберная DN250 PN100",
      "item_type": "задвижка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: задвижка нужна срочно; нет остатков; нет на складе — срочность закупки: критическая",
      "source_id": "COMP-SYN-022",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000741",
      "ksm_code": "KSM-SYN-REG-000741",
      "name": "Заглушка эллиптическая приварная 76x4 09ГСФ",
      "item_type": "заглушка",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "рекомендуется закупить: заглушка; нет остатков; нет на складе — срочность закупки: средняя",
      "source_id": "COMP-SYN-023",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    },
    {
      "mtr_code": "MTR-SYN-REG-000880",
      "ksm_code": "KSM-SYN-REG-000880",
      "name": "Тройник переходный 89x4-57x3 20",
      "item_type": "тройник",
      "quantity": 0.0,
      "status": "установлен на UNIT-SYN-MIX-001",
      "detail": "критично: тройник нужна срочно; нет остатков; нет на складе — срочность закупки: высокая",
      "source_id": "COMP-SYN-024",
      "unit_id": "UNIT-SYN-MIX-001",
      "match_score": null,
      "match_percent": null,
      "tz_status": null,
      "matched_params": [],
      "mismatched_params": [],
      "missing_params": []
    }
  ],
  "warnings": [
    "Расчёт — черновик: нормы запаса требуют утверждения",
    "Соответствие H2S, CO2, коррозионной среде и наличие покрытия нельзя подтверждать только геометрическим ГОСТом: нужны паспорт, ТУ, проектная документация и/или внутренний ЛНД.",
    "Указанная среда не является доказательством стойкости каждого установленного компонента.",
    "План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.",
    "Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.",
    "Рекомендуемое количество является расчетным до получения норм страхового запаса.",
    "Расчет нужно пересчитать после получения утвержденных норм страхового запаса.",
    "Заявка остается черновиком до утверждения норм запаса и технической пригодности."
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
      "Указанная среда не является доказательством стойкости каждого установленного компонента.",
      "Заявка остается черновиком до утверждения норм запаса и технической пригодности."
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
      "kind": "object_graph",
      "id": "COMP-SYN-007",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-007",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-008",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-008",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-009",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-009",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-010",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-010",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-011",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-011",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-012",
      "fragment": "UNIT-SYN-H2S-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-012",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-019",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-019",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-020",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-020",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-021",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-021",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-022",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-022",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-023",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-023",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "object_graph",
      "id": "COMP-SYN-024",
      "fragment": "UNIT-SYN-MIX-001"
    },
    {
      "kind": "passport",
      "id": "COMP-SYN-024",
      "fragment": "паспорт изделия (статус в графе требует паспорт)"
    },
    {
      "kind": "maintenance_history",
      "id": "UNIT-SYN-H2S-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)"
    },
    {
      "kind": "maintenance_history",
      "id": "UNIT-SYN-MIX-001",
      "fragment": "риски по истории эксплуатации (МВП: расчётно)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000011",
      "fragment": "Труба бесшовная горячедеформированная 89x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000011",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000013",
      "fragment": "Труба бесшовная горячедеформированная 57x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000013",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000014",
      "fragment": "Труба бесшовная горячедеформированная 273x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000014",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000015",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000015",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000024",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000024",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000027",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000027",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000029",
      "fragment": "Труба бесшовная горячедеформированная 273x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000029",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000032",
      "fragment": "Труба бесшовная горячедеформированная 108x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000032",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000033",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000033",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000036",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000036",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000038",
      "fragment": "Труба бесшовная горячедеформированная 377x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000038",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000046",
      "fragment": "Труба бесшовная горячедеформированная 76x5 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000046",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000061",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000061",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000087",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000087",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000093",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000093",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000098",
      "fragment": "Труба бесшовная горячедеформированная 325x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000098",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000103",
      "fragment": "Труба бесшовная горячедеформированная 426x14 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000103",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000105",
      "fragment": "Труба бесшовная горячедеформированная 530x16 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000105",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000116",
      "fragment": "Труба электросварная спиральношовная 219x8 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000116",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000125",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000125",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000131",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000131",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000135",
      "fragment": "Труба электросварная прямошовная 159x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000135",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000146",
      "fragment": "Труба электросварная спиральношовная 720x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000146",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000149",
      "fragment": "Труба электросварная спиральношовная 530x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000149",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000154",
      "fragment": "Труба электросварная прямошовная 630x12 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000154",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000179",
      "fragment": "Труба электросварная прямошовная 426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000179",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000195",
      "fragment": "Труба электросварная спиральношовная 820x14 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000195",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000208",
      "fragment": "Труба электросварная спиральношовная 426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000208",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000209",
      "fragment": "Труба электросварная спиральношовная 1020x16 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000209",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000226",
      "fragment": "ОКШ 90-57x3 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000226",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000229",
      "fragment": "ОКШ 45-273x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000229",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000231",
      "fragment": "ОКШ 90-426x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000231",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000232",
      "fragment": "ОКШ 90-57x3 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000232",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000237",
      "fragment": "ОКШ 90-76x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000237",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000241",
      "fragment": "ОКШ 90-325x10 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000241",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000242",
      "fragment": "ОКШ 45-219x8 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000242",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000245",
      "fragment": "ОКШ 90-133x6 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000245",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
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
      "id": "MTR-SYN-REG-000283",
      "fragment": "ОКШ 90-76x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000283",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "catalog",
      "id": "MTR-SYN-REG-000289",
      "fragment": "ОКШ 45-108x4 13ХФА"
    },
    {
      "kind": "passport_or_tu",
      "id": "MTR-SYN-REG-000289",
      "fragment": "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000011",
      "fragment": "остаток: 19.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000013",
      "fragment": "остаток: 60.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000014",
      "fragment": "остаток: 26.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000015",
      "fragment": "остаток: 11.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000024",
      "fragment": "остаток: 36.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000027",
      "fragment": "остаток: 3.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000029",
      "fragment": "остаток: 75.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000032",
      "fragment": "остаток: 31.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000033",
      "fragment": "остаток: 56.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000036",
      "fragment": "остаток: 40.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000038",
      "fragment": "остаток: 1.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000046",
      "fragment": "остаток: 7.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000061",
      "fragment": "остаток: 34.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000087",
      "fragment": "остаток: 22.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000093",
      "fragment": "остаток: 53.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000098",
      "fragment": "остаток: 3.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000103",
      "fragment": "остаток: 19.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000105",
      "fragment": "остаток: 75.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000116",
      "fragment": "остаток: 36.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000125",
      "fragment": "остаток: 2.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000131",
      "fragment": "остаток: 73.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000135",
      "fragment": "остаток: 78.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000146",
      "fragment": "остаток: 2.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000149",
      "fragment": "остаток: 4.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000154",
      "fragment": "остаток: 39.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000179",
      "fragment": "остаток: 3.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000195",
      "fragment": "остаток: 42.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000208",
      "fragment": "остаток: 28.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000209",
      "fragment": "остаток: 8.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000226",
      "fragment": "остаток: 41.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000229",
      "fragment": "остаток: 73.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000231",
      "fragment": "остаток: 65.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000232",
      "fragment": "остаток: 30.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000237",
      "fragment": "остаток: 16.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000241",
      "fragment": "остаток: 5.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000242",
      "fragment": "остаток: 47.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000245",
      "fragment": "остаток: 75.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000249",
      "fragment": "остаток: 58.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000283",
      "fragment": "остаток: 17.0"
    },
    {
      "kind": "stock",
      "id": "KSM-SYN-REG-000289",
      "fragment": "остаток: 52.0"
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
      "kind": "regulation",
      "id": "regulation_matrix.json",
      "fragment": null
    }
  ],
  "missing_parameters": [],
  "human_review_required": true,
  "status": "требует проверки",
  "recommendations": [
    "Уточните параметры запроса: тип изделия, DN, PN, среда.",
    "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
  ],
  "expert_review_id": null,
  "parsed_confidence": 0.64,
  "parsed_query": {
    "original_query": "Покажи все детали для H2S, которых сейчас нет на складе, и расставь их по срочности закупки",
    "operations": [
      "inventory",
      "plan",
      "search"
    ],
    "item_types": [],
    "component_ids": [],
    "unit_ids": [],
    "card": {
      "card_id": null,
      "mtr_code": null,
      "ksm_code": null,
      "item_type": null,
      "subtype": null,
      "designation": "H2S",
      "name": null,
      "geometry": {
        "dn": null,
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
        "method": "hybrid",
        "missing_fields": [
          "item_type",
          "dn",
          "geometry",
          "material"
        ]
      },
      "sources": [
        {
          "type": "user_query",
          "file": null,
          "page": null,
          "row": null,
          "fragment": "Покажи все детали для H2S, которых сейчас нет на складе, и расставь их по срочности закупки"
        }
      ]
    },
    "cards": [
      {
        "card_id": null,
        "mtr_code": null,
        "ksm_code": null,
        "item_type": null,
        "subtype": null,
        "designation": "H2S",
        "name": null,
        "geometry": {
          "dn": null,
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
          "method": "hybrid",
          "missing_fields": [
            "item_type",
            "dn",
            "geometry",
            "material"
          ]
        },
        "sources": [
          {
            "type": "user_query",
            "file": null,
            "page": null,
            "row": null,
            "fragment": "Покажи все детали для H2S, которых сейчас нет на складе, и расставь их по срочности закупки"
          }
        ]
      }
    ],
    "technical_filters": {
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
    "sort_by": "procurement_urgency",
    "on_stock": false,
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
      "plan",
      "search"
    ],
    "required_capabilities": [
      "inventory",
      "maintenance_planning",
      "search"
    ],
    "confidence": 0.64,
    "confidence_details": {
      "operations": 0.8,
      "card": 0.6,
      "ambiguities": 1.0
    },
    "intents": [
      "CHECK_STOCK",
      "LIST_OUT_OF_STOCK"
    ],
    "status": "PARTIAL",
    "missing_params": {
      "CHECK_STOCK": [
        "ksm_code"
      ],
      "LIST_OUT_OF_STOCK": []
    },
    "params": {},
    "primary_intent": "CHECK_STOCK",
    "groups": [
      {
        "group": "СКЛАД",
        "score": 2,
        "confidence": 0.667,
        "matched": [
          "склад",
          "закуп"
        ]
      },
      {
        "group": "ПОИСК",
        "score": 1,
        "confidence": 0.333,
        "matched": [
          "покажи"
        ]
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

>>> Время выполнения: 26973 мс
