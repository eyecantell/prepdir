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

def test_configure_logging_verbose_debug(caplog, streams):
    """Test configure_logging with verbose=2 (DEBUG level)."""
    stdout, stderr = streams
    prepdir_logging.configure_logging(logger, verbose=2, stdout_stream=stdout, stderr_stream=stderr)
    
    assert logger.getEffectiveLevel() == logging.DEBUG
    assert len(logger.handlers) == 1, f"Expected 1 handler, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream is stdout
    
    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        logger.debug("Test debug")
        logger.info("Test info")
        logger.warning("Test warning")
    
    assert len(caplog.records) == 3, f"Expected 3 records, got {len(caplog.records)}: {caplog.records}"
    stdout_content = stdout.getvalue()
    assert "Test debug" in stdout_content
    assert "Test info" in stdout_content
    assert "Test warning" in stdout_content
    assert stderr.getvalue() == ""  # stderr_stream is unused
    
    # Verify formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    for record in caplog.records:
        formatted = formatter.format(record)
        assert formatted in stdout_content
        assert record.name == "prepdir.test"
        assert record.funcName == "test_configure_logging_verbose_debug"

def test_configure_logging_verbose_info(caplog, streams):
    """Test configure_logging with verbose=0 or 1 (INFO level)."""
    stdout, stderr = streams
    for verbose in (0, 1):
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
        caplog.clear()
        
        prepdir_logging.configure_logging(logger, verbose=verbose, stdout_stream=stdout, stderr_stream=stderr)
        
        assert logger.getEffectiveLevel() == logging.INFO
        assert len(logger.handlers) == 1, f"Expected 1 handler, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.handlers[0].stream is stdout
        
        with caplog.at_level(logging.INFO, logger="prepdir.test"):  # Changed from DEBUG to INFO
            logger.debug("Test debug")
            logger.info("Test info")
            logger.warning("Test warning")
        
        assert len(caplog.records) == 2, f"Expected 2 records for verbose={verbose}, got {len(caplog.records)}: {caplog.records}"
        for record in caplog.records:
            assert record.levelno >= logging.INFO, f"Unexpected log level {record.levelname} for verbose={verbose}"
        
        stdout_content = stdout.getvalue()
        assert "Test debug" not in stdout_content
        assert "Test info" in stdout_content
        assert "Test warning" in stdout_content
        assert stderr.getvalue() == ""  # stderr_stream is unused
        
        # Verify formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
        for record in caplog.records:
            formatted = formatter.format(record)
            assert formatted in stdout_content
            assert record.name == "prepdir.test"
            assert record.funcName == "test_configure_logging_verbose_info"

def test_configure_logging_default_stream(caplog):
    """Test configure_logging with default streams (sys.stdout)."""
    prepdir_logging.configure_logging(logger, verbose=2)
    
    assert logger.getEffectiveLevel() == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream is sys.stdout
    
    with caplog.at_level(logging.DEBUG, logger="prepdir.test"):
        logger.debug("Test debug")
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "Test debug"

def test_configure_logging_invalid_streams():
    """Test configure_logging with invalid streams."""
    with pytest.raises(AttributeError, match="'stdout_stream' must be a file-like object with a write method"):
        prepdir_logging.configure_logging(logger, verbose=0, stdout_stream=123)
    
    with pytest.raises(AttributeError, match="'stderr_stream' must be a file-like object with a write method"):
        prepdir_logging.configure_logging(logger, verbose=0, stderr_stream="invalid")

def test_configure_logging_stream_flushing(caplog, streams):
    """Test that streams are flushed if they have a flush method."""
    stdout, stderr = streams
    stdout_flush = Mock(wraps=stdout.flush)
    stderr_flush = Mock(wraps=stderr.flush)
    stdout.flush = stdout_flush
    stderr.flush = stderr_flush
    
    prepdir_logging.configure_logging(logger, verbose=0, stdout_stream=stdout, stderr_stream=stderr)
    
    assert stdout_flush.called
    assert stderr_flush.called
    
    with caplog.at_level(logging.INFO, logger="prepdir.test"):
        logger.info("Test info")
    assert "Test info" in stdout.getvalue()
    assert stderr.getvalue() == ""

if __name__ == "__main__":
    pytest.main(["-v", __file__])