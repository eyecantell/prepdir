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
    # Clear existing handlers
    logger.handlers.clear()

    # Set logger level based on verbosity
    level_map = {0: logging.INFO, 1: logging.INFO, 2: logging.DEBUG}
    logging_level = level_map.get(verbose, logging.INFO)
    logger.setLevel(logging_level)

    # Single handler for all levels
    handler = logging.StreamHandler(stdout_stream or sys.stdout)
    handler.setLevel(logging.DEBUG)  # Capture all levels
    '''if verbose >= 2:
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"))
    else:
        handler.setFormatter(logging.Formatter("%(message)s"))'''
    
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"))
    logger.addHandler(handler)

    # Flush streams
    if stdout_stream and hasattr(stdout_stream, 'flush'):
        stdout_stream.flush()
    if stderr_stream and hasattr(stderr_stream, 'flush'):
        stderr_stream.flush()