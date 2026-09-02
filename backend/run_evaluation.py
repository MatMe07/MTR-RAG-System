"""Прогон всех 40 вопросов из complex_questions_40.jsonl через агента.

Запуск:  python run_evaluation.py          (из каталога backend)
         python run_evaluation.py --mode llm
"""

import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s | %(name)-32s | %(message)s",
    stream=sys.stdout,
)

for _name in ("mawo_natasha", "mawo_pymorphy3", "mawo_razdel", "mawo_slovnet", "hnswlib"):
    logging.getLogger(_name).setLevel(logging.WARNING)

from app.services.agent.core.config import AgentConfig
from app.services.agent.executor import AgentExecutor


QUESTIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "evaluation", "complex_questions_40.jsonl",
)


def main() -> None:
    mode = "deterministic"
    if len(sys.argv) > 1 and sys.argv[1] == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]

    if not os.path.exists(QUESTIONS_PATH):
        print(f"Файл не найден: {QUESTIONS_PATH}")
        sys.exit(1)

    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    print(f"Загружено вопросов: {len(questions)}")
    print(f"Режим: {mode}\n")

    config = AgentConfig(use_llm=(mode in ("llm", "auto")))
    executor = AgentExecutor(config)

    for i, item in enumerate(questions, 1):
        case_id = item.get("case_id", f"#{i}")
        question = item["question"]
        category = item.get("category", "")

        print("=" * 72)
        print(f"[{i:02d}/40] {case_id}  ({category})")
        print(f"Вопрос: {question}")
        print("-" * 72)

        start = time.time()
        try:
            answer = executor.execute(question, mode=mode)
            elapsed = (time.time() - start) * 1000

            print(f"--- AgentAnswer (время: {elapsed:.0f} мс) ---")
            print(answer)
        except Exception as exc:
            print(f"!!! ОШИБКА: {exc}")

        print("=" * 72)
        print()


if __name__ == "__main__":
    main()
