import pytest
import logging
import os

@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset all prepdir-related loggers before each test."""
    loggers = [
        logging.getLogger("prepdir"),
        logging.getLogger("prepdir.config"),
        logging.getLogger("prepdir.prepdir_processor"),
        logging.getLogger("prepdir.prepdir_output_file"),
        logging.getLogger("prepdir.prepdir_file_entry"),
        logging.getLogger("prepdir.glob_translate"),
        logging.getLogger("prepdir.is_excluded_file"),
        logging.getLogger("prepdir.scrub_uuids"),
        logging.getLogger("dynaconf"),
    ]
    for logger in loggers:
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
    yield

@pytest.fixture(autouse=True, scope="function")
def reset_env():
    """Reset key environment variables before each test."""
    env_keys = ["PREPDIR_SKIP_CONFIG_FILE_LOAD", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD", "HOME"]
    original_env = {key: os.environ.get(key) for key in env_keys}
    yield
    for key in env_keys:
        if original_env[key] is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_env[key]