import sys
import logging
from pathlib import Path
from dynaconf import Dynaconf

# Conditional import for Python <3.9 compatibility
if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

logger = logging.getLogger(__name__)

def load_config(tool_name: str, config_path: str = None) -> Dynaconf:
    """
    Load configuration for a tool with precedence:
    1. Custom config specified via config_path (--config)
    2. Local .{tool_name}/config.yaml in current directory
    3. Global ~/.{tool_name}/config.yaml in home directory
    4. Bundled src/{tool_name}/config.yaml in package

    Args:
        tool_name: Name of the tool (e.g., 'prepdir', 'vibedir', 'applydir')
        config_path: Path to custom config file (optional)

    Returns:
        Dynaconf instance containing the configuration
    """
    settings_files = []
    
    # 1. Custom config (highest precedence)
    if config_path:
        settings_files.append(config_path)
    else:
        # 2. Local config (e.g., .prepdir/config.yaml)
        settings_files.append(f".{tool_name}/config.yaml")
        
        # 3. Global config (e.g., ~/.prepdir/config.yaml)
        settings_files.append(str(Path.home() / f".{tool_name}" / "config.yaml"))
        
        # 4. Bundled config (e.g., src/prepdir/config.yaml)
        try:
            with resources.files(tool_name).joinpath("config.yaml") as bundled:
                settings_files.append(str(bundled))
        except Exception as e:
            logger.warning(f"Failed to load bundled config for {tool_name}: {e}")

    # Initialize Dynaconf with the settings files
    config = Dynaconf(
        settings_files=settings_files,
        envvar_prefix=tool_name.upper(),
        load_dotenv=True,
        merge_enabled=True,  # Merge configs from multiple files
        root_path=Path.cwd(),
        lowercase_read=True,  # Allow lowercase key access
    )
    
    logger.debug(f"Attempted config files for {tool_name}: {settings_files}")
    return config