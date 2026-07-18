# backend/app/scripts/index_qdrant.py

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.embedding_service import EmbeddingService


def main():
    parser = argparse.ArgumentParser(description="Индексация МТР в Qdrant")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Принудительно удалить и пересоздать коллекцию"
    )
    args = parser.parse_args()

    print("Начинаем индексацию МТР в Qdrant...")

    embedding_service = EmbeddingService()
    count = embedding_service.index_all_mtr(force_recreate=args.force)

    if count > 0:
        print(f"Успешно индексировано {count} МТР в Qdrant")
    else:
        print("Нет МТР для индексации. Проверьте, что данные загружены в mtr_items.")


if __name__ == "__main__":
    main()
