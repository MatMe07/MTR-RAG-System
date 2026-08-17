"""Единая конфигурация логирования.

setup_logging вызывается в main.py (и любом entrypoint) один раз, после чего
все модули получают логгер через get_logger. Уровень берётся из
settings.LOG_LEVEL (env LOG_LEVEL), по умолчанию INFO.
"""

import logging
import sys

from app.core.config import settings

_LOGGER_NAME = "mtr"


def get_logger(name: str | None = None) -> logging.Logger:
    """Возвращает логгер в пространстве имён приложения."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def setup_logging(level: str | int | None = None) -> None:
    """Настраивает корневой консольный логгер (идемпотентно)."""
    root = logging.getLogger()
    root.setLevel(level or getattr(settings, "LOG_LEVEL", "INFO"))

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
        ))
        root.addHandler(handler)

    # Убираем лишний шум от дочерних библиотек.
    for noisy in ("httpx", "urllib3", "openai", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
