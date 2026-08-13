# backend/conftest.py
# По умолчанию тесты идут в офлайн-режиме: не ходим в LLM (OpenRouter/Ollama)
# и не замедляем прогон. LLM-сценарии покрываются отдельными тестами с моками.
# Чтобы прогнать с реальным LLM (например, автопроверку 40 вопросов), запускайте:
#   AGENT_LLM_MODE=auto pytest app/tests/test_40_questions.py
import os

from app.core.config import settings

if os.environ.get("AGENT_LLM_MODE") not in ("auto", "on"):
    settings.AGENT_LLM_MODE = "off"

# test_e2e_search требует тяжёлого embedding-стека (langchain_huggingface/qdrant),
# которого нет в этом окружении. В продакшн-среде тест запускается штатно.
collect_ignore = ["app/tests/test_e2e_search.py"]
