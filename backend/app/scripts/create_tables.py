
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(str(Path(__file__).parent.parent.parent))

from app.database import engine, Base
from app.models import *


def create_tables():
    """Создаёт все таблицы в БД."""
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    
    print("Таблицы созданы.")


def drop_tables():
    """Удаляет все таблицы из БД."""
    print("Удаление таблиц...")
    Base.metadata.drop_all(bind=engine)
    print("Таблицы удалены.")


def recreate_tables():
    """Пересоздаёт все таблицы (drop + create)."""
    drop_tables()
    create_tables()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Управление таблицами БД")
    parser.add_argument(
        "--action",
        choices=["create", "drop", "recreate"],
        default="create",
        help="Действие: create (создать), drop (удалить), recreate (пересоздать)"
    )
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_tables()
    elif args.action == "drop":
        drop_tables()
    elif args.action == "recreate":
        recreate_tables()
