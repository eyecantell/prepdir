import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
import yaml
from dynaconf import Dynaconf
from importlib import resources

__version__ = "0.0.0"

try:
    from importlib.metadata import version

    __version__ = version(__name__.split(".", 1)[0])
except Exception as e:
    logging.getLogger(__name__).debug(f"Failed to load package version: {e}")

logger = logging.getLogger(__name__)


def check_namespace_value(namespace: str) -> None:
    """Validate the namespace value to ensure it's a valid Python identifier.

    Args:
        namespace (str): The namespace to validate.

    Raises:
        ValueError: If the namespace is empty or not a valid Python identifier.
    """
    if not namespace:
        raise ValueError("Invalid namespace '': must be non-empty")
    if not namespace.isidentifier():
        raise ValueError(f"Invalid namespace '{namespace}': must be a valid Python identifier")


def is_resource(namespace: str, resource_name: str) -> bool:
    """Check if a resource exists in the given namespace.

    Args:
        namespace (str): The namespace to check (e.g., 'prepdir').
        resource_name (str): The name of the resource to check (e.g., 'config.yaml').

    Returns:
        bool: True if the resource exists, False otherwise.
    """
    try:
        return resources.files(namespace).__truediv__(resource_name).is_file()
    except (TypeError, FileNotFoundError):
        return False


def check_config_format(content: str, config_name: str) -> None:
    """Validate that the given content is valid YAML.

    Args:
        content (str): The YAML content to validate.
        config_name (str): The name or path of the config file for error reporting.

    Raises:
        ValueError: If the content is not valid YAML.
    """
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {config_name}: {e}", exc_info=True)
        raise ValueError(f"Invalid YAML in {config_name}: {e}")


def get_bundled_config(namespace: str) -> str:
    """Retrieve and validate the bundled configuration content.

    Args:
        namespace (str): The namespace for the configuration (e.g., 'prepdir').

    Returns:
        str: The content of the bundled config.yaml file.

    Raises:
        ValueError: If the bundled config does not exist or contains invalid YAML.
    """
    logger.debug(f"Checking is_resource({namespace}, config.yaml)")
    if not is_resource(namespace, "config.yaml"):
        logger.error(f"No bundled config found for {namespace}", exc_info=True)
        raise ValueError(f"No bundled config found for {namespace}")
    try:
        with resources.files(namespace).joinpath("config.yaml").open("r", encoding="utf-8") as f:
            config_content = f.read()
        # logger.debug(f"Bundled config content: {config_content}")
        check_config_format(config_content, f"bundled config for '{namespace}'")
        return config_content
    except Exception as e:
        logger.error(f"Failed to load bundled config for {namespace}: {e}", exc_info=True)
        raise ValueError(f"Failed to load bundled config for {namespace}: {e}")


