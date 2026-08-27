import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any

import structlog


def silence_noisy_loggers() -> None:
    for name in ("pymorphy2", "pymorphy2.opencorpora_dict", "natasha", "hnswlib"):
        logging.getLogger(name).setLevel(logging.WARNING)


def setup_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    silence_noisy_loggers()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
