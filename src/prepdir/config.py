import os
import logging
import re
from dynaconf import Dynaconf
from pathlib import Path
import sys
from typing import Optional
import tempfile
from importlib.metadata import version, PackageNotFoundError

logger = logging.getLogger(__name__)

try:
    __version__ = version("prepdir")
except PackageNotFoundError:
    __version__ = "0.0.0"

if sys.version_info < (3, 9):
    from importlib_resources import files, is_resource
else:
    from importlib.resources import files, is_resource

def check_namespace_value(namespace: str):
    """
    Validate the namespace string.

    Args:
        namespace: The namespace string to validate.

    Raises:
        ValueError: If the namespace is empty or contains invalid characters.
    """
    if not namespace or not re.match(r"^[a-zA-Z0-9_-]+$", namespace):
        logger.error(
            f"Invalid namespace '{namespace}': must be non-empty and contain only alphanumeric, underscore, or hyphen chars"
        )
        raise ValueError(
            f"Invalid namespace '{namespace}': must be non-empty and contain only alphanumeric, underscore, or hyphen chars"
        )

def load_config(namespace: str, config_path: Optional[str] = None, verbose: int = 0, quiet: bool = False, stdout=sys.stdout, stderr=sys.stderr) -> Dynaconf:
    """
    Load configuration settings using Dynaconf from various sources.

    Args:
        namespace: Configuration namespace (e.g., 'prepdir').
        config_path: Path to custom config file.
        verbose: Verbosity level (0: no diagnostics, 1: INFO, 2: DEBUG).
        quiet: If True, suppress user-facing output to stdout.
        stdout: Stream for user-facing output.
        stderr: Stream for error messages.

    Returns:
        Dynaconf: Configured Dynaconf instance with loaded settings.

    Raises:
        ValueError: If no configuration files are found or if YAML is invalid.
    """
    if verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif verbose >= 1:
        logger.setLevel(logging.INFO)
    logger.debug(f"Loading config with {namespace=}, {config_path=}, {verbose=}, {quiet=}")

    check_namespace_value(namespace)
    settings_files = []

    if config_path:
        config_path = Path(config_path).resolve()
        if not config_path.exists():
            logger.error(f"Custom config path '{config_path}' does not exist")
            print(f"Error: Custom config path '{config_path}' does not exist", file=stderr)
            raise ValueError(f"Custom config path '{config_path}' does not exist")
        else:
            settings_files.append(str(config_path))
            if not quiet:
                print(f"Using custom config path: {config_path}", file=stdout)
            logger.info(f"Using custom config path: {config_path}")

    elif os.getenv("PREPDIR_SKIP_CONFIG_LOAD") == "true":
        logger.warning("Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true")
        if not quiet and verbose >= 1:
            print("Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true", file=stdout)
    else:
        local_config = Path(f".{namespace}/config.yaml").resolve()
        home_config = Path(os.path.expanduser(f"~/.{namespace}/config.yaml")).resolve()

        if home_config.exists():
            settings_files.append(str(home_config))
            if not quiet:
                print(f"Found home config: {home_config}", file=stdout)
            logger.info(f"Found home config: {home_config}")
        else:
            logger.debug(f"No home config found at: {home_config}")

        if local_config.exists():
            settings_files.append(str(local_config))
            if not quiet:
                print(f"Found local config: {local_config}", file=stdout)
            logger.info(f"Found local config: {local_config}")
        else:
            logger.debug(f"No local config found at: {local_config}")

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
                    if not quiet:
                        print("Will use default config", file=stdout)
                    logger.info("Will use default config")
                except Exception as e:
                    logger.warning(f"Failed to load bundled config for {namespace}: {str(e)}")
                    print(f"Error: Failed to load bundled config for {namespace}: {str(e)}", file=stderr)
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
        config._wrapped
        logger.debug(f"Final config values for UUIDS:\nREPLACEMENT_UUID={config.get('REPLACEMENT_UUID', 'Not set')}\n")
    except Exception as e:
        logger.error(f"Invalid YAML in config file(s): {str(e)}")
        print(f"Error: Invalid YAML in config file(s): {str(e)}", file=stderr)
        raise ValueError(f"Invalid YAML in config file(s): {str(e)}")

    if "bundled_config_path" in locals() and bundled_config_path.exists():
        try:
            bundled_config_path.unlink()
            logger.debug(f"Removed temporary bundled config: {bundled_config_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary bundled config {bundled_config_path} for {namespace}: {str(e)}")

    logger.debug(f"Loaded config for {namespace} from: {settings_files}")
    return config

def init_config(
    namespace: str = "prepdir",
    config_path: Optional[str] = None,
    force: bool = False,
    stdout=sys.stdout,
    stderr=sys.stderr,
):
    """
    Initialize a local config.yaml with the package's default config.

    Args:
        namespace: Configuration namespace (default: 'prepdir').
        config_path: Path to save the config file (default: .prepdir/config.yaml).
        force: If True, overwrite existing config file.
        stdout: Stream for user-facing output.
        stderr: Stream for error messages.

    Raises:
        SystemExit: If the config file already exists and force=False, or if initialization fails.
    """
    check_namespace_value(namespace)
    logger.debug(f"Initializing config with {namespace=}, {config_path=}, {force=}")

    config_path = Path(config_path) if config_path else Path(f".{namespace}/config.yaml")
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists() and not force:
        print(f"Error: '{config_path}' already exists. Use force=True to overwrite.", file=stderr)
        raise SystemExit(1)

    bundled_config = files(namespace) / "config.yaml"
    if not is_resource(namespace, "config.yaml"):
        logger.error(f"No bundled config found for {namespace}, cannot initialize")
        print(f"Error: No bundled config found for {namespace}", file=stderr)
        raise SystemExit(1)

    try:
        with bundled_config.open("r", encoding="utf-8") as src:
            config_content = src.read()
        with config_path.open("w", encoding="utf-8") as dest:
            dest.write(config_content)
        print(f"Created '{config_path}' with default configuration.", file=stdout)
    except Exception as e:
        logger.error(f"Failed to create {config_path}: {str(e)}")
        print(f"Error: Failed to create '{config_path}': {str(e)}", file=stderr)
        raise SystemExit(1)