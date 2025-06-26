import os
import logging
from dynaconf import Dynaconf
from pathlib import Path
import sys
import yaml
from typing import Optional
from importlib.metadata import version, PackageNotFoundError

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

logger = logging.getLogger(__name__)

try:
    __version__ = version("prepdir")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback to hardcoded version

def load_config(namespace: str, config_path: Optional[str] = None) -> Dynaconf:
    settings_files = []
    if config_path:
        settings_files = [config_path]
        logger.debug(f"Using custom config path: {config_path}")
    elif os.getenv("TEST_ENV") != "true":
        home_config = Path(os.path.expanduser("~/.prepdir/config.yaml")).resolve()
        local_config = Path(".prepdir/config.yaml").resolve()
        # Prioritize global config first, then local config to ensure local overrides
        if home_config.exists():
            settings_files.append(str(home_config))
            logger.debug(f"Found home config: {home_config}")
        else:
            logger.debug(f"No home config found at: {home_config}")
        if local_config.exists():
            settings_files.append(str(local_config))
            logger.debug(f"Found local config: {local_config}")
        else:
            logger.debug(f"No local config found at: {local_config}")
        if not settings_files:
            logger.debug("No local or home config found, will attempt bundled config")
        else:
            logger.debug(f"Loading default config files in order: {settings_files}")
    else:
        logger.debug("Skipping default config files due to TEST_ENV=true")

    bundled_config_path = None
    if os.getenv("TEST_ENV") == "true" or config_path or settings_files:
        logger.debug(
            "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files"
        )
    else:
        try:
            bundled_config = files(namespace) / "config.yaml"
            logger.debug(f"Attempting to load bundled config from: {bundled_config}")
            with bundled_config.open("r", encoding="utf-8") as f:
                temp_bundled_path = Path(f"/tmp/{namespace}_bundled_config.yaml")
                temp_bundled_path.write_text(f.read(), encoding="utf-8")
                settings_files.append(str(temp_bundled_path))
                bundled_config_path = temp_bundled_path
                logger.debug(f"Loaded bundled config into temporary file: {temp_bundled_path}")
        except Exception as e:
            logger.warning(f"Failed to load bundled config for {namespace}: {str(e)}")

    logger.debug(f"Initializing Dynaconf with settings files: {settings_files}")
    try:
        config = Dynaconf(
            settings_files=settings_files,
            environments=False,
            load_dotenv=False,
            merge_enabled=True,
            merge_lists=False,
            lowercase_read=True,
            default_settings_paths=[],
        )
        # Force loading to catch YAML errors early
        config._wrapped  # Access internal storage to trigger loading
        logger.debug(
            f"Final config values: REPLACEMENT_UUID={config.get('REPLACEMENT_UUID', 'Not set')}, SCRUB_UUIDS={config.get('SCRUB_UUIDS', 'Not set')}"
        )
    except Exception as e:
        logger.error(f"Invalid YAML in config file(s): {str(e)}")
        raise ValueError(f"Invalid YAML in config file(s): {str(e)}")

    if bundled_config_path and bundled_config_path.exists():
        try:
            bundled_config_path.unlink()
            logger.debug(f"Removed temporary bundled config: {bundled_config_path}")
        except Exception as e:
            logger.debug(f"Failed to remove temporary bundled config: {str(e)}")

    logger.debug(f"Attempted config files for {namespace}: {settings_files}")
    return config

def init_config(config_path=".prepdir/config.yaml", force=False, stdout=sys.stdout, stderr=sys.stderr):
    """
    Initialize a local config.yaml with the package's default config.

    Args:
        config_path (str): Path to the configuration file to create.
        force (bool): If True, overwrite existing config file.
        stdout (file-like): Stream for success messages (default: sys.stdout).
        stderr (file-like): Stream for error messages (default: sys.stderr).

    Raises:
        SystemExit: If the config file exists and force=False, or if creation fails.
    """
    config_path = Path(config_path)
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists() and not force:
        print(f"Error: '{config_path}' already exists. Use force=True to overwrite.", file=stderr)
        raise SystemExit(1)

    try:
        config = load_config("prepdir")
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config.as_dict(), f)
        print(f"Created '{config_path}' with default configuration.", file=stdout)
    except Exception as e:
        print(f"Error: Failed to create '{config_path}': {str(e)}", file=stderr)
        raise SystemExit(1)