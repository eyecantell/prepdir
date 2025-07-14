import logging
import pytest
from prepdir import prepdir_logging
from io import StringIO
import sys
from unittest.mock import Mock

logger = logging.getLogger("prepdir.test")


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset logger state before and after each test."""
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    yield
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


@pytest.fixture
def streams():
    """Provide StringIO streams for stdout and stderr."""
    stdout = StringIO()
    stderr = StringIO()
    yield stdout, stderr
    stdout.close()
    stderr.close()


def test_configure_logging_level_debug(caplog, streams):
    """Test configure_logging with level=DEBUG."""
    stdout, stderr = streams
    prepdir_logging.configure_logging(logger, level=logging.DEBUG, stdout_stream=stdout, stderr_stream=stderr)

    # Clear caplog to ignore configure_logging's own logs
    caplog.clear()

    assert logger.getEffectiveLevel() == logging.DEBUG
    assert len(logger.handlers) == 2, (
        f"Expected 2 handlers, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
    )
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream is stdout
    assert isinstance(logger.handlers[1], logging.StreamHandler)
    assert logger.handlers[1].stream is stderr

    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        logger.debug("Test debug")
        logger.info("Test info")
        logger.warning("Test warning")
        logger.error("Test error")

    assert len(caplog.records) == 4, f"Expected 4 records, got {len(caplog.records)}: {caplog.records}"
    stdout_content = stdout.getvalue()
    assert "Test debug" in stdout_content
    assert "Test info" in stdout_content
    assert "Test warning" in stdout_content
    assert "Test error" not in stdout_content
    stderr_content = stderr.getvalue()
    assert "Test error" in stderr_content

    # Verify formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    for record in caplog.records:
        formatted = formatter.format(record)
        if record.levelno <= logging.WARNING:
            assert formatted in stdout_content
        else:
            assert formatted in stderr_content
        assert record.name == "prepdir.test"
        assert record.funcName == "test_configure_logging_level_debug"


def test_configure_logging_level_info(caplog, streams):
    """Test configure_logging with level=INFO."""
    stdout, stderr = streams
    prepdir_logging.configure_logging(logger, level=logging.INFO, stdout_stream=stdout, stderr_stream=stderr)

    # Clear caplog to ignore configure_logging's own logs
    caplog.clear()

    assert logger.getEffectiveLevel() == logging.INFO
    assert len(logger.handlers) == 2, (
        f"Expected 2 handlers, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
    )
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream is stdout
    assert isinstance(logger.handlers[1], logging.StreamHandler)
    assert logger.handlers[1].stream is stderr

    with caplog.at_level(logging.INFO, logger="prepdir.test"):
        logger.debug("Test debug")
        logger.info("Test info")
        logger.warning("Test warning")
        logger.error("Test error")

    assert len(caplog.records) == 3, f"Expected 3 records, got {len(caplog.records)}: {caplog.records}"
    for record in caplog.records:
        assert record.levelno >= logging.INFO, f"Unexpected log level {record.levelname}"

    stdout_content = stdout.getvalue()
    assert "Test debug" not in stdout_content
    assert "Test info" in stdout_content
    assert "Test warning" in stdout_content
    assert "Test error" not in stdout_content
    stderr_content = stderr.getvalue()
    assert "Test error" in stderr_content

    # Verify formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    for record in caplog.records:
        formatted = formatter.format(record)
        if record.levelno <= logging.WARNING:
            assert formatted in stdout_content
        else:
            assert formatted in stderr_content
        assert record.name == "prepdir.test"
        assert record.funcName == "test_configure_logging_level_info"


def test_configure_logging_level_none(caplog, streams):
    """Test configure_logging with level=None (preserves existing level)."""
    stdout, stderr = streams
    # Set an initial level
    logger.setLevel(logging.WARNING)
    prepdir_logging.configure_logging(logger, level=None, stdout_stream=stdout, stderr_stream=stderr)

    # Clear caplog to ignore configure_logging's own logs
    caplog.clear()

    assert logger.getEffectiveLevel() == logging.WARNING, (
        f"Expected level WARNING, got {logging.getLevelName(logger.getEffectiveLevel())}"
    )
    assert len(logger.handlers) == 2, (
        f"Expected 2 handlers, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
    )
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream is stdout
    assert isinstance(logger.handlers[1], logging.StreamHandler)
    assert logger.handlers[1].stream is stderr

    with caplog.at_level(logging.WARNING, logger="prepdir.test"):
        logger.debug("Test debug")
        logger.info("Test info")
        logger.warning("Test warning")
        logger.error("Test error")

    assert len(caplog.records) == 2, f"Expected 2 records, got {len(caplog.records)}: {caplog.records}"
    for record in caplog.records:
        assert record.levelno >= logging.WARNING, f"Unexpected log level {record.levelname}"

    stdout_content = stdout.getvalue()
    assert "Test debug" not in stdout_content
    assert "Test info" not in stdout_content
    assert "Test warning" in stdout_content
    assert "Test error" not in stdout_content
    stderr_content = stderr.getvalue()
    assert "Test error" in stderr_content

    # Verify formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    for record in caplog.records:
        formatted = formatter.format(record)
        if record.levelno <= logging.WARNING:
            assert formatted in stdout_content
        else:
            assert formatted in stderr_content
        assert record.name == "prepdir.test"
        assert record.funcName == "test_configure_logging_level_none"


def test_configure_logging_default_stream(caplog):
    """Test configure_logging with default streams (sys.stdout, sys.stderr)."""
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)

    # Clear caplog to ignore configure_logging's own logs
    caplog.clear()

    assert logger.getEffectiveLevel() == logging.DEBUG
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream is sys.stdout
    assert isinstance(logger.handlers[1], logging.StreamHandler)
    assert logger.handlers[1].stream is sys.stderr

    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        logger.debug("Test debug")
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "Test debug"


def test_configure_logging_invalid_streams():
    """Test configure_logging with invalid streams."""
    with pytest.raises(AttributeError, match="'stdout_stream' must be a file-like object with a write method"):
        prepdir_logging.configure_logging(logger, level=logging.DEBUG, stdout_stream=123)

    with pytest.raises(AttributeError, match="'stderr_stream' must be a file-like object with a write method"):
        prepdir_logging.configure_logging(logger, level=logging.DEBUG, stderr_stream="invalid")


def test_configure_logging_stream_flushing(caplog, streams):
    """Test that streams are flushed if they have a flush method."""
    stdout, stderr = streams
    stdout_flush = Mock(wraps=stdout.flush)
    stderr_flush = Mock(wraps=stderr.flush)
    stdout.flush = stdout_flush
    stderr.flush = stderr_flush

    prepdir_logging.configure_logging(logger, level=logging.INFO, stdout_stream=stdout, stderr_stream=stderr)

    # Clear caplog to ignore configure_logging's own logs
    caplog.clear()

    assert stdout_flush.called
    assert stderr_flush.called

    with caplog.at_level(logging.INFO, logger="prepdir.test"):
        logger.info("Test info")
    assert "Test info" in stdout.getvalue()
    assert stderr.getvalue() == ""


if __name__ == "__main__":
    pytest.main(["-v", __file__])
