import json
import logging
import os
import pytest
import yaml
from io import StringIO
from unittest.mock import patch, MagicMock
from pathlib import Path
from dynaconf import Dynaconf
from prepdir.config import (
    load_config,
    check_namespace_value,
    init_config,
    check_config_format,
    get_bundled_config,
    is_resource,
)
from prepdir import prepdir_logging

# Set up logger
logger = logging.getLogger("prepdir.config")


# Custom handler to capture log records in a list
class LoggingListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def flush(self):
        pass


@pytest.fixture
def clean_cwd(tmp_path):
    """Change working directory to a clean temporary path to avoid loading real configs."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


@pytest.fixture
def sample_config_content():
    """Provide sample configuration content."""
    return {
        "EXCLUDE": {
            "DIRECTORIES": [".gitdir", "__pycache__dir"],
            "FILES": ["*.myexttodisclude", "*.mylog"],
        },
        "REPLACEMENT_UUID": "12345678-1234-1234-4321-4321432143214321",
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": False,
    }


@pytest.fixture
def expected_bundled_config_content():
    """Sample of expected values in src/prepdir/config.yaml"""
    return {
        "DEFAULT_EXTENSIONS": [],
        "EXCLUDE": {
            "DIRECTORIES": [".git", "__pycache__"],
            "FILES": ["*.pyc", "*.log"],
        },
        "DEFAULT_OUTPUT_FILE": "prepped_dir.txt",
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000",
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": True,
    }


@pytest.fixture
def clean_logger():
    """Clean logger setup and teardown with a LoggingListHandler to capture log records."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)

    # Add LoggingListHandler to capture log records
    list_handler = LoggingListHandler()
    list_handler.setLevel(logging.DEBUG)
    logger.addHandler(list_handler)

    yield logger

    # Clean up
    logger.removeHandler(list_handler)
    list_handler.close()
    logger.handlers.clear()


def assert_config_content_equal(config: Dynaconf, expected_config_content: dict):
    """Common set of assertions to check Dynaconf config content against an expected set of values"""
    assert isinstance(config, Dynaconf)
    print(f"config is:\n{json.dumps(config.to_dict(), indent=4)}\n--")
    assert isinstance(expected_config_content, dict)
    print(f"expected_config_content is:\n{json.dumps(expected_config_content, indent=4)}\n--")
    assert config.get("replacement_uuid") == expected_config_content["REPLACEMENT_UUID"]
    assert config.get("scrub_hyphenated_uuids") == expected_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("scrub_hyphenless_uuids") == expected_config_content["SCRUB_HYPHENLESS_UUIDS"]

    assert all(item in config.get("exclude.directories") for item in expected_config_content["EXCLUDE"]["DIRECTORIES"])
    assert all(item in expected_config_content["EXCLUDE"]["DIRECTORIES"] for item in config.get("exclude.directories"))

    assert all(item in config.get("exclude.files") for item in expected_config_content["EXCLUDE"]["FILES"])
    assert all(item in expected_config_content["EXCLUDE"]["FILES"] for item in config.get("exclude.files"))


def test_check_namespace_value():
    """Test namespace validation."""
    check_namespace_value("prepdir")
    check_namespace_value("applydir")
    check_namespace_value("vibedir_123")

    with pytest.raises(ValueError, match="Invalid namespace '': must be non-empty"):
        check_namespace_value("")

    with pytest.raises(ValueError, match="Invalid namespace 'invalid@name': must be a valid Python identifier"):
        check_namespace_value("invalid@name")


def test_check_config_format():
    """Test check_config_format for valid and invalid YAML."""
    check_config_format("key: value", "test config")

    with pytest.raises(ValueError, match="Invalid YAML in test config"):
        check_config_format("invalid: yaml: : :", "test config")


def test_is_resource_bundled_config():
    """Make sure the bundled config (src/prepdir/config.yaml) exists"""
    assert is_resource("prepdir", "config.yaml")


def test_is_resource_false():
    """Test resource check for a non-existent file"""
    assert not is_resource("prepdir", "nonexistent.yaml")


def test_is_resource_exception(clean_logger):
    """Test is_resource exception handling (line 47)."""
    with patch("importlib.resources.files", side_effect=TypeError("Invalid resource")):
        assert not is_resource("prepdir", "config.yaml")


