import logging
import sys
from typing import Union  # For Python 3.9 compatibility

class StatusFilter(logging.Filter):
    """Filter to allow INFO messages with is_status=True in non-verbose mode."""
    def filter(self, record: logging.LogRecord) -> bool:
        # Allow all messages in verbose mode (INFO level or lower)
        if record.levelno <= logging.INFO:
            return True
        # In non-verbose mode, allow WARNING and above, plus INFO with is_status=True
        return record.levelno >= logging.WARNING or (
            record.levelno == logging.INFO and getattr(record, "is_status", False)
        )

def configure_logging(
    logger: logging.Logger,
    verbose: bool = False,
    stdout_stream: Union[object, None] = None,
    stderr_stream: Union[object, None] = None
) -> None:
    """Configure the provided logger for verbose or non-verbose mode.

    Args:
        logger: The logger instance to configure (e.g., logging.getLogger(__name__)).
        verbose: If True, show all INFO and above messages; otherwise, show WARNING and above plus INFO with is_status=True.
        stdout_stream: Stream for INFO and status messages (defaults to sys.stdout).
        stderr_stream: Stream for WARNING and ERROR messages (defaults to sys.stderr).
    """
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set logger level
    logger.setLevel(logging.INFO if verbose else logging.WARNING)
    
    # stdout handler for INFO (verbose mode) and status messages
    stdout_handler = logging.StreamHandler(stdout_stream or sys.stdout)
    stdout_handler.addFilter(StatusFilter())
    stdout_handler.setFormatter(logging.Formatter("%(message)s"))  # Clean output
    logger.addHandler(stdout_handler)
    
    # stderr handler for WARNING and above
    stderr_handler = logging.StreamHandler(stderr_stream or sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stderr_handler)