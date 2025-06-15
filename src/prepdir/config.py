import os
import logging
from dynaconf import Dynaconf
from pathlib import Path
import sys
from typing import Optional

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

# Configure logging to ensure debug messages are visible
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(namespace: str, config_path: Optional[str] = None) -> Dynaconf:
    """
    Load configuration for the given namespace, with optional custom config path.

    Args:
        namespace (str): Namespace for the configuration (e.g., 'prepdir').
        config_path (Optional[str]): Path to a custom configuration file.

    Returns:
        Dynaconf: Configuration object with loaded settings.
    """
    # Initialize settings_files based on whether custom config_path is provided
    settings_files = []
    if config_path:
        settings_files = [config_path]
        logger.debug(f"Using custom config path: {config_path}")
    elif os.getenv('TEST_ENV') != 'true':
        # Prioritize local config first
        local_config = '.prepdir/config.yaml'
        home_config = os.path.expanduser('~/.prepdir/config.yaml')
        if Path(local_config).exists():
            settings_files.append(local_config)
            logger.debug(f"Found local config: {local_config}")
        else:
            logger.debug(f"No local config found at: {local_config}")
        if Path(home_config).exists():
            settings_files.append(home_config)
            logger.debug(f"Found home config: {home_config}")
        else:
            logger.debug(f"No home config found at: {home_config}")
        if not settings_files:
            logger.debug("No local or home config found, will attempt bundled config")
        else:
            logger.debug("Loading default config files")
    else:
        logger.debug("Skipping default config files due to TEST_ENV=true")

    # Log skipping bundled config if TEST_ENV is set or custom config_path is provided
    bundled_config_path = None
    if os.getenv('TEST_ENV') == 'true' or config_path or settings_files:
        logger.debug("Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files")
    else:
        try:
            bundled_config = files(namespace) / 'config.yaml'
            logger.debug(f"Attempting to load bundled config from: {bundled_config}")
            with bundled_config.open('r', encoding='utf-8') as f:
                # Create a temporary file for Dynaconf to read the bundled config
                temp_bundled_path = Path(f"/tmp/{namespace}_bundled_config.yaml")
                temp_bundled_path.write_text(f.read(), encoding='utf-8')
                settings_files.append(str(temp_bundled_path))
                bundled_config_path = temp_bundled_path
                logger.debug(f"Loaded bundled config into temporary file: {temp_bundled_path}")
        except Exception as e:
            logger.warning(f"Failed to load bundled config for {namespace}: {str(e)}")

    # Initialize Dynaconf with explicit settings files
    logger.debug(f"Initializing Dynaconf with settings files: {settings_files}")
    config = Dynaconf(
        settings_files=settings_files,
        environments=False,  # Disable environment-based configs
        load_dotenv=False,  # Disable .env file loading
        merge_enabled=False,  # Disable merging to prevent appending
        lowercase_read=True,  # Allow case-insensitive key access
        default_settings_paths=[],  # Prevent default configs
    )

    # Log the final configuration values for debugging
    logger.debug(f"Final config values: REPLACEMENT_UUID={config.get('REPLACEMENT_UUID', 'Not set')}, SCRUB_UUIDS={config.get('SCRUB_UUIDS', 'Not set')}")

    # Clean up temporary bundled config file if it was created
    if bundled_config_path and bundled_config_path.exists():
        try:
            bundled_config_path.unlink()
            logger.debug(f"Removed temporary bundled config: {bundled_config_path}")
        except Exception as e:
            logger.debug(f"Failed to remove temporary bundled config: {str(e)}")

    # Log the config files attempted
    logger.debug(f"Attempted config files for {namespace}: {settings_files}")

    return config