# logger.py
"""
Reusable logging helper.

Usage in your app’s entrypoint (once at startup):
    from app.core.logger import setup_logging
    setup_logging(log_level="DEBUG")  # optional log_path parameter

Then in any module:
    from app.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("message")

"""

from __future__ import annotations

import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Defaults can be overridden via setup_logging()
_DEFAULT_LEVEL = logging.INFO
_DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d "
    "| %(funcName)s | %(message)s"
)
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_FILENAME = "app.log"


def setup_logging(
    *,
    log_level: str | int = _DEFAULT_LEVEL,
    log_path: str | Path | None = None,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5,
    propagate: bool = False,
) -> None:
    """
    Configure root logging with console + rotating file handlers.

    Call this once at application startup.

    Args:
        log_level: Logging level (name or numeric).
        log_path: Directory or file path for the log file.
                  If a directory, `app.log` is created inside.
        max_bytes: Rotate file when size exceeds this many bytes.
        backup_count: How many rotated files to keep.
        propagate: Whether child loggers should propagate to the root handlers.
    """
    level = _resolve_level(log_level)

    # Determine file location
    log_path = _resolve_log_path(log_path)

    # Build handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT))
    console_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT))
    file_handler.setLevel(level)

    # Reset root handlers to avoid duplicates
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.propagate = propagate

    # Optional: silence overly chatty third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.INFO)


def get_logger(name: Optional[str] = None) -> Logger:
    """
    Retrieve a logger instance for the given namespace.
    Falls back to the root logger when `name` is None.
    """
    return logging.getLogger(name)


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    try:
        return logging.getLevelName(level.upper())  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Invalid log level: {level}") from exc


def _resolve_log_path(target: str | Path | None) -> Path:
    if target is None:
        directory = _DEFAULT_LOG_DIR
        directory.mkdir(parents=True, exist_ok=True)
        return directory / _DEFAULT_FILENAME

    target_path = Path(target)
    if target_path.suffix:  # treat as file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return target_path

    target_path.mkdir(parents=True, exist_ok=True)
    return target_path / _DEFAULT_FILENAME
