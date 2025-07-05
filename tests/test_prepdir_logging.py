import logging
import pytest
from prepdir.prepdir_logging import configure_logging, StatusFilter

logger = logging.getLogger("prepdir.test")  # Use explicit logger name to match assertions

@pytest.fixture(autouse=True)
def reset_logger():
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    yield
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)

def test_status_filter_details(caplog, capsys):
    logger.setLevel(logging.DEBUG)
    configure_logging(logger, always_show_status=True, details=True)
    caplog.set_level(logging.DEBUG, logger="prepdir.test")
    logger.debug("Test debug")
    captured = capsys.readouterr()
    print(f"caplog.text is {caplog.text}")
    print(f"captured.out is {captured.out}")
    # Check formatted message using record attributes
    assert len(caplog.records) == 1, f"Expected 1 record, got {len(caplog.records)}: {caplog.records}"
    record = caplog.records[0]
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    formatted_message = formatter.format(record)
    assert record.message == "Test debug"
    assert record.levelname == "DEBUG"
    assert record.name == "prepdir.test"
    assert record.funcName == "test_status_filter_details"
    assert record.asctime  # Verify timestamp exists
    assert "Test debug" in captured.out

def test_status_filter_non_verbose(caplog, capsys):
    logger.setLevel(logging.WARNING)
    configure_logging(logger, always_show_status=False, details=False)
    caplog.set_level(logging.INFO, logger="prepdir.test")
    logger.info("Test info")
    logger.info("Status message", extra={"is_status": True})
    logger.warning("Test warning")
    captured = capsys.readouterr()
    print(f"caplog.text is {caplog.text}")
    print(f"captured.out is {captured.out}")
    print(f"captured.err is {captured.err}")
    assert "Test info" not in captured.out
    assert "Status message" not in captured.out
    assert "Test warning" in captured.out  # WARNING goes to stdout with WARNING level
    assert "WARNING: Test warning" in captured.err  # Also goes to stderr

def test_status_filter_always_show_status(caplog, capsys):
    logger.setLevel(logging.ERROR)
    assert logger.getEffectiveLevel() == logging.ERROR, f"Expected logger level ERROR, got {logging.getLevelName(logger.getEffectiveLevel())}"
    configure_logging(logger, always_show_status=True, details=False)
    assert logger.getEffectiveLevel() == logging.ERROR, f"Expected logger level ERROR after configure, got {logging.getLevelName(logger.getEffectiveLevel())}"
    caplog.set_level(logging.DEBUG, logger="prepdir.test")
    logger.debug("Debug status", extra={"is_status": True})
    logger.info("Info status", extra={"is_status": True})
    logger.warning("Warning status", extra={"is_status": True})
    logger.info("Regular info")
    captured = capsys.readouterr()
    print(f"caplog.text is {caplog.text}")
    print(f"captured.out is {captured.out}")
    print(f"captured.err is {captured.err}")
    # Debug filter decisions
    for record in caplog.records:
        if record.msg == "Regular info":
            print(f"Filter decision for Regular info: {record.__dict__}")
    assert "Debug status" in captured.out
    assert "Info status" in captured.out
    assert "Warning status" in captured.out
    assert "Regular info" not in captured.out
    assert "WARNING: Warning status" in captured.err

def test_status_filter_debug_level(caplog, capsys):
    logger.setLevel(logging.DEBUG)
    configure_logging(logger, always_show_status=False, details=True)
    caplog.set_level(logging.DEBUG, logger="prepdir.test")
    logger.debug("Test debug")
    logger.debug("Debug status", extra={"is_status": True})
    captured = capsys.readouterr()
    print(f"caplog.text is {caplog.text}")
    print(f"captured.out is {captured.out}")
    assert "Test debug" in captured.out
    assert "Debug status" in captured.out