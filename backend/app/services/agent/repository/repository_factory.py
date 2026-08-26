# agent/repository/repository_factory.py

import os
from typing import Optional

from .interfaces import IRepository
from .json_repository import JsonRepository
from .db_repository import DbRepository


_repository: Optional[IRepository] = None


def get_repository(storage: Optional[str] = None) -> IRepository:
    """Фабрика репозитория с кешированием"""
    global _repository
    
    if _repository is not None:
        return _repository
    
    storage = storage or os.environ.get("AGENT_STORAGE", "auto").strip().lower()
    
    if storage == "json":
        _repository = JsonRepository()
    elif storage == "db":
        try:
            _repository = DbRepository()
            _repository.get_catalog()
        except Exception:
            _repository = JsonRepository()
    else:  # auto
        try:
            _repository = DbRepository()
            _repository.get_catalog()
        except Exception:
            _repository = JsonRepository()
    
    return _repository


def reset_repository() -> None:
    """Сброс кеша репозитория"""
    global _repository
    if _repository:
        _repository.close()
        _repository = None
