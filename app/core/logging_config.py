"""Centralized logging configuration (Phase 4).

A single ``configure_logging`` entry point sets up the root logger with:
- a console handler (human-readable, level-configurable), and
- a rotating file handler writing to ``logs/`` (retains history, caps disk).

Every module obtains its logger via ``get_logger(__name__)`` and never calls
``logging.basicConfig`` itself. This keeps log formatting and routing in one
place and makes the verbosity configurable from YAML (see ConfigManager).

Threading note: the platform is multi-threaded (capture, inference, UI).
Python's ``logging`` handlers are internally synchronized, so loggers are
safe to share across threads.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_FILE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | "
    "%(funcName)s:%(lineno)d | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(
    *,
    level: str = "INFO",
    log_dir: Path | str = "logs",
    file_name: str = "vision_platform.log",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    console: bool = True,
) -> None:
    """Configure root logging. Idempotent: safe to call more than once.

    Args:
        level: Root log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files; created if missing.
        file_name: Log file name within ``log_dir``.
        max_bytes: Rotate the file once it exceeds this size.
        backup_count: Number of rotated files to retain.
        console: Whether to also emit logs to stderr.
    """
    global _configured

    resolved_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(resolved_level)

    # Avoid duplicate handlers if reconfigured (e.g. tests, config reload).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path / file_name,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT, _DATE_FORMAT))
        root.addHandler(console_handler)

    _configured = True
    get_logger(__name__).debug("Logging configured at level %s", level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Use ``get_logger(__name__)`` in each module."""
    return logging.getLogger(name)
