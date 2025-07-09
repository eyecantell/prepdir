import logging
import pytest
from prepdir import prepdir_logging
from io import StringIO

logger = logging.getLogger("prepdir.test")

@pytest.fixture(autouse=True)
def reset_logger():
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    yield
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)

@pytest.fixture
def streams():
    stdout = StringIO()
    stderr = StringIO()
    yield stdout, stderr
    stdout.close()
    stderr.close()

def test_status_filter_details(caplog, capsys, streams):
    stdout, stderr = streams
    logger.setLevel(logging.DEBUG)
    prepdir_logging.configure_logging(logger, details=True, stdout_stream=stdout, stderr_stream=stderr)
    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        with capsys.disabled():
            logger.debug("Test debug")
    print(f"stdout content: {stdout.getvalue()}")
    print(f"stderr content: {stderr.getvalue()}")
    assert len(caplog.records) == 1, f"Expected 1 record, got {len(caplog.records)}: {caplog.records}"
    record = caplog.records[0]
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    formatted_message = formatter.format(record)
    assert record.message == "Test debug"
    assert record.levelname == "DEBUG"
    assert record.name == "prepdir.test"
    assert record.funcName == "test_status_filter_details"
    assert record.asctime
    assert "Test debug" in stdout.getvalue()
    assert stderr.getvalue() == ""

def test_status_filter_non_verbose(caplog, capsys, streams):
    stdout, stderr = streams
    logger.setLevel(logging.INFO)
    prepdir_logging.configure_logging(logger, details=False, stdout_stream=stdout, stderr_stream=stderr)
    with caplog.at_level(logging.INFO, logger="prepdir.test"):
        with capsys.disabled():
            logger.info("Test info")
            logger.status("Status message")
            logger.warning("Test warning")
    print(f"stdout content: {stdout.getvalue()}")
    print(f"stderr content: {stderr.getvalue()}")
    assert "Test info" in stdout.getvalue()
    assert "Status message" in stdout.getvalue()
    assert "Test warning" in stdout.getvalue()
    assert "WARNING: Test warning" in stderr.getvalue()

def test_status_filter_status_level(caplog, capsys, streams):
    stdout, stderr = streams
    logger.setLevel(logging.STATUS)
    prepdir_logging.configure_logging(logger, details=False, stdout_stream=stdout, stderr_stream=stderr)
    assert logger.getEffectiveLevel() == logging.STATUS, f"Expected logger level STATUS, got {logging.getLevelName(logger.getEffectiveLevel())}"
    assert len(logger.handlers) == 2, f"Expected 2 handlers, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
    assert all(isinstance(h, logging.StreamHandler) for h in logger.handlers), "Expected StreamHandler"
    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        with capsys.disabled():
            logger.debug("Debug status")
            logger.info("Info status")
            logger.status("Status message")
            logger.warning("Warning status")
            logger.info("Regular info")
    print(f"stdout content: {stdout.getvalue()}")
    print(f"stderr content: {stderr.getvalue()}")
    assert "Debug status" not in stdout.getvalue()
    assert "Info status" not in stdout.getvalue()
    assert "Status message" in stdout.getvalue()
    assert "Warning status" in stdout.getvalue()
    assert "Regular info" not in stdout.getvalue()
    assert "WARNING: Warning status" in stderr.getvalue()

def test_status_filter_default_level(caplog, capsys, streams):
    stdout, stderr = streams
    prepdir_logging.configure_logging(logger, details=False, stdout_stream=stdout, stderr_stream=stderr)
    assert logger.getEffectiveLevel() == logging.STATUS, f"Expected logger level STATUS, got {logging.getLevelName(logger.getEffectiveLevel())}"
    assert len(logger.handlers) == 2, f"Expected 2 handlers, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
    assert all(isinstance(h, logging.StreamHandler) for h in logger.handlers), "Expected StreamHandler"
    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        with capsys.disabled():
            logger.debug("Debug status")
            logger.info("Info status")
            logger.status("Status message")
            logger.warning("Warning status")
            logger.info("Regular info")
    print(f"stdout content: {stdout.getvalue()}")
    print(f"stderr content: {stderr.getvalue()}")
    assert "Debug status" not in stdout.getvalue()
    assert "Info status" not in stdout.getvalue()
    assert "Status message" in stdout.getvalue()
    assert "Warning status" in stdout.getvalue()
    assert "Regular info" not in stdout.getvalue()
    assert "WARNING: Warning status" in stderr.getvalue()

def test_status_filter_debug_level(caplog, capsys, streams):
    stdout, stderr = streams
    logger.setLevel(logging.DEBUG)
    prepdir_logging.configure_logging(logger, details=True, stdout_stream=stdout, stderr_stream=stderr)
    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        with capsys.disabled():
            logger.debug("Test debug")
            logger.status("Debug status")
    print(f"stdout content: {stdout.getvalue()}")
    print(f"stderr content: {stderr.getvalue()}")
    assert "Test debug" in stdout.getvalue()
    assert "Debug status" in stdout.getvalue()
    assert stderr.getvalue() == ""