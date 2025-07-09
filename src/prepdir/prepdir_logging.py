import logging
import sys
from typing import Union

# Define STATUS level
logging.STATUS = 25
logging.addLevelName(logging.STATUS, "STATUS")

def status(self, message, *args, **kwargs):
    """Custom logging method for STATUS level."""
    if self.isEnabledFor(logging.STATUS):
        self._log(logging.STATUS, message, args, **kwargs)
logging.Logger.status = status

class StatusFormatter(logging.Formatter):
    """Custom formatter to output only the message for STATUS level, detailed for others."""
    def __init__(self, fmt: str = None, *args, **kwargs):
        super().__init__(fmt, *args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.STATUS:
            return record.getMessage()  # Clean output for STATUS
        return super().format(record)  # Detailed or simple format for other levels

def configure_logging(
    logger: logging.Logger,
    details: bool = False,
    stdout_stream: Union[object, None] = None,
    stderr_stream: Union[object, None] = None,
    clear_root_handlers: bool = False
) -> None:
    """Configure the logger with handlers for status or detailed output.

    Args:
        logger: The logger instance to configure.
        details: If True, use detailed format for non-STATUS levels; if False, use simple format.
        stdout_stream: Stream for messages (defaults to sys.stdout).
        stderr_stream: Stream for WARNING+ messages (defaults to sys.stderr).
        clear_root_handlers: If True, clear root logger handlers (use with caution in programmatic use).
    """
    # Clear existing handlers on the logger
    logger.handlers.clear()

    # Optionally clear root logger handlers (for CLI use)
    if clear_root_handlers:
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.CRITICAL + 1)  # Disable root logger

    # Set default level to STATUS if NOTSET
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.STATUS)

    # Formatters
    detailed_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    simple_formatter = logging.Formatter("%(message)s")

    # Configure stdout handler for DEBUG, INFO, STATUS
    stdout_handler = logging.StreamHandler(stdout_stream or sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(StatusFormatter(detailed_formatter.fmt if details else simple_formatter.fmt))
    stdout_handler.addFilter(lambda record: record.levelno <= logging.STATUS)
    logger.addHandler(stdout_handler)

    # Configure stderr handler for WARNING and above
    stderr_handler = logging.StreamHandler(stderr_stream or sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(StatusFormatter(detailed_formatter.fmt if details else "%(levelname)s: %(message)s"))
    logger.addHandler(stderr_handler)

    if stdout_stream and hasattr(stdout_stream, 'flush'):
        stdout_stream.flush()
    if stderr_stream and hasattr(stderr_stream, 'flush'):
        stderr_stream.flush()