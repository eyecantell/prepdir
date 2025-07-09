import logging
import sys
from typing import Union

def configure_logging(
    logger: logging.Logger,
    verbose: int = 0,
    stdout_stream: Union[object, None] = None,
    stderr_stream: Union[object, None] = None
) -> None:
    """Configure the logger for diagnostic messages.

    Args:
        logger: The logger instance to configure.
        verbose: Verbosity level (0: INFO, 1: INFO with more details, 2: DEBUG).
        stdout_stream: Stream for messages (defaults to sys.stdout).
        stderr_stream: Stream for errors (defaults to sys.stderr).
    """
    # Validate streams
    if stdout_stream is not None and not hasattr(stdout_stream, 'write'):
        raise AttributeError("'stdout_stream' must be a file-like object with a write method")
    if stderr_stream is not None and not hasattr(stderr_stream, 'write'):
        raise AttributeError("'stderr_stream' must be a file-like object with a write method")

    # Clear existing handlers
    logger.handlers.clear()

    # Set logger level based on verbosity
    level_map = {0: logging.INFO, 1: logging.INFO, 2: logging.DEBUG}
    logging_level = level_map.get(verbose, logging.INFO)
    logger.setLevel(logging_level)

    # Single handler for all levels
    handler = logging.StreamHandler(stdout_stream or sys.stdout)
    handler.setLevel(logging_level)  # Match handler level to logger level
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"))
    logger.addHandler(handler)

    # Flush streams
    if stdout_stream and hasattr(stdout_stream, 'flush'):
        stdout_stream.flush()
    if stderr_stream and hasattr(stderr_stream, 'flush'):
        stderr_stream.flush()