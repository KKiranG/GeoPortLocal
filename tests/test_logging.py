import logging

import geoportlocal.runtime.logging as logging_module
from geoportlocal.runtime.logging import RedactingFormatter, configure_logging, redact_text


def test_redact_text_removes_modern_and_legacy_udids() -> None:
    modern = "00008150-001D342A348A401C"
    legacy = "a" * 40
    message = f"device={modern} fallback={legacy}"

    redacted = redact_text(message)

    assert modern not in redacted
    assert legacy not in redacted
    assert redacted.count("<udid:redacted>") == 2


def test_redacting_formatter_removes_identifier_from_message_and_exception() -> None:
    udid = "00008150-001D342A348A401C"
    formatter = RedactingFormatter("%(levelname)s %(message)s")

    try:
        raise RuntimeError(f"failed device {udid}")
    except RuntimeError:
        record = logging.LogRecord(
            name="geoportlocal",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="session udid=%s",
            args=(udid,),
            exc_info=__import__("sys").exc_info(),
            func=None,
        )

    rendered = formatter.format(record)

    assert udid not in rendered
    assert "<udid:redacted>" in rendered
    assert "<identifier:redacted>" in rendered


def test_configure_logging_persists_bounded_redacted_log(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "GeoPortLocal" / "geoportlocal.log"
    monkeypatch.setattr(logging_module, "default_log_path", lambda: log_path)

    try:
        active_path = configure_logging()
        udid = "00008150-001D342A348A401C"
        logging.getLogger("geoportlocal.test").warning("device serial=%s", udid)

        for handler in logging.getLogger().handlers:
            handler.flush()

        persisted = log_path.read_text(encoding="utf-8")
        assert active_path == log_path
        assert udid not in persisted
        assert "serial=<identifier:redacted>" in persisted
        assert log_path.stat().st_size < logging_module._LOG_MAX_BYTES
    finally:
        logging.shutdown()
        logging.basicConfig(handlers=[logging.NullHandler()], force=True)
