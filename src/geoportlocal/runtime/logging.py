"""Logging configuration with conservative identifier redaction."""

from __future__ import annotations

import copy
import logging
import re

_MODERN_UDID = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}\b")
_LEGACY_UDID = re.compile(r"\b[0-9A-Fa-f]{40}\b")
_LABELLED_IDENTIFIER = re.compile(
    r"(?i)\b(udid|unique(?:device)?id|serial)\s*([:=])\s*([\"']?)[A-Za-z0-9-]{12,}\3"
)


def redact_identifier(identifier: str | None) -> str:
    """Return a stable short suffix suitable for routine diagnostic logs."""
    if not identifier:
        return "<none>"
    suffix = identifier[-4:] if len(identifier) > 4 else identifier
    return f"***{suffix}"


def redact_text(value: object) -> str:
    """Return display/log text with common iOS identifiers removed."""
    text = str(value)
    text = _MODERN_UDID.sub("<udid:redacted>", text)
    text = _LEGACY_UDID.sub("<udid:redacted>", text)
    text = _LABELLED_IDENTIFIER.sub(r"\1\2<identifier:redacted>", text)
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


def configure_logging(level: int = logging.INFO) -> None:
    """Install one process-wide redacting log handler for the local desktop app."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        RedactingFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.basicConfig(level=level, handlers=[handler], force=True)

    for noisy_logger in ("httpcore", "httpx", "uvicorn.access"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
