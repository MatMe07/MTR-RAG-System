# Eval 40 вопросов в auto-режиме (quality gate)

- Дата: 2026-08-31T20:40:24.202152+00:00
- Режим: auto
- Total: 40
- verdict PASS: 26 / REVIEW: 14
- Эскалаций (REVIEW): 14 (35.0%)
- tools OK: 39/40
- sources OK: 39/40
- кейсов с sufficiency-verdict: 1
- avg duration: 1425.8 ms

## Распределение gap-типов (reason)

- parameter_miss: 11
- intent_mismatch: 7

## По кейсам

| case | cat | verdict | esc | sufficiency | tools | sources | ms |
|---|---|---|---|---|---|---|---|
| AQ001 | replacement | pass | - | - | P | P | 2133.0 |
| AQ002 | replacement | pass | - | - | P | P | 1441.9 |
| AQ003 | replacement | pass | - | - | P | P | 1134.5 |
| AQ004 | replacement | pass | - | - | P | P | 989.9 |
| AQ005 | replacement | pass | - | - | P | P | 977.5 |
| AQ006 | replacement | pass | - | - | P | P | 1730.4 |
| AQ007 | replacement | pass | - | - | P | P | 941.0 |
| AQ008 | inventory | review | Y | - | P | P | 1739.1 |
| AQ009 | inventory | pass | - | Y | F | P | 1744.9 |
| AQ010 | inventory | pass | - | - | P | P | 839.1 |
| AQ011 | inventory | pass | - | - | P | P | 1706.1 |
| AQ012 | inventory | review | Y | - | P | P | 1571.4 |
| AQ013 | inventory | review | Y | - | P | F | 1608.6 |
| AQ014 | inventory | review | Y | - | P | P | 1799.6 |
| AQ015 | inventory | review | Y | - | P | P | 2623.6 |
| AQ016 | toir | review | Y | - | P | P | 2479.5 |
| AQ017 | toir | pass | - | - | P | P | 2185.9 |
| AQ018 | toir | pass | - | - | P | P | 1043.0 |
| AQ019 | toir | review | Y | - | P | P | 1131.1 |
| AQ020 | toir | review | Y | - | P | P | 1729.3 |
| AQ021 | equipment_guidance | pass | - | - | P | P | 590.5 |
| AQ022 | equipment_guidance | pass | - | - | P | P | 915.7 |
| AQ023 | equipment_guidance | pass | - | - | P | P | 1495.5 |
| AQ024 | equipment_guidance | pass | - | - | P | P | 1769.4 |
| AQ025 | equipment_guidance | pass | - | - | P | P | 609.9 |
| AQ026 | object_configuration | review | Y | - | P | P | 1761.1 |
| AQ027 | object_configuration | review | Y | - | P | P | 1797.9 |
| AQ028 | object_configuration | pass | - | - | P | P | 2097.8 |
| AQ029 | object_configuration | review | Y | - | P | P | 2134.5 |
| AQ030 | composite_replacement | pass | - | - | P | P | 1771.6 |
| AQ031 | composite_replacement | pass | - | - | P | P | 1450.9 |
| AQ032 | composite_replacement | pass | - | - | P | P | 1508.5 |
| AQ033 | composite_replacement | pass | - | - | P | P | 1593.7 |
| AQ034 | composite_replacement | pass | - | - | P | P | 1130.0 |
| AQ035 | composite_replacement | pass | - | - | P | P | 1597.2 |
| AQ036 | impact_analysis | review | Y | - | P | P | 610.9 |
| AQ037 | impact_analysis | review | Y | - | P | P | 690.9 |
| AQ038 | impact_analysis | pass | - | - | P | P | 589.7 |
| AQ039 | document_search | review | Y | - | P | P | 714.5 |
| AQ040 | document_search | pass | - | - | P | P | 652.7 |