def test_expected_bundled_config_values(expected_bundled_config_content):
    # Load the bundled config and make sure its valid
    bundled_config_content = get_bundled_config("prepdir")
    check_config_format(bundled_config_content, "bundled config")

    bundled_yaml = yaml.safe_load(bundled_config_content)
    print(f"bundled yaml is {bundled_yaml}", "bundled")
    assert bundled_yaml is not None

    # Check expected bundled config values
    assert bundled_yaml["REPLACEMENT_UUID"] == expected_bundled_config_content["REPLACEMENT_UUID"]
    assert bundled_yaml["SCRUB_HYPHENATED_UUIDS"] == expected_bundled_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert bundled_yaml["SCRUB_HYPHENLESS_UUIDS"] == expected_bundled_config_content["SCRUB_HYPHENLESS_UUIDS"]
    assert bundled_yaml["DEFAULT_EXTENSIONS"] == expected_bundled_config_content["DEFAULT_EXTENSIONS"]
    assert all(
        item in bundled_yaml["EXCLUDE"]["DIRECTORIES"]
        for item in expected_bundled_config_content["EXCLUDE"]["DIRECTORIES"]
    )
    assert all(item in bundled_yaml["EXCLUDE"]["FILES"] for item in expected_bundled_config_content["EXCLUDE"]["FILES"])


def test_nonexistent_bundled_config():
    """Try to load a bundled config for a namespace that does not exist"""
    # Load the bundled config and make sure its valid
    namespace = "namespace_that_does_not_exist"
    with pytest.raises(ModuleNotFoundError, match=f"No module named '{namespace}'"):
        get_bundled_config(namespace)


def test_load_config_from_specific_path(sample_config_content, clean_cwd, clean_logger):
    """Test loading local configuration from mydir/config.yaml."""
    config_path = clean_cwd / "mydir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))

    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true"}):
        config = load_config("prepdir", str(config_path), quiet=True)

    assert_config_content_equal(config, sample_config_content)


def test_load_config_local(sample_config_content, clean_cwd, clean_logger):
    """Test loading local configuration from .prepdir/config.yaml."""

    # Create local config file
    config_path = clean_cwd / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))

    # Create empty home dir (so no config gets loaded from there)
    home_dir = clean_cwd / "home"
    home_dir.mkdir()

    with patch.dict(
        os.environ,
        {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"},
    ):
        config = load_config("prepdir")

    assert_config_content_equal(config, sample_config_content)


def test_load_config_home(sample_config_content, clean_cwd, clean_logger):
    """Test loading configuration from ~/.prepdir/config.yaml."""
    home_dir = clean_cwd / "home"
    home_dir.mkdir()
    config_path = home_dir / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))

    with patch.dict(
        os.environ,
        {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"},
    ):
        config = load_config("prepdir", quiet=True)

    assert_config_content_equal(config, sample_config_content)


def test_load_config_bundled(clean_logger):
    """Test loading bundled configuration using get_bundled_config."""
    # Load the bundled config
    bundled_yaml = yaml.safe_load(get_bundled_config("prepdir"))

    # Skip any file loads and load the bubdled config
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
        config = load_config("prepdir", quiet=True)

    assert_config_content_equal(config, bundled_yaml)


def test_load_config_with_skip_flags(clean_cwd, clean_logger):
    """Test no config files with skip flags."""
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"}):
        config = load_config("prepdir", quiet=True)

    expected_blank_config = {"LOAD_DOTENV": False, "DEFAULT_SETTINGS_PATHS": []}

    print(f"config is:\n{json.dumps(config.to_dict(), indent=4)}\n--")
    assert config.get("LOAD_DOTENV") == expected_blank_config["LOAD_DOTENV"]
    assert config.get("DEFAULT_SETTINGS_PATHS") == expected_blank_config["DEFAULT_SETTINGS_PATHS"]
    assert config.get("replacement_uuid", None) is None
    assert config.get("scrub_hyphenated_uuids", None) is None


def test_load_config_ignore_real_configs(sample_config_content, clean_cwd, clean_logger):
    """Test that real config files are ignored when PREPDIR_SKIP_CONFIG_FILE_LOAD=true."""
    real_config_path = clean_cwd / ".prepdir" / "config.yaml"
    real_config_path.parent.mkdir()
    real_config_path.write_text(yaml.safe_dump(sample_config_content))

    home_dir = clean_cwd / "home"
    home_dir.mkdir()
    home_config_path = home_dir / ".prepdir" / "config.yaml"
    home_config_path.parent.mkdir()
    home_config_path.write_text(yaml.safe_dump(sample_config_content))

    with patch.dict(
        os.environ,
        {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_FILE_LOAD": "true", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"},
    ):
        config = load_config("prepdir", quiet=True)

    print(f"config is:\n{json.dumps(config.to_dict(), indent=4)}\n--")
    # Everything should be blank
    assert config.get("exclude.directories", []) == []
    assert config.get("exclude.files", []) == []
    assert config.get("replacement_uuid", None) is None
    assert config.get("scrub_hyphenated_uuids", None) is None


def test_load_config_invalid_yaml(clean_cwd, clean_logger):
    """Test loading a config with invalid YAML raises an error."""
    config_path = clean_cwd / "invalid.yaml"
    config_path.write_text("invalid: yaml: : :")

    with pytest.raises(ValueError, match=f"Invalid YAML in custom config '{config_path}'"):
        load_config("prepdir", str(config_path), quiet=True)


def test_load_config_empty_yaml(clean_cwd, clean_logger):
    """Test loading an empty YAML config file."""
    config_path = clean_cwd / "empty.yaml"
    config_path.write_text("")

    config = load_config("prepdir", str(config_path), quiet=True)

    assert config.get("exclude.directories", []) == []
    assert config.get("exclude.files", []) == []
    assert config.get("replacement_uuid", None) is None
    assert config.get("scrub_hyphenated_uuids", None) is None


def test_load_config_missing_file(clean_cwd, clean_logger):
    """Test loading a non-existent config file."""
    config_path = clean_cwd / "nonexistent.yaml"

    with pytest.raises(ValueError, match=f"Custom config path '{config_path.resolve()}' does not exist"):
        load_config("prepdir", str(config_path), quiet=True)


def test_init_config_existing_file_no_force(sample_config_content, clean_cwd, clean_logger):
    """Test init_config raises SystemExit when config file exists and force=False."""
    config_path = clean_cwd / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))

    with pytest.raises(SystemExit, match="Config file '.*' already exists"):
        init_config(namespace="prepdir", config_path=str(config_path), force=False)


