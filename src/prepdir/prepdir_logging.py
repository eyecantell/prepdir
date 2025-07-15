import logging
import sys
from typing import Union, Optional


def configure_logging(
    logger: logging.Logger,
    level: Optional[int] = None,
    stdout_stream: Union[object, None] = None,
    stderr_stream: Union[object, None] = None,
) -> None:
    """Configure the logger for diagnostic messages.

    Args:
        logger: The logger instance to configure.
        level: Logging level (e.g., logging.DEBUG, logging.INFO, logging.WARNING). If None, preserves the logger's current level.
        stdout_stream: Stream for messages (defaults to sys.stdout).
        stderr_stream: Stream for errors (defaults to sys.stderr).
    """
    # Validate streams
    if stdout_stream is not None and not hasattr(stdout_stream, "write"):
        raise AttributeError("'stdout_stream' must be a file-like object with a write method")
    if stderr_stream is not None and not hasattr(stderr_stream, "write"):
        raise AttributeError("'stderr_stream' must be a file-like object with a write method")

    # Set logger level if provided
    if level is not None:
        logger.setLevel(level)
        logger.debug(f"Set logger level to {logging.getLevelName(level)}")
    else:
        logger.debug(f"Preserving logger level: {logging.getLevelName(logger.level)}")

    # Clear existing handlers
    logger.handlers.clear()
    logger.debug(f"Cleared existing handlers for {logger.name}")

    # Handler for DEBUG, INFO to stdout
    stdout_handler = logging.StreamHandler(stdout_stream or sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
    stdout_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    )
    logger.addHandler(stdout_handler)
    logger.debug(f"Added stdout StreamHandler with level {logging.getLevelName(logging.DEBUG)}")

    # Handler for WARNING and above to stderr
    stderr_handler = logging.StreamHandler(stderr_stream or sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    )
    logger.addHandler(stderr_handler)
    logger.debug(f"Added stderr StreamHandler with level {logging.getLevelName(logging.WARNING)}")

    # Flush streams
    if stdout_stream and hasattr(stdout_stream, "flush"):
        stdout_stream.flush()
    if stderr_stream and hasattr(stderr_stream, "flush"):
        stderr_stream.flush()