def load_config(namespace: str, config_path: Optional[str] = None, quiet: bool = False) -> Dynaconf:
    """Load configuration with precedence: custom > local > home > bundled.

    Args:
        namespace (str): The namespace for the configuration (e.g., 'prepdir').
        config_path (Optional[str]): Path to a custom configuration file. If provided, only this file is used.
        quiet (bool): If True, suppresses console output. Defaults to False.

    Returns:
        Dynaconf: A Dynaconf instance with the loaded configuration.

    Raises:
        ValueError: If the config path doesn't exist or contains invalid YAML.

    Environment Variables:
        PREPDIR_SKIP_CONFIG_FILE_LOAD: If set to "true", skips loading of home (~/.{namespace}/config.yaml)
            and local (./.{namespace}/config.yaml) configuration files. Defaults to "false".
        PREPDIR_SKIP_BUNDLED_CONFIG_LOAD: If set to "true", skips loading of the bundled configuration
            file (packaged with the application). Defaults to "false".
    """
    check_namespace_value(namespace)
    settings_files = []
    logger.debug(f"Loading config with namespace='{namespace}', config_path='{config_path}', quiet={quiet}")

    skip_config_file_load = os.environ.get("PREPDIR_SKIP_CONFIG_FILE_LOAD", "false").lower() == "true"
    skip_bundled_config = os.environ.get("PREPDIR_SKIP_BUNDLED_CONFIG_LOAD", "false").lower() == "true"

    if config_path:
        config_path_obj = Path(config_path)
        if not config_path_obj.is_file():
            logger.error(f"Custom config path '{config_path_obj.resolve()}' does not exist", exc_info=True)
            raise ValueError(f"Custom config path '{config_path_obj.resolve()}' does not exist")
        with config_path_obj.open("r", encoding="utf-8") as f:
            content = f.read()
        check_config_format(content, f"custom config '{config_path_obj}'")
        settings_files.append(config_path_obj.resolve())
        logger.info(f"Using custom config path: {config_path_obj.resolve()}")
        if not quiet:
            print(f"Using custom config path: {config_path_obj.resolve()}")

    elif not skip_config_file_load:
        home_config_path = Path.home() / f".{namespace}" / "config.yaml"
        local_config_path = Path(f".{namespace}") / "config.yaml"

        if home_config_path.is_file():
            with home_config_path.open("r", encoding="utf-8") as f:
                content = f.read()
            check_config_format(content, f"home config '{home_config_path}'")
            settings_files.append(home_config_path.resolve())
            logger.info(f"Found home config: {home_config_path.resolve()}")
            if not quiet:
                print(f"Found home config: {home_config_path.resolve()}")
        else:
            logger.debug(f"No home config found at: {home_config_path.resolve()}")

        if local_config_path.is_file():
            with local_config_path.open("r", encoding="utf-8") as f:
                content = f.read()
            check_config_format(content, f"local config '{local_config_path}'")
            settings_files.append(local_config_path.resolve())
            logger.info(f"Found local config: {local_config_path.resolve()}")
            if not quiet:
                print(f"Found local config: {local_config_path.resolve()}")
        else:
            logger.debug(f"No local config found at: {local_config_path.resolve()}")

    temp_path = None
    if not settings_files and not skip_bundled_config:
        try:
            config_content = get_bundled_config(namespace)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=f"_{namespace}_bundled_config.yaml", delete=False
            ) as temp:
                temp.write(config_content)
                temp_path = temp.name
            settings_files.append(Path(temp_path).resolve())
            logger.info("Will use default (bundled) config")
            if not quiet:
                print("Will use default (bundled) config")
            logger.debug(f"Loaded bundled config into temporary file: {temp_path}")
        except ValueError as e:
            logger.warning(f"No bundled config available for {namespace}: {e}")

    if not settings_files:
        logger.debug(f"No custom, home, local, or bundled config files found for {namespace}, using defaults")

    try:
        logger.debug(f"Initializing Dynaconf with settings files: {settings_files}")

        settings = Dynaconf(
            settings_files=settings_files,
            merge_enabled=True,
            load_dotenv=False,
            default_settings_paths=[],
        )
        # logger.debug(f"Loaded config dictionary: {settings.to_dict()}")
        logger.debug(f"Loaded config for {namespace} from: {settings_files}")

    finally:
        # If a bundled config was used, remove the temporary file
        if temp_path and Path(temp_path).is_file():
            try:
                settings.to_dict()  # Force the actual config load before the file is removed
                Path(temp_path).unlink()
                logger.debug(f"Removed temporary bundled config: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary bundled config {temp_path}: {e}", exc_info=True)

    return settings


def init_config(namespace: str, config_path: str, force: bool = False, quiet: bool = False) -> None:
    """Initialize a configuration file at the specified path.

    Args:
        namespace (str): The namespace for the configuration (e.g., 'prepdir').
        config_path (str): Path where the configuration file will be created.
        force (bool): If True, overwrite the config file if it exists. Defaults to False.
        quiet (bool): If True, suppresses console output. Defaults to False.

    Raises:
        SystemExit: If the config file exists and force=False, or if the bundled config cannot be loaded,
                    or if the config file cannot be created.
    """
    check_namespace_value(namespace)
    config_path_obj = Path(config_path)
    if config_path_obj.exists() and not force:
        msg = f"Config file '{config_path_obj}' already exists. Use force=True to overwrite"
        logger.error(msg)
        if not quiet:
            print(msg)
        raise SystemExit(msg)

    try:
        config_content = get_bundled_config(namespace)
    except Exception as e:
        logger.error(f"Failed to initialize config: {e}", exc_info=True)
        raise SystemExit(f"Error: Failed to initialize config: {e}")

    try:
        config_path_obj.parent.mkdir(parents=True, exist_ok=True)
        config_path_obj.write_text(config_content, encoding="utf-8")
        logger.info(f"Created '{config_path_obj}' with default configuration.")
        if not quiet:
            print(f"Created '{config_path_obj}' with default configuration.")
    except Exception as e:
        logger.error(f"Failed to create config file '{config_path_obj}': {e}", exc_info=True)
        raise SystemExit(f"Error: Failed to create config file '{config_path_obj}': {e}")