def test_init_config_force_overwrite(sample_config_content, clean_cwd, clean_logger):
    """Test init_config with force=True overwrites existing config file using get_bundled_config."""

    config_path = clean_cwd / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump({"OLD_KEY": "old_value"}))

    init_config(namespace="prepdir", config_path=str(config_path), force=True)

    bundled_yaml = yaml.safe_load(get_bundled_config("prepdir"))

    with config_path.open("r") as f:
        new_config = yaml.safe_load(f)

    assert new_config == bundled_yaml


def test_config_precedence(sample_config_content, clean_cwd, clean_logger, expected_bundled_config_content):
    """Test configuration precedence: custom > local > home > bundled."""
    bundled_yaml = yaml.safe_dump(sample_config_content)

    home_dir = clean_cwd / "home"
    home_dir.mkdir()
    home_config_path = home_dir / ".prepdir" / "config.yaml"
    home_config_path.parent.mkdir()
    home_config = {
        "EXCLUDE": {"DIRECTORIES": ["home_dir"], "FILES": ["home_file"]},
        "DEFAULT_OUTPUT_FILE": "home_dir.txt",
    }
    home_config_path.write_text(yaml.safe_dump(home_config))

    local_config_path = clean_cwd / ".prepdir" / "config.yaml"
    local_config_path.parent.mkdir()
    local_config = {
        "DEFAULT_OUTPUT_FILE": "local_dir.txt",
        "EXCLUDE": {"DIRECTORIES": ["local_dir"], "FILES": ["local_file"]},
    }
    local_config_path.write_text(yaml.safe_dump(local_config))

    custom_config_path = clean_cwd / "custom.yaml"
    custom_config = {
        "DEFAULT_OUTPUT_FILE": "custom_dir.txt",
        "EXCLUDE": {"DIRECTORIES": ["custom_dir"], "FILES": ["custom_file"]},
    }
    custom_config_path.write_text(yaml.safe_dump(custom_config))

    with patch.dict(
        os.environ,
        {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"},
    ):
        # Test custom config precedence
        config = load_config("prepdir", str(custom_config_path), quiet=True)
        assert config.get("default_output_file") == "custom_dir.txt"
        assert config.get("exclude.directories") == ["custom_dir"]

        # Test local config precedence (should merge arrays with home)
        config = load_config("prepdir", quiet=True)
        assert config.get("default_output_file") == "local_dir.txt"
        assert sorted(config.get("exclude.directories")) == sorted(["home_dir", "local_dir"])

        # Test home config only
        local_config_path.unlink()
        config = load_config("prepdir", quiet=True)
        assert config.get("default_output_file") == "home_dir.txt"
        assert config.get("exclude.directories") == ["home_dir"]

        # Test bundled config only (local and home have been removed)
        home_config_path.unlink()
        config = load_config("prepdir", quiet=True)
        assert config.get("default_output_file") == expected_bundled_config_content["DEFAULT_OUTPUT_FILE"]
        assert config.get("replacement_uuid") == expected_bundled_config_content["REPLACEMENT_UUID"]
        assert config.get("scrub_hyphenated_uuids") == expected_bundled_config_content["SCRUB_HYPHENATED_UUIDS"]


def test_multiple_namespaces(clean_cwd, clean_logger):
    """Test that different namespaces use different config files."""
    namespaces = ["prepdir", "applydir", "vibedir"]

    for namespace in namespaces:
        config_path = clean_cwd / f".{namespace}" / "config.yaml"
        config_path.parent.mkdir()
        config_content = {
            "DEFAULT_OUTPUT_FILE": f"{namespace}.txt",
            "EXCLUDE": {"DIRECTORIES": [f"{namespace}_dir"]},
        }
        config_path.write_text(yaml.safe_dump(config_content))

    for namespace in namespaces:
        with patch.dict(
            os.environ,
            {
                "HOME": str(clean_cwd / "home"),
                "PREPDIR_SKIP_CONFIG_FILE_LOAD": "false",
                "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false",
            },
        ):
            config = load_config(namespace, quiet=True)
            assert config.get("default_output_file") == f"{namespace}.txt"
            assert config.get("exclude.directories") == [f"{namespace}_dir"]


def test_load_config_no_files_no_bundled(clean_cwd, clean_logger):
    """Test load_config when no files are found and bundled config is skipped (lines 195-196)."""
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"}):
        config = load_config("prepdir", quiet=True)
        assert config.get("exclude.directories", []) == []
        assert config.get("exclude.files", []) == []
        assert any(
            "No custom, home, local, or bundled config files found" in record.message
            for record in clean_logger.handlers[-1].records
        )


def test_load_config_temp_file_cleanup_failure(clean_cwd, clean_logger):
    """Test load_config temporary file cleanup failure (lines 220-222)."""
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
        with patch("pathlib.Path.unlink", side_effect=OSError("Cannot delete")):
            config = load_config("prepdir", quiet=True)
            assert isinstance(config, Dynaconf)
            assert any(
                "Failed to remove temporary bundled config" in record.message
                for record in clean_logger.handlers[-1].records
            )


def test_init_config_create_failure(clean_cwd, clean_logger):
    """Test init_config file creation failure (lines 229-231)."""
    config_path = clean_cwd / ".prepdir" / "config.yaml"
    with patch("pathlib.Path.write_text", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit, match="Error: Failed to create config file"):
            init_config("prepdir", str(config_path), force=True)
        assert any("Failed to create config file" in record.message for record in clean_logger.handlers[-1].records)


def test_load_config_no_home_no_local(clean_cwd, clean_logger):
    """Test load_config when no home or local config exists (lines 167, 169-170)."""
    home_dir = clean_cwd / "home"
    home_dir.mkdir()
    with patch.dict(
        os.environ,
        {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"},
    ):
        config = load_config("prepdir", quiet=True)
        assert config.get("exclude.directories", []) == []
        assert any("No home config found at" in record.message for record in clean_logger.handlers[-1].records)
        assert any("No local config found at" in record.message for record in clean_logger.handlers[-1].records)


def test_version_load_failure(clean_logger):
    """Test version load failure in config.py (lines 15-16)."""
    with patch("importlib.metadata.version", side_effect=Exception("Version load failed")):
        import importlib
        import sys

        if "prepdir.config" in sys.modules:
            del sys.modules["prepdir.config"]
        import prepdir.config

        assert prepdir.config.__version__ == "0.0.0"
        assert any("Failed to load package version" in record.message for record in clean_logger.handlers[-1].records)


def test_is_resource_exception(clean_logger):
    """Test is_resource exception handling (line 47)."""
    with patch("importlib.resources.files", side_effect=TypeError("Invalid resource")):
        assert not is_resource("prepdir", "config.yaml")


def test_load_config_debug_log(clean_cwd, clean_logger):
    """Test load_config debug log (line 129)."""
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "true"}):
        config = load_config("prepdir", quiet=True)
        assert any(
            "Loading config with namespace='prepdir'" in record.message for record in clean_logger.handlers[-1].records
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
