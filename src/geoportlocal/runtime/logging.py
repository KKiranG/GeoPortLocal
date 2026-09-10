"""Logging configuration with conservative identifier redaction."""

from __future__ import annotations

import copy
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MODERN_UDID = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}\b")
_LEGACY_UDID = re.compile(r"\b[0-9A-Fa-f]{40}\b")
_LABELLED_IDENTIFIER = re.compile(
    r"(?i)\b(udid|unique(?:device)?id|serial)\s*([:=])\s*([\"']?)[A-Za-z0-9-]{12,}\3"
)
_LOG_MAX_BYTES = 1_000_000
_LOG_BACKUPS = 2


def redact_identifier(identifier: str | None) -> str:
    """Return a stable short suffix suitable for routine diagnostic logs."""
    if not identifier:
        return "<none>"
    suffix = identifier[-4:] if len(identifier) > 4 else identifier
    return f"***{suffix}"


def redact_text(value: object) -> str:
    """Return display/log text with common iOS identifiers removed."""
    text = str(value)
    text = _LABELLED_IDENTIFIER.sub(r"\1\2<identifier:redacted>", text)
    text = _MODERN_UDID.sub("<udid:redacted>", text)
    text = _LEGACY_UDID.sub("<udid:redacted>", text)
    return text


class RedactingFormatter(logging.Formatter):
    """Format records without leaking identifiers from messages or tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        safe_record = copy.copy(record)
        safe_record.msg = redact_text(record.getMessage())
        safe_record.args = ()
        safe_record.exc_text = None
        return redact_text(super().format(safe_record))

    def formatException(  # type: ignore[override]
        self,
        exc_info: tuple[type[BaseException], BaseException, object],
    ) -> str:
        return redact_text(super().formatException(exc_info))


def default_log_path() -> Path:
    """Return GeoPortLocal's per-user log path without touching legacy GeoPort state."""
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Logs" / "GeoPortLocal"
    elif os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        root = (
            Path(local_app_data) / "GeoPortLocal" / "Logs"
            if local_app_data
            else Path.home() / "AppData" / "Local" / "GeoPortLocal" / "Logs"
        )
    else:
        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        root = (
            Path(xdg_state_home) / "geoportlocal"
            if xdg_state_home
            else Path.home() / ".local" / "state" / "geoportlocal"
        )
    return root / "geoportlocal.log"


def configure_logging(level: int = logging.INFO) -> Path | None:
    """Install redacted stream/file handlers and return the active file path if available."""
    formatter = RedactingFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handlers: list[logging.Handler] = []

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)

    log_path = default_log_path()
    active_log_path: Path | None = None
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUPS,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
        active_log_path = log_path
    except OSError:
        # Logging must never prevent the local control application from starting.
        pass

    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(level=level, handlers=handlers, force=True)

    for noisy_logger in ("httpcore", "httpx", "uvicorn.access"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    return active_log_path
