import os
import logging
import re
from dynaconf import Dynaconf
from pathlib import Path
import sys
import yaml
from typing import Optional
import tempfile
from importlib.metadata import version, PackageNotFoundError

if sys.version_info < (3, 9):
    from importlib_resources import files, is_resource
else:
    from importlib.resources import files, is_resource

logger = logging.getLogger(__name__)

try:
    __version__ = version("prepdir")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback to hardcoded version

def check_namespace_value(namespace: str):
    """
    Validate the namespace string.

    Args:
        namespace (str): The package namespace to validate.

    Raises:
        ValueError: If namespace is invalid.
    """
    if not namespace or not re.match(r'^[a-zA-Z0-9_-]+$', namespace):
        logger.error(f"Invalid namespace '{namespace}': must be non-empty and contain only alphanumeric, underscore, or hyphen chars")
        raise ValueError(f"Invalid namespace '{namespace}': must be non-empty and contain only alphanumeric, underscore, or hyphen chars")

def load_config(namespace: str, config_path: Optional[str] = None, verbose: bool = False) -> Dynaconf:
    """
    Load configuration settings using Dynaconf from various sources.

    Args:
        namespace (str): The package namespace (e.g., "prepdir", "applydir", "vibedir") for bundled config.
        config_path (Optional[str]): Custom path to a configuration file, overriding defaults if provided.
        verbose (bool): If True, enable detailed logging.

    Returns:
        Dynaconf: Config object with loaded settings.

    Raises:
        ValueError: If no valid config files are found, YAML is invalid, config_path is missing, or namespace is invalid.

    Notes:
        - Priority: custom_config > local_config (./{namespace}/config.yaml) > home_config (~/{namespace}/config.yaml) > bundled_config.
        - In PREPDIR_SKIP_CONFIG_LOAD=true, only custom_config is used.
        - If no bundled config exists for the namespace, returns an empty Dynaconf object.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug(f"Loading config with {namespace=}, {config_path=}, {verbose=}")

    check_namespace_value(namespace)
    settings_files = []

    # Use custom config path if provided
    if config_path:
        config_path = Path(config_path).resolve()
        if not config_path.exists():
            logger.error(f"Custom config path '{config_path}' does not exist")
            raise ValueError(f"Custom config path '{config_path}' does not exist")
        else:
            settings_files.append(str(config_path))
            logger.debug(f"Using custom config path: {config_path}")

    # Skip default config search in test environment
    elif os.getenv("PREPDIR_SKIP_CONFIG_LOAD") == "true":
        logger.warning("Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true")
    else:
        # Check home config first, then local config. The order of the settings files matters (later override earlier)
        local_config = Path(f".{namespace}/config.yaml").resolve()
        home_config = Path(os.path.expanduser(f"~/.{namespace}/config.yaml")).resolve()

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

        # Fallback to bundled config if it exists
        if not settings_files:
            bundled_config = files(namespace) / "config.yaml"
            if is_resource(namespace, "config.yaml"):
                logger.debug(f"Attempting to load bundled config from: {bundled_config}")
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{namespace}_bundled_config.yaml") as f:
                        with bundled_config.open("r", encoding="utf-8") as src:
                            f.write(src.read().encode("utf-8"))
                        temp_bundled_path = Path(f.name)
                    settings_files.append(str(temp_bundled_path))
                    bundled_config_path = temp_bundled_path
                    logger.debug(f"Loaded bundled config into temporary file: {temp_bundled_path}")
                except Exception as e:
                    logger.warning(f"Failed to load bundled config for {namespace}: {str(e)}")
                    raise ValueError(f"Failed to load bundled config for {namespace}: {str(e)}")
            else:
                logger.debug(f"No bundled config found for {namespace}, using defaults")
                config = Dynaconf(settings_files=[], merge_enabled=True, lowercase_read=True)
                return config

    if not settings_files and not os.getenv("PREPDIR_SKIP_CONFIG_LOAD"):
        raise ValueError(
            f"No configuration files found and no bundled config available for {namespace}.\n"
            f"PREPDIR_SKIP_CONFIG_LOAD={os.environ.get('PREPDIR_SKIP_CONFIG_LOAD')}"
        )

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
            f"Final config values for UUIDS:\n"
            f"REPLACEMENT_UUID={config.get('REPLACEMENT_UUID', 'Not set')}\n"
            f"SCRUB_HYPHENATED_UUIDS={config.get('SCRUB_HYPHENATED_UUIDS', 'Not set')}"
        )
    except Exception as e:
        logger.error(f"Invalid YAML in config file(s): {str(e)}")
        raise ValueError(f"Invalid YAML in config file(s): {str(e)}")

    # Clean up temporary bundled config if it exists
    if "bundled_config_path" in locals() and bundled_config_path.exists():
        try:
            bundled_config_path.unlink()
            logger.debug(f"Removed temporary bundled config: {bundled_config_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary bundled config {bundled_config_path} for {namespace}: {str(e)}")

    logger.debug(f"Loaded config for {namespace} from: {settings_files}")
    return config

def init_config(namespace: str = "prepdir", config_path: Optional[str] = None, force: bool = False, stdout=sys.stdout, stderr=sys.stderr):
    """
    Initialize a local config.yaml with the package's default config.

    Args:
        namespace: Name associated with config (e.g., "prepdir", "applydir", "vibedir").
        config_path (str): Path to the configuration file to create (defaults to .{namespace}/config.yaml).
        force (bool): If True, overwrite existing config file.
        stdout (file-like): Stream for success messages (default: sys.stdout).
        stderr (file-like): Stream for error messages (default: sys.stderr).

    Raises:
        SystemExit: If the config file exists and force=False, or if creation fails.
        ValueError: If namespace is invalid.
    """
    check_namespace_value(namespace)
    logger.debug(f"Initializing config with {namespace=}, {config_path=}, {force=}")

    config_path = Path(config_path) if config_path else Path(f".{namespace}/config.yaml")
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists() and not force:
        print(f"Error: '{config_path}' already exists. Use force=True to overwrite.", file=stderr)
        raise SystemExit(1)

    try:
        config = load_config(namespace, verbose=True)
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config.as_dict(), f)
        print(f"Created '{config_path}' with default configuration.", file=stdout)
    except Exception as e:
        print(f"Error: Failed to create '{config_path}': {str(e)}", file=stderr)
        raise SystemExit(1)