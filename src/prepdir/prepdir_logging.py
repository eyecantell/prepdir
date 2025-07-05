import logging
import sys
from typing import Union  # For Python 3.9 compatibility

class StatusFilter(logging.Filter):
    """Filter to control logging output based on status messages and logger level."""
    def __init__(self, logger: logging.Logger, always_show_status: bool = False):
        """Initialize the filter with a logger instance and status message control.

        Args:
            logger: The logger instance to filter for.
            always_show_status: If True, allow messages with is_status=True regardless of level.
        """
        super().__init__()
        self.logger = logger
        self.always_show_status = always_show_status

    def filter(self, record: logging.LogRecord) -> bool:
        # Always show messages with is_status=True if always_show_status=True
        if self.always_show_status and hasattr(record, "is_status") and record.is_status:
            print(f"Allowing status message: {record.msg} (level={record.levelname})")
            return True
        # Otherwise, allow messages at or above the logger's effective level
        allow = record.levelno >= self.logger.getEffectiveLevel()
        print(f"Filtering message: {record.msg} (level={record.levelname}, logger_level={logging.getLevelName(self.logger.getEffectiveLevel())}, allow={allow})")
        return allow

def configure_logging(
    logger: logging.Logger,
    always_show_status: bool = False,
    details: bool = False,
    stdout_stream: Union[object, None] = None,
    stderr_stream: Union[object, None] = None
) -> None:
    """Configure the provided logger with handlers and formatters for status or detailed output.

    Args:
        logger: The logger instance to configure (e.g., logging.getLogger(__name__)).
        always_show_status: If True, show all messages with is_status=True on stdout,
                           regardless of logger level. If False, respect the logger's level.
        details: If True, use detailed formatter with timestamp, name, level, and function name.
        stdout_stream: Stream for INFO and status messages (defaults to sys.stdout).
        stderr_stream: Stream for WARNING and ERROR messages (defaults to sys.stderr).
    """
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    print(f"Logger level before configuring: {logging.getLevelName(logger.getEffectiveLevel())}")
    
    # Define formatters
    detailed_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    info_formatter = logging.Formatter("%(message)s")  # Clean output for INFO
    warning_formatter = logging.Formatter("%(levelname)s: %(message)s")  # Prefixed for WARNING/ERROR
    
    # stdout handler for status messages and levels allowed by logger
    stdout_handler = logging.StreamHandler(stdout_stream or sys.stdout)
    stdout_handler.setLevel(logging.DEBUG if always_show_status else logger.getEffectiveLevel())
    stdout_handler.addFilter(StatusFilter(logger=logger, always_show_status=always_show_status))
    stdout_handler.setFormatter(detailed_formatter if details else info_formatter)
    logger.addHandler(stdout_handler)
    
    # stderr handler for WARNING and above
    stderr_handler = logging.StreamHandler(stderr_stream or sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(detailed_formatter if details else warning_formatter)
    logger.addHandler(stderr_handler)