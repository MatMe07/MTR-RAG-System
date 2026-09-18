# Eval 40 вопросов в auto-режиме (quality gate)

- Дата: 2026-09-17T19:09:20.669547+00:00
- Режим: auto
- Total: 40
- verdict PASS: 18 / REVIEW: 22
- Эскалаций (REVIEW): 22 (55.0%)
- Эскалации по типу: refine=2, full_llm=20, none=18
- C2 (full LLM): 20 кейсов (50.0%), из них пропущено без LLM: 20
- LLM-токены: total=0, avg=None (кейсов: 0)
- tools OK: 40/40
- sources OK: 39/40
- кейсов с sufficiency-verdict: 1
- avg duration: 1481.2 ms

## Распределение gap-типов (reason)

- safety_unconfirmed: 20
- inventory_reply_missing: 3
- intent_mismatch: 1
- scope_mismatch: 1

## По кейсам

| case | cat | verdict | esc | escal | applied | tokens | sufficiency | tools | sources | ms |
|---|---|---|---|---|---|---|---|---|---|---|
| AQ001 | replacement | review | Y | full_llm | none | - | - | P | P | 2542.1 |
| AQ002 | replacement | review | Y | full_llm | none | - | - | P | P | 1525.1 |
| AQ003 | replacement | review | Y | full_llm | none | - | - | P | P | 2480.8 |
| AQ004 | replacement | review | Y | full_llm | none | - | - | P | P | 1417.0 |
| AQ005 | replacement | pass | - | none | none | - | - | P | P | 1406.8 |
| AQ006 | replacement | review | Y | full_llm | none | - | - | P | P | 1319.9 |
| AQ007 | replacement | pass | - | none | none | - | - | P | P | 1180.4 |
| AQ008 | inventory | review | Y | full_llm | none | - | - | P | P | 1869.3 |
| AQ009 | inventory | review | Y | full_llm | none | - | Y | P | P | 1496.3 |
| AQ010 | inventory | review | Y | full_llm | none | - | - | P | P | 965.1 |
| AQ011 | inventory | review | Y | full_llm | none | - | - | P | P | 1696.9 |
| AQ012 | inventory | pass | - | none | none | - | - | P | P | 1304.4 |
| AQ013 | inventory | pass | - | none | none | - | - | P | P | 1849.1 |
| AQ014 | inventory | pass | - | none | none | - | - | P | P | 1956.9 |
| AQ015 | inventory | review | Y | full_llm | none | - | - | P | F | 2042.1 |
| AQ016 | toir | review | Y | full_llm | none | - | - | P | P | 1295.2 |
| AQ017 | toir | review | Y | full_llm | none | - | - | P | P | 1053.2 |
| AQ018 | toir | review | Y | full_llm | none | - | - | P | P | 1498.0 |
| AQ019 | toir | pass | - | none | none | - | - | P | P | 1232.6 |
| AQ020 | toir | pass | - | none | none | - | - | P | P | 1475.7 |
| AQ021 | equipment_guidance | pass | - | none | none | - | - | P | P | 1216.7 |
| AQ022 | equipment_guidance | pass | - | none | none | - | - | P | P | 1063.0 |
| AQ023 | equipment_guidance | pass | - | none | none | - | - | P | P | 1468.4 |
| AQ024 | equipment_guidance | review | Y | refine | none | - | - | P | P | 1315.5 |
| AQ025 | equipment_guidance | pass | - | none | none | - | - | P | P | 1223.7 |
| AQ026 | object_configuration | review | Y | full_llm | none | - | - | P | P | 1754.7 |
| AQ027 | object_configuration | review | Y | full_llm | none | - | - | P | P | 1850.9 |
| AQ028 | object_configuration | pass | - | none | none | - | - | P | P | 2481.7 |
| AQ029 | object_configuration | review | Y | full_llm | none | - | - | P | P | 2097.5 |
| AQ030 | composite_replacement | pass | - | none | none | - | - | P | P | 1280.9 |
| AQ031 | composite_replacement | pass | - | none | none | - | - | P | P | 1235.0 |
| AQ032 | composite_replacement | pass | - | none | none | - | - | P | P | 1033.8 |
| AQ033 | composite_replacement | pass | - | none | none | - | - | P | P | 976.5 |
| AQ034 | composite_replacement | review | Y | full_llm | none | - | - | P | P | 1743.3 |
| AQ035 | composite_replacement | review | Y | full_llm | none | - | - | P | P | 1673.0 |
| AQ036 | impact_analysis | review | Y | refine | none | - | - | P | P | 1034.4 |
| AQ037 | impact_analysis | review | Y | full_llm | none | - | - | P | P | 1089.5 |
| AQ038 | impact_analysis | pass | - | none | none | - | - | P | P | 924.1 |
| AQ039 | document_search | review | Y | full_llm | none | - | - | P | P | 1122.6 |
| AQ040 | document_search | pass | - | none | none | - | - | P | P | 1056.9 |
