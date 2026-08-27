# backend/conftest.py
# По умолчанию тесты идут в офлайн-режиме: не ходим в LLM (OpenRouter/Ollama)
# и не замедляем прогон. LLM-сценарии покрываются отдельными тестами с моками.
# Чтобы прогнать с реальным LLM (например, автопроверку 40 вопросов), запускайте:
#   AGENT_LLM_MODE=auto pytest app/tests/test_40_questions.py
import os

# Репозиторий и LLM читают настройки из окружения при первом обращении,
# поэтому значения выставляются до импорта app-модулей.
if os.environ.get("AGENT_LLM_MODE") not in ("auto", "on"):
    os.environ["AGENT_LLM_MODE"] = "off"

# Агентские тесты по умолчанию идут на демо-JSON-каталоге (без PostgreSQL/Qdrant).
# Чтобы прогнать их против реальной БД, задайте явно: AGENT_STORAGE=db.
if os.environ.get("AGENT_STORAGE") not in ("json", "db"):
    os.environ["AGENT_STORAGE"] = "json"