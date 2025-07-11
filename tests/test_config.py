import os
import sys
import yaml
import pytest
import json
import logging
from io import StringIO
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from dynaconf import Dynaconf
from importlib.metadata import PackageNotFoundError
from prepdir.config import load_config, check_namespace_value, init_config, check_config_format, get_bundled_config
from prepdir import prepdir_logging

# Set up logger
logger = logging.getLogger("prepdir.config")

@pytest.fixture
def clean_cwd(tmp_path):
    """Change working directory to a clean temporary path to avoid loading real configs."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield
    os.chdir(original_cwd)

@pytest.fixture
def sample_config_content():
    """Provide sample configuration content."""
    return {
        "EXCLUDE": {
            "DIRECTORIES": [".git", "__pycache__"],
            "FILES": ["*.pyc", "*.log"],
        },
        "REPLACEMENT_UUID": "12345678-1234-1234-4321-4321432143214321",
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": False,
    }

def show_config_lines(config_file_path: str, name: str = "Test"):
    """Print config file contents for debugging."""
    with open(config_file_path, "r") as f:
        config_lines = f.read()
    print(f"{name} config lines in '{config_file_path}':\n--\n{config_lines}\n--\n")

@pytest.mark.timeout(30)
def test_check_namespace_value(clean_cwd):
    """Test namespace validation."""
    print("Starting test_check_namespace_value")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    check_namespace_value("prepdir")
    check_namespace_value("applydir")
    check_namespace_value("vibedir_123")
    with pytest.raises(ValueError, match="Invalid namespace '': must be non-empty"):
        check_namespace_value("")
    with pytest.raises(ValueError, match="Invalid namespace 'invalid@name': must be a valid Python identifier"):
        check_namespace_value("invalid@name")

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_check_namespace_value")

@pytest.mark.timeout(30)
def test_check_config_format():
    """Test check_config_format for valid and invalid YAML."""
    print("Starting test_check_config_format")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    # Valid YAML
    check_config_format("key: value", "test config")
    # Invalid YAML
    with pytest.raises(ValueError, match="Invalid YAML in test config"):
        check_config_format("invalid: yaml: : :", "test config")
    log_output = log_stream.getvalue()
    assert "Invalid YAML in test config" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_check_config_format")

'''@pytest.mark.timeout(30)
def test_get_bundled_config(clean_cwd, sample_config_content):
    """Test get_bundled_config for valid, missing, and invalid bundled config."""
    print("Starting test_get_bundled_config")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    print(f"Creating bundled_path: {bundled_path}")
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(sample_config_content))
    print("Bundled path created")

    # Valid bundled config
    with patch("importlib.resources.files") as mock_files:
        print("Patching importlib.resources.files for valid config")
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = yaml.safe_dump(sample_config_content)
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            content = get_bundled_config("prepdir")
            assert content == yaml.safe_dump(sample_config_content)
            log_output = log_stream.getvalue()
            assert f"Bundled config content: {content}" in log_output
            assert f"Checking is_resource(prepdir, config.yaml)" in log_output
    print("Valid bundled config test complete")
    log_stream.truncate(0)
    log_stream.seek(0)

    # Missing bundled config
    with patch("prepdir.config.is_resource", return_value=False):
        print("Testing missing bundled config")
        with pytest.raises(ValueError, match="No bundled config found for prepdir"):
            get_bundled_config("prepdir")
        log_output = log_stream.getvalue()
        assert "No bundled config found for prepdir" in log_output
    print("Missing bundled config test complete")
    log_stream.truncate(0)
    log_stream.seek(0)

    # Invalid YAML
    with patch("importlib.resources.files") as mock_files:
        print("Testing invalid YAML bundled config")
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = "invalid: yaml: : :"
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            with pytest.raises(ValueError, match="Invalid YAML in bundled config for 'prepdir'"):
                get_bundled_config("prepdir")
            log_output = log_stream.getvalue()
            assert "Invalid YAML in bundled config for 'prepdir'" in log_output
    print("Invalid YAML bundled config test complete")

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_get_bundled_config")'''

@pytest.mark.timeout(30)
def test_load_config_from_specific_path(sample_config_content, clean_cwd):
    """Test loading local configuration from .prepdir/config.yaml."""
    print("Starting test_load_config_from_specific_path")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    config_path = Path(".prepdir") / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(config_path)

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "true"}):
        with patch('sys.stdout', new=stdout_capture):
            with patch('sys.stderr', new=stderr_capture):
                config = load_config("prepdir", str(config_path), quiet=False, settings_files=[str(config_path)])
    assert config.get("exclude.directories") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("exclude.files") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("replacement_uuid") == sample_config_content["REPLACEMENT_UUID"]
    assert config.get("scrub_hyphenated_uuids") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("scrub_hyphenless_uuids") == sample_config_content["SCRUB_HYPHENLESS_UUIDS"]

    log_output = log_stream.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in log_output
    stdout_output = stdout_capture.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_from_specific_path")

@pytest.mark.timeout(30)
def test_load_config_home(sample_config_content, clean_cwd, monkeypatch):
    """Test loading configuration from ~/.prepdir/config.yaml."""
    print("Starting test_load_config_home")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    home_dir = Path("home")
    home_dir.mkdir()
    config_path = home_dir / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(config_path)

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_FILE_LOAD", "false")

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", quiet=False)
    assert config.get("exclude.directories") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("exclude.files") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("scrub_hyphenated_uuids") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("replacement_uuid") == sample_config_content["REPLACEMENT_UUID"]
    log_output = log_stream.getvalue()
    assert f"Found home config: {config_path.resolve()}" in log_output
    stdout_output = stdout_capture.getvalue()
    assert f"Found home config: {config_path.resolve()}" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_home")

@pytest.mark.timeout(30)
def test_load_config_bundled(clean_cwd, sample_config_content):
    """Test loading bundled configuration."""
    print("Starting test_load_config_bundled")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(bundled_path)

    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = yaml.safe_dump(sample_config_content)
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
                stdout_capture = StringIO()
                stderr_capture = StringIO()
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        config = load_config("prepdir", quiet=False)
    assert config.get("exclude.directories") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("exclude.files") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("scrub_hyphenated_uuids") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("replacement_uuid") == sample_config_content["REPLACEMENT_UUID"]
    log_output = log_stream.getvalue()
    assert "_prepdir_bundled_config.yaml" in log_output
    assert f"Checking is_resource(prepdir, config.yaml)" in log_output
    assert "Loaded bundled config into temporary file" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "Will use default config" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_bundled")

@pytest.mark.timeout(30)
def test_load_config_bundled_missing(clean_cwd):
    """Test handling missing bundled config."""
    print("Starting test_load_config_bundled_missing")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.is_resource", return_value=False):
        with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
            with patch('sys.stdout', new=stdout_capture):
                with patch('sys.stderr', new=stderr_capture):
                    config = load_config("prepdir", quiet=False)
    assert config.get("replacement_uuid", None) is None
    assert config.get("scrub_hyphenated_uuids", None) is None
    log_output = log_stream.getvalue()
    assert "No custom, home, local, or bundled config files found for prepdir, using defaults" in log_output
    stdout_output = stdout_capture.getvalue()
    assert stdout_output == ""  # No stdout output expected

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_bundled_missing")

@pytest.mark.timeout(30)
def test_load_config_bundled_permission_error(clean_cwd, sample_config_content):
    """Test bundled config loading with PermissionError."""
    print("Starting test_load_config_bundled_permission_error")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(sample_config_content))

    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = yaml.safe_dump(sample_config_content)
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            with patch("prepdir.config.tempfile.NamedTemporaryFile", side_effect=PermissionError("Permission denied")):
                with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
                    stdout_capture = StringIO()
                    stderr_capture = StringIO()
                    with patch('sys.stdout', new=stdout_capture):
                        with patch('sys.stderr', new=stderr_capture):
                            with pytest.raises(
                                ValueError, match="Failed to load bundled config for prepdir: Permission denied"
                            ):
                                load_config("prepdir", quiet=False)
    log_output = log_stream.getvalue()
    assert "Failed to load bundled config for prepdir: Permission denied" in log_output
    stderr_output = stderr_capture.getvalue()
    assert "Failed to load bundled config for prepdir: Permission denied" in stderr_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_bundled_permission_error")

@pytest.mark.timeout(30)
def test_load_config_bundled_cleanup_failure(sample_config_content, clean_cwd):
    """Test failure to clean up temporary bundled config file."""
    print("Starting test_load_config_bundled_cleanup_failure")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.WARNING)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(sample_config_content))

    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = yaml.safe_dump(sample_config_content)
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            with patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
                with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
                    stdout_capture = StringIO()
                    stderr_capture = StringIO()
                    with patch('sys.stdout', new=stdout_capture):
                        with patch('sys.stderr', new=stderr_capture):
                            config = load_config("prepdir", quiet=False)
    assert config.get("replacement_uuid") == sample_config_content["REPLACEMENT_UUID"]
    log_output = log_stream.getvalue()
    assert "Failed to remove temporary bundled config" in log_output
    assert "Permission denied" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "Will use default config" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_bundled_cleanup_failure")

@pytest.mark.timeout(30)
def test_load_config_no_configs_with_skip(clean_cwd, monkeypatch):
    """Test no config files with PREPDIR_SKIP_CONFIG_FILE_LOAD=true and PREPDIR_SKIP_BUNDLED_CONFIG_LOAD=true."""
    print("Starting test_load_config_no_configs_with_skip")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Test with both environment variables set to true
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_FILE_LOAD", "true")
    monkeypatch.setenv("PREPDIR_SKIP_BUNDLED_CONFIG_LOAD", "true")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", quiet=False)
    assert config.get("replacement_uuid", None) is None
    assert config.get("scrub_hyphenated_uuids", None) is None
    log_output = log_stream.getvalue()
    assert "No custom, home, local, or bundled config files found for prepdir, using defaults" in log_output
    stdout_output = stdout_capture.getvalue()
    assert stdout_output == ""  # No stdout output expected
    log_stream.truncate(0)
    log_stream.seek(0)

    # Test with only PREPDIR_SKIP_BUNDLED_CONFIG_LOAD=true
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_FILE_LOAD", "false")
    monkeypatch.setenv("PREPDIR_SKIP_BUNDLED_CONFIG_LOAD", "true")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", quiet=False)
    assert config.get("replacement_uuid", None) is None
    assert config.get("scrub_hyphenated_uuids", None) is None
    log_output = log_stream.getvalue()
    assert "No custom, home, local, or bundled config files found for prepdir, using defaults" in log_output
    stdout_output = stdout_capture.getvalue()
    assert stdout_output == ""  # No stdout output expected

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_no_configs_with_skip")

@pytest.mark.timeout(30)
def test_load_config_ignore_real_configs(sample_config_content, clean_cwd, monkeypatch):
    """Test that real config files are ignored when PREPDIR_SKIP_CONFIG_FILE_LOAD=true."""
    print("Starting test_load_config_ignore_real_configs")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    real_config_path = Path(".prepdir") / "config.yaml"
    real_config_path.parent.mkdir()
    real_config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(real_config_path, "real_config_path")

    home_dir = Path("home")
    home_dir.mkdir()
    home_config_path = home_dir / ".prepdir" / "config.yaml"
    home_config_path.parent.mkdir()
    home_config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(home_config_path, "home_config_path")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_FILE_LOAD", "true")
    monkeypatch.setenv("PREPDIR_SKIP_BUNDLED_CONFIG_LOAD", "true")

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", quiet=False)
    log_output = log_stream.getvalue()
    assert "No custom, home, local, or bundled config files found for prepdir, using defaults" in log_output
    assert config.get("exclude.directories", []) == []
    assert config.get("exclude.files", []) == []
    stdout_output = stdout_capture.getvalue()
    assert stdout_output == ""  # No stdout output expected

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_ignore_real_configs")

@pytest.mark.timeout(30)
def test_load_config_invalid_yaml(clean_cwd):
    """Test loading a config with invalid YAML raises an error and logs."""
    print("Starting test_load_config_invalid_yaml")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    config_path = Path("invalid.yaml")
    config_path.write_text("invalid: yaml: : :")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            with pytest.raises(ValueError, match=f"Invalid YAML in custom config '{config_path}'"):
                load_config("prepdir", str(config_path), quiet=False)
    log_output = log_stream.getvalue()
    assert f"Invalid YAML in custom config '{config_path}'" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_invalid_yaml")

@pytest.mark.timeout(30)
def test_load_config_empty_yaml(clean_cwd):
    """Test loading an empty YAML config file."""
    print("Starting test_load_config_empty_yaml")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    config_path = Path("empty.yaml")
    config_path.write_text("")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", str(config_path), quiet=False)
    assert config.get("exclude.directories", []) == []
    assert config.get("exclude.files", []) == []
    assert config.get("scrub_hyphenated_uuids", True) is True
    log_output = log_stream.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in log_output
    stdout_output = stdout_capture.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_empty_yaml")

@pytest.mark.timeout(30)
def test_load_config_missing_file(clean_cwd):
    """Test loading a non-existent config file."""
    print("Starting test_load_config_missing_file")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    config_path = Path("nonexistent.yaml")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            with pytest.raises(ValueError, match=f"Custom config path '{config_path.resolve()}' does not exist"):
                load_config("prepdir", str(config_path), quiet=False)
    log_output = log_stream.getvalue()
    assert f"Custom config path '{config_path.resolve()}' does not exist" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_missing_file")

@pytest.mark.timeout(30)
def test_init_config_existing_file_no_force(sample_config_content, clean_cwd):
    """Test init_config raises SystemExit when config file exists and force=False."""
    print("Starting test_init_config_existing_file_no_force")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    config_path = Path(".prepdir") / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(config_path)

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            with pytest.raises(SystemExit, match="Config file '.*' already exists"):
                init_config(namespace="prepdir", config_path=str(config_path), force=False)
    log_output = log_stream.getvalue()
    assert f"Config file '{config_path}' already exists. Use force=True to overwrite" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_init_config_existing_file_no_force")

@pytest.mark.timeout(30)
def test_init_config_force_overwrite(sample_config_content, clean_cwd):
    """Test init_config with force=True overwrites existing config file using a bundled config."""
    print("Starting test_init_config_force_overwrite")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(bundled_path, "bundled_config")

    config_path = Path(".prepdir") / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump({"OLD_KEY": "old_value"}))
    show_config_lines(config_path, "original_config")

    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = yaml.safe_dump(sample_config_content)
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            with patch('sys.stdout', new=stdout_capture):
                with patch('sys.stderr', new=stderr_capture):
                    init_config(namespace="prepdir", config_path=str(config_path), force=True)

    with config_path.open("r") as f:
        new_config = yaml.safe_load(f)
    assert new_config == sample_config_content
    stdout_output = stdout_capture.getvalue()
    assert f"Created '{config_path}' with default configuration." in stdout_output
    log_output = log_stream.getvalue()
    assert f"Created '{config_path}' with default configuration." in log_output
    assert f"Checking is_resource(prepdir, config.yaml)" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_init_config_force_overwrite")

@pytest.mark.timeout(30)
def test_init_config_permission_error(sample_config_content, clean_cwd):
    """Test init_config with permission error when writing config file."""
    print("Starting test_init_config_permission_error")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    config_path = Path(".prepdir") / "config.yaml"
    config_path.parent.mkdir()

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(sample_config_content))

    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = yaml.safe_dump(sample_config_content)
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
                stdout_capture = StringIO()
                stderr_capture = StringIO()
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        with pytest.raises(SystemExit, match="Failed to create config file"):
                            init_config(namespace="prepdir", config_path=str(config_path), force=True)
    log_output = log_stream.getvalue()
    assert f"Failed to create config file '{config_path}'" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_init_config_permission_error")

@pytest.mark.timeout(30)
def test_init_config_missing_bundled(clean_cwd):
    """Test init_config with missing bundled config."""
    print("Starting test_init_config_missing_bundled")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    config_path = Path(".prepdir") / "config.yaml"
    config_path.parent.mkdir()

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.is_resource", return_value=False):
        with patch('sys.stdout', new=stdout_capture):
            with patch('sys.stderr', new=stderr_capture):
                with pytest.raises(SystemExit, match="Failed to initialize config: No bundled config found for prepdir"):
                    init_config(namespace="prepdir", config_path=str(config_path), force=True)
    log_output = log_stream.getvalue()
    assert "No bundled config found for prepdir" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_init_config_missing_bundled")

@pytest.mark.timeout(30)
def test_init_config_invalid_directory(clean_cwd):
    """Test init_config with invalid directory path."""
    print("Starting test_init_config_invalid_directory")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    config_path = Path("/invalid/path/config.yaml")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.is_resource", return_value=True):
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
            with patch('sys.stdout', new=stdout_capture):
                with patch('sys.stderr', new=stderr_capture):
                    with pytest.raises(SystemExit, match="Failed to create config file"):
                        init_config(namespace="prepdir", config_path=str(config_path), force=True)
    log_output = log_stream.getvalue()
    assert f"Failed to create config file '{config_path}'" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_init_config_invalid_directory")

@pytest.mark.timeout(30)
def test_version_package_not_found(clean_cwd):
    """Test __version__ assignment when package is not found."""
    print("Starting test_version_package_not_found")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    if "prepdir.config" in sys.modules:
        del sys.modules["prepdir.config"]

    class CustomPackageNotFoundError(Exception):
        def __init__(self, name):
            self.args = (name,)
            self.name = name

    with patch("importlib.metadata.version", side_effect=CustomPackageNotFoundError("prepdir")):
        import importlib
        import prepdir.config
        importlib.reload(prepdir.config)
        assert prepdir.config.__version__ == "0.0.0"
    log_output = log_stream.getvalue()
    assert "Failed to load package version" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_version_package_not_found")

@pytest.fixture
def namespace_configs(sample_config_content, clean_cwd, monkeypatch):
    """Set up config files for multiple namespaces."""
    print("Starting namespace_configs fixture")
    namespaces = ["prepdir", "applydir", "vibedir"]
    home_dir = Path("home")
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_FILE_LOAD", "false")
    monkeypatch.setenv("PREPDIR_SKIP_BUNDLED_CONFIG_LOAD", "true")

    configs = {}
    for namespace in namespaces:
        configs[namespace] = {}
        
        # Home config
        home_config_path = home_dir / f".{namespace}" / "config.yaml"
        home_config_path.parent.mkdir(parents=True, exist_ok=True)
        home_config = sample_config_content.copy()
        home_config["EXCLUDE"]["DIRECTORIES"] = [f"global_{namespace}_dir"]
        home_config["EXCLUDE"]["FILES"] = [f"global_{namespace}_file"]
        home_config["REPLACEMENT_UUID"] = f"11111111-{namespace}-1111-1111-111111111111"
        home_config_path.write_text(yaml.safe_dump(home_config))
        configs[namespace]["home"] = home_config_path
        show_config_lines(home_config_path, f"{namespace}_home_config")

        # Local config
        local_config_path = Path(f".{namespace}") / "config.yaml"
        local_config_path.parent.mkdir(parents=True, exist_ok=True)
        local_config = sample_config_content.copy()
        local_config["EXCLUDE"]["DIRECTORIES"] = [f"local_{namespace}_dir"]
        local_config["EXCLUDE"]["FILES"] = [f"local_{namespace}_file"]
        local_config["REPLACEMENT_UUID"] = f"22222222-{namespace}-2222-2222-222222222222"
        local_config_path.write_text(yaml.safe_dump(local_config))
        configs[namespace]["local"] = local_config_path
        show_config_lines(local_config_path, f"{namespace}_local_config")

        # Custom config
        custom_config_path = Path(f"{namespace}_custom.yaml")
        custom_config = sample_config_content.copy()
        custom_config["EXCLUDE"]["DIRECTORIES"] = [f"custom_{namespace}_dir"]
        custom_config["EXCLUDE"]["FILES"] = [f"custom_{namespace}_file"]
        custom_config["REPLACEMENT_UUID"] = f"33333333-{namespace}-3333-3333-333333333333"
        custom_config_path.write_text(yaml.safe_dump(custom_config))
        configs[namespace]["custom"] = custom_config_path
        show_config_lines(custom_config_path, f"{namespace}_custom_config")

    yield configs
    print("Completed namespace_configs fixture")

@pytest.mark.timeout(30)
def test_config_precedence(sample_config_content, clean_cwd, monkeypatch):
    """Test configuration precedence: custom > local > home > bundled, with list merging."""
    print("Starting test_config_precedence")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    bundled_config = {
        "EXCLUDE": {"DIRECTORIES": ["bundled_dir"], "FILES": ["bundled_file"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "SCRUB_HYPHENLESS_UUIDS": False,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000",
    }
    bundled_yaml = yaml.safe_dump(bundled_config)
    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(bundled_yaml)
    show_config_lines(bundled_path, "bundled_path")

    home_dir = Path("home")
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config = {
        "EXCLUDE": {"DIRECTORIES": ["global_dir"], "FILES": ["global_file"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "SCRUB_HYPHENLESS_UUIDS": True,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111",
    }
    global_config_path.write_text(yaml.safe_dump(global_config))
    show_config_lines(global_config_path, "global_config_path")

    local_config_path = Path(".prepdir") / "config.yaml"
    local_config_path.parent.mkdir()
    local_config = {
        "EXCLUDE": {"DIRECTORIES": ["local_dir"], "FILES": ["local_file"]},
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": False,
        "REPLACEMENT_UUID": "22222222-2222-2222-2222-222222222222",
    }
    local_config_path.write_text(yaml.safe_dump(local_config))
    show_config_lines(local_config_path, "local_config_path")

    custom_config_path = Path("custom.yaml")
    custom_config = {
        "EXCLUDE": {"DIRECTORIES": ["custom_dir"], "FILES": ["custom_file"]},
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": True,
        "REPLACEMENT_UUID": "33333333-3333-3333-3333-333333333333",
    }
    custom_config_path.write_text(yaml.safe_dump(custom_config))
    show_config_lines(custom_config_path, "custom_config_path")

    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource.__str__.return_value = str(bundled_path)
        mock_resource.open.return_value.__enter__.return_value.read.return_value = bundled_yaml
        mock_files.return_value.__truediv__.return_value = mock_resource
        with patch("prepdir.config.is_resource", return_value=True):
            with patch.dict(os.environ, {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_FILE_LOAD": "false", "PREPDIR_SKIP_BUNDLED_CONFIG_LOAD": "false"}):
                stdout_capture = StringIO()
                stderr_capture = StringIO()
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        # First precedence: custom config
                        config = load_config("prepdir", str(custom_config_path), quiet=False)
                        assert config.get("replacement_uuid") == "33333333-3333-3333-3333-333333333333"
                        assert config.get("scrub_hyphenated_uuids") is True
                        assert config.get("scrub_hyphenless_uuids") is True
                        assert config.get("exclude.directories") == ["custom_dir"]
                        assert config.get("exclude.files") == ["custom_file"]
                        log_output = log_stream.getvalue()
                        assert f"Using custom config path: {custom_config_path.resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Using custom config path: {custom_config_path.resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        # Second precedence: local + home config (lists merged)
                        config = load_config("prepdir", quiet=False)
                        assert config.get("replacement_uuid") == "22222222-2222-2222-2222-222222222222"
                        assert config.get("scrub_hyphenated_uuids") is True
                        assert config.get("scrub_hyphenless_uuids") is False
                        assert sorted(config.get("exclude.directories")) == sorted(["global_dir", "local_dir"])
                        assert sorted(config.get("exclude.files")) == sorted(["global_file", "local_file"])
                        log_output = log_stream.getvalue()
                        assert f"Found local config: {local_config_path.resolve()}" in log_output
                        assert f"Found home config: {global_config_path.resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Found local config: {local_config_path.resolve()}" in stdout_output
                        assert f"Found home config: {global_config_path.resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        # Third precedence: home config
                        local_config_path.unlink()
                        config = load_config("prepdir", quiet=False)
                        assert config.get("replacement_uuid") == "11111111-1111-1111-1111-111111111111"
                        assert config.get("scrub_hyphenated_uuids") is False
                        assert config.get("scrub_hyphenless_uuids") is True
                        assert config.get("exclude.directories") == ["global_dir"]
                        assert config.get("exclude.files") == ["global_file"]
                        log_output = log_stream.getvalue()
                        assert f"Found home config: {global_config_path.resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Found home config: {global_config_path.resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        # Fourth precedence: bundled
                        global_config_path.unlink()
                        config = load_config("prepdir", quiet=False)
                        assert config.get("replacement_uuid") == "00000000-0000-0000-0000-000000000000"
                        assert config.get("scrub_hyphenated_uuids") is False
                        assert config.get("scrub_hyphenless_uuids") is False
                        assert config.get("exclude.directories") == ["bundled_dir"]
                        assert config.get("exclude.files") == ["bundled_file"]
                        log_output = log_stream.getvalue()
                        assert f"Loaded bundled config into temporary file" in log_output
                        assert f"Checking is_resource(prepdir, config.yaml)" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert "Will use default config" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_config_precedence")

@pytest.mark.timeout(30)
def test_load_config_namespace_variants(namespace_configs, sample_config_content, clean_cwd, monkeypatch):
    """Test loading configuration with different namespaces (prepdir, applydir, vibedir)."""
    print("Starting test_load_config_namespace_variants")
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    def mock_is_resource(namespace, resource_name):
        logger.debug(f"mock_is_resource called with namespace={namespace}, resource_name={resource_name}")
        return False

    monkeypatch.setattr("prepdir.config.is_resource", mock_is_resource)
    with patch("importlib.resources.files") as mock_files:
        mock_resource = MagicMock()
        mock_resource_path = MagicMock()
        mock_resource_path.__str__.return_value = str(Path("mocked/config.yaml"))
        mock_files.return_value.__truediv__.return_value = mock_resource_path

        if "prepdir.config" in sys.modules:
            del sys.modules["prepdir.config"]

        def mock_path_open(self, *args, **kwargs):
            if str(self) == "/workspaces/prepdir/src/prepdir/config.yaml":
                raise FileNotFoundError("Mocked: No real bundled config")
            with open(self, *args, **kwargs) as f:
                return f

        monkeypatch.setattr("pathlib.Path.open", mock_path_open)

        namespaces = ["prepdir", "applydir", "vibedir"]

        for namespace in namespaces:
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            with patch('sys.stdout', new=stdout_capture):
                with patch('sys.stderr', new=stderr_capture):
                    # Custom config
                    config = load_config(namespace, str(namespace_configs[namespace]["custom"]), quiet=False)
                    assert config.get("replacement_uuid") == f"33333333-{namespace}-3333-3333-333333333333"
                    assert config.get("exclude.directories") == [f"custom_{namespace}_dir"]
                    assert config.get("exclude.files") == [f"custom_{namespace}_file"]
                    log_output = log_stream.getvalue()
                    assert f"Using custom config path: {namespace_configs[namespace]['custom'].resolve()}" in log_output
                    stdout_output = stdout_capture.getvalue()
                    assert f"Using custom config path: {namespace_configs[namespace]['custom'].resolve()}" in stdout_output
                    stdout_capture.truncate(0)
                    stdout_capture.seek(0)
                    stderr_capture.truncate(0)
                    stderr_capture.seek(0)
                    log_stream.truncate(0)
                    log_stream.seek(0)

                    # Local + home config (lists merged)
                    config = load_config(namespace, quiet=False)
                    assert config.get("replacement_uuid") == f"22222222-{namespace}-2222-2222-222222222222"
                    assert sorted(config.get("exclude.directories")) == sorted([f"global_{namespace}_dir", f"local_{namespace}_dir"])
                    assert sorted(config.get("exclude.files")) == sorted([f"global_{namespace}_file", f"local_{namespace}_file"])
                    log_output = log_stream.getvalue()
                    assert f"Found local config: {namespace_configs[namespace]['local'].resolve()}" in log_output
                    assert f"Found home config: {namespace_configs[namespace]['home'].resolve()}" in log_output
                    stdout_output = stdout_capture.getvalue()
                    assert f"Found local config: {namespace_configs[namespace]['local'].resolve()}" in stdout_output
                    assert f"Found home config: {namespace_configs[namespace]['home'].resolve()}" in stdout_output
                    stdout_capture.truncate(0)
                    stdout_capture.seek(0)
                    stderr_capture.truncate(0)
                    stderr_capture.seek(0)
                    log_stream.truncate(0)
                    log_stream.seek(0)

                    # Home config
                    namespace_configs[namespace]["local"].unlink()
                    config = load_config(namespace, quiet=False)
                    assert config.get("replacement_uuid") == f"11111111-{namespace}-1111-1111-111111111111"
                    assert config.get("exclude.directories") == [f"global_{namespace}_dir"]
                    assert config.get("exclude.files") == [f"global_{namespace}_file"]
                    log_output = log_stream.getvalue()
                    assert f"Found home config: {namespace_configs[namespace]['home'].resolve()}" in log_output
                    stdout_output = stdout_capture.getvalue()
                    assert f"Found home config: {namespace_configs[namespace]['home'].resolve()}" in stdout_output
                    stdout_capture.truncate(0)
                    stdout_capture.seek(0)
                    stderr_capture.truncate(0)
                    stderr_capture.seek(0)
                    log_stream.truncate(0)
                    log_stream.seek(0)

                    # No config (should return empty config for all namespaces)
                    namespace_configs[namespace]["home"].unlink()
                    config = load_config(namespace, quiet=False)
                    print(f"config for '{namespace}' is {json.dumps(config.to_dict(), indent=4)}")
                    assert config.get("replacement_uuid", None) is None
                    assert config.get("exclude.directories", None) is None
                    assert config.get("exclude.files", None) is None
                    log_output = log_stream.getvalue()
                    assert f"No custom, home, local, or bundled config files found for {namespace}, using defaults" in log_output
                    stdout_output = stdout_capture.getvalue()
                    assert stdout_output == ""  # No stdout output expected

    logger.removeHandler(handler)
    logger.handlers.clear()
    print("Completed test_load_config_namespace_variants")

if __name__ == "__main__":
    pytest.main([__file__])