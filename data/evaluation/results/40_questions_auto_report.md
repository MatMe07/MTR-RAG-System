# Eval 40 вопросов в auto-режиме (quality gate)

- Дата: 2026-09-09T18:07:57.697888+00:00
- Режим: auto
- Total: 40
- verdict PASS: 39 / REVIEW: 1
- Эскалаций (REVIEW): 1 (2.5%)
- Эскалации по типу: refine=1, full_llm=0, none=39
- C2 (full LLM): 0 кейсов (0.0%), из них пропущено без LLM: 0
- LLM-токены: total=0, avg=None (кейсов: 0)
- tools OK: 40/40
- sources OK: 40/40
- кейсов с sufficiency-verdict: 1
- avg duration: 227.2 ms

## Распределение gap-типов (reason)

- intent_mismatch: 1
- scope_mismatch: 1

## По кейсам

| case | cat | verdict | esc | escal | applied | tokens | sufficiency | tools | sources | ms |
|---|---|---|---|---|---|---|---|---|---|---|
| AQ001 | replacement | pass | - | none | none | - | - | P | P | 1493.3 |
| AQ002 | replacement | pass | - | none | none | - | - | P | P | 174.1 |
| AQ003 | replacement | pass | - | none | none | - | - | P | P | 189.2 |
| AQ004 | replacement | pass | - | none | none | - | - | P | P | 171.1 |
| AQ005 | replacement | pass | - | none | none | - | - | P | P | 162.6 |
| AQ006 | replacement | pass | - | none | none | - | - | P | P | 203.2 |
| AQ007 | replacement | pass | - | none | none | - | - | P | P | 166.9 |
| AQ008 | inventory | pass | - | none | none | - | - | P | P | 267.2 |
| AQ009 | inventory | pass | - | none | none | - | Y | P | P | 240.8 |
| AQ010 | inventory | pass | - | none | none | - | - | P | P | 119.3 |
| AQ011 | inventory | pass | - | none | none | - | - | P | P | 284.2 |
| AQ012 | inventory | pass | - | none | none | - | - | P | P | 257.6 |
| AQ013 | inventory | pass | - | none | none | - | - | P | P | 245.9 |
| AQ014 | inventory | pass | - | none | none | - | - | P | P | 224.6 |
| AQ015 | inventory | pass | - | none | none | - | - | P | P | 250.2 |
| AQ016 | toir | pass | - | none | none | - | - | P | P | 214.7 |
| AQ017 | toir | pass | - | none | none | - | - | P | P | 277.3 |
| AQ018 | toir | pass | - | none | none | - | - | P | P | 178.3 |
| AQ019 | toir | pass | - | none | none | - | - | P | P | 136.1 |
| AQ020 | toir | pass | - | none | none | - | - | P | P | 311.5 |
| AQ021 | equipment_guidance | pass | - | none | none | - | - | P | P | 121.5 |
| AQ022 | equipment_guidance | pass | - | none | none | - | - | P | P | 112.5 |
| AQ023 | equipment_guidance | pass | - | none | none | - | - | P | P | 155.1 |
| AQ024 | equipment_guidance | review | Y | refine | none | - | - | P | P | 121.1 |
| AQ025 | equipment_guidance | pass | - | none | none | - | - | P | P | 114.3 |
| AQ026 | object_configuration | pass | - | none | none | - | - | P | P | 168.2 |
| AQ027 | object_configuration | pass | - | none | none | - | - | P | P | 196.3 |
| AQ028 | object_configuration | pass | - | none | none | - | - | P | P | 247.1 |
| AQ029 | object_configuration | pass | - | none | none | - | - | P | P | 196.7 |
| AQ030 | composite_replacement | pass | - | none | none | - | - | P | P | 375.0 |
| AQ031 | composite_replacement | pass | - | none | none | - | - | P | P | 202.3 |
| AQ032 | composite_replacement | pass | - | none | none | - | - | P | P | 206.3 |
| AQ033 | composite_replacement | pass | - | none | none | - | - | P | P | 308.5 |
| AQ034 | composite_replacement | pass | - | none | none | - | - | P | P | 160.9 |
| AQ035 | composite_replacement | pass | - | none | none | - | - | P | P | 243.7 |
| AQ036 | impact_analysis | pass | - | none | none | - | - | P | P | 111.7 |
| AQ037 | impact_analysis | pass | - | none | none | - | - | P | P | 128.5 |
| AQ038 | impact_analysis | pass | - | none | none | - | - | P | P | 96.0 |
| AQ039 | document_search | pass | - | none | none | - | - | P | P | 132.1 |
| AQ040 | document_search | pass | - | none | none | - | - | P | P | 123.9 |
