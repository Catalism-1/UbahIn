from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .path_utils import get_log_dir


def setup_logging(log_dir: Path | None = None) -> logging.Logger:
    directory = log_dir or get_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ubahin")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        handler = RotatingFileHandler(
            directory / "ubahin.log",
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    return logger


def get_logger(name: str = "ubahin") -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
