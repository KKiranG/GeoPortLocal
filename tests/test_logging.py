import logging

from geoportlocal.runtime.logging import RedactingFormatter, redact_text


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
