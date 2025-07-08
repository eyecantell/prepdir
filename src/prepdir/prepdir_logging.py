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

def configure_logging(
    logger: logging.Logger,
    details: bool = False,
    stdout_stream: Union[object, None] = None,
    stderr_stream: Union[object, None] = None
) -> None:
    """Configure the logger with handlers for status or detailed output.

    Args:
        logger: The logger instance to configure.
        details: If True, use detailed format; if False, use simple format.
        stdout_stream: Stream for messages (defaults to sys.stdout).
        stderr_stream: Stream for WARNING+ messages (defaults to sys.stderr).
    """
    logger.handlers.clear()
    #print(f"Logger level before configuring: {logging.getLevelName(logger.getEffectiveLevel())}")
    #print(f"Handlers before configuring: {[h.__class__.__name__ for h in logger.handlers]}")
    
    # Set default level to STATUS if NOTSET
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.STATUS)
    #print(f"Logger level after setting: {logging.getLevelName(logger.getEffectiveLevel())}")
    
    detailed_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s")
    info_formatter = logging.Formatter("%(message)s")
    warning_formatter = logging.Formatter("%(levelname)s: %(message)s")
    
    stdout_handler = logging.StreamHandler(stdout_stream or sys.stdout)
    stdout_handler.setLevel(logger.getEffectiveLevel())
    stdout_handler.setFormatter(detailed_formatter if details else info_formatter)
    logger.addHandler(stdout_handler)
    #logger.debug(f"STDOUT handler will use: {'detailed_formatter' if details else 'info_formatter'}")
    
    stderr_handler = logging.StreamHandler(stderr_stream or sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(detailed_formatter if details else warning_formatter)
    logger.addHandler(stderr_handler)
    #logger.debug(f"STDERR handler will use: {'detailed_formatter' if details else 'warning_formatter'}")
    
    if stdout_stream and hasattr(stdout_stream, 'flush'):
        stdout_stream.flush()
    if stderr_stream and hasattr(stderr_stream, 'flush'):
        stderr_stream.flush()
    
    #print(f"Handlers after configuring: {[h.__class__.__name__ for h in logger.handlers]}")