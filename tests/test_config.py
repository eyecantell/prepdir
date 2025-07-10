import os
import sys
import yaml
import pytest
import logging
from io import StringIO
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from dynaconf import Dynaconf
from importlib.metadata import PackageNotFoundError
from prepdir.config import load_config, check_namespace_value, init_config
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

def test_check_namespace_value(clean_cwd):
    """Test namespace validation."""
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
    with pytest.raises(ValueError, match="Invalid namespace 'invalid@name': must be non-empty"):
        check_namespace_value("invalid@name")

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_from_specific_path(sample_config_content, clean_cwd):
    """Test loading local configuration from .prepdir/config.yaml."""
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
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
        with patch('sys.stdout', new=stdout_capture):
            with patch('sys.stderr', new=stderr_capture):
                config = load_config("prepdir", str(config_path), quiet=False)

    assert config.get("EXCLUDE.DIRECTORIES") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE.FILES") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("REPLACEMENT_UUID") == sample_config_content["REPLACEMENT_UUID"]
    assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("SCRUB_HYPHENLESS_UUIDS") == sample_config_content["SCRUB_HYPHENLESS_UUIDS"]

    log_output = log_stream.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in log_output
    stdout_output = stdout_capture.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_home(sample_config_content, clean_cwd, monkeypatch):
    """Test loading configuration from ~/.prepdir/config.yaml."""
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
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "false")

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", quiet=False)

    assert config.get("EXCLUDE.DIRECTORIES") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE.FILES") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("REPLACEMENT_UUID") == sample_config_content["REPLACEMENT_UUID"]
    log_output = log_stream.getvalue()
    assert f"Found home config: {config_path.resolve()}" in log_output
    stdout_output = stdout_capture.getvalue()
    assert f"Found home config: {config_path.resolve()}" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_bundled(clean_cwd):
    """Test loading bundled configuration."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_config_content = {
        "EXCLUDE": {"DIRECTORIES": ["bundled_dir"], "FILES": ["*.py"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111",
    }
    bundled_path.write_text(yaml.safe_dump(bundled_config_content))
    show_config_lines(bundled_path)

    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding="utf-8")
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        config = load_config("prepdir", quiet=False)
    assert config.get("EXCLUDE.DIRECTORIES") == ["bundled_dir"]
    assert config.get("EXCLUDE.FILES") == ["*.py"]
    assert config.get("SCRUB_HYPHENATED_UUIDS") is False
    assert config.get("REPLACEMENT_UUID") == "11111111-1111-1111-1111-111111111111"
    log_output = log_stream.getvalue()
    assert "_prepdir_bundled_config.yaml" in log_output
    assert "Attempting to load bundled config" in log_output
    assert "Loaded config for prepdir" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "Will use default config" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_bundled_missing(clean_cwd):
    """Test handling missing bundled config."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.is_resource", return_value=False):
        with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
            with patch('sys.stdout', new=stdout_capture):
                with patch('sys.stderr', new=stderr_capture):
                    config = load_config("prepdir", quiet=False)
    assert config.get("REPLACEMENT_UUID", None) is None
    assert config.get("SCRUB_HYPHENATED_UUIDS", None) is None
    log_output = log_stream.getvalue()
    assert "No bundled config found for prepdir, using defaults" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "No bundled config found for prepdir, using defaults" not in stdout_output  # No stdout output expected

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_bundled_permission_error(clean_cwd):
    """Test bundled config loading with PermissionError."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(Path("src") / "prepdir" / "config.yaml")
    mock_files.__truediv__.return_value = mock_resource

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch("prepdir.config.tempfile.NamedTemporaryFile", side_effect=PermissionError("Permission denied")):
                with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
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

def test_load_config_bundled_cleanup_failure(sample_config_content, clean_cwd):
    """Test failure to clean up temporary bundled config file."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.WARNING)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)

    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_config_content = {
        "EXCLUDE": {"DIRECTORIES": ["bundled_dir"], "FILES": ["*.py"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111",
    }
    bundled_path.write_text(yaml.safe_dump(bundled_config_content))

    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding="utf-8")
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
                with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
                    with patch('sys.stdout', new=stdout_capture):
                        with patch('sys.stderr', new=stderr_capture):
                            config = load_config("prepdir", quiet=False)
    assert config.get("REPLACEMENT_UUID") == "11111111-1111-1111-1111-111111111111"
    log_output = log_stream.getvalue()
    assert "Failed to remove temporary bundled config" in log_output
    assert "Permission denied" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "Will use default config" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_no_configs_with_skip(clean_cwd, monkeypatch):
    """Test no config files with PREPDIR_SKIP_CONFIG_LOAD=true."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "true")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.is_resource", return_value=False):
        with patch('sys.stdout', new=stdout_capture):
            with patch('sys.stderr', new=stderr_capture):
                config = load_config("prepdir", quiet=False)
    assert config.get("REPLACEMENT_UUID", None) is None
    assert config.get("SCRUB_HYPHENATED_UUIDS", None) is None
    log_output = log_stream.getvalue()
    assert "Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_ignore_real_configs(sample_config_content, clean_cwd, monkeypatch):
    """Test that real config files are ignored when PREPDIR_SKIP_CONFIG_LOAD=true."""
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
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "true")

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            config = load_config("prepdir", quiet=False)

    log_output = log_stream.getvalue()
    assert "Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true" in log_output
    assert config.get("EXCLUDE.DIRECTORIES", []) == []
    assert config.get("EXCLUDE.FILES", []) == []
    stdout_output = stdout_capture.getvalue()
    assert "Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_config_precedence(sample_config_content, clean_cwd, monkeypatch):
    """Test configuration precedence: custom > local > global > bundled using non-list fields."""
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
    bundled_path = Path("src") / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(bundled_config))
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

    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding="utf-8")
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource

    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch.dict(os.environ, {"HOME": str(home_dir), "PREPDIR_SKIP_CONFIG_LOAD": "false"}):
                stdout_capture = StringIO()
                stderr_capture = StringIO()
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        # First precedence: custom config
                        config = load_config("prepdir", str(custom_config_path), quiet=False)
                        assert config.get("REPLACEMENT_UUID") == "33333333-3333-3333-3333-333333333333"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") is True
                        assert config.get("SCRUB_HYPHENLESS_UUIDS") is True
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

                        # Second precedence: local .prepdir/config
                        config = load_config("prepdir", quiet=False)
                        assert config.get("REPLACEMENT_UUID") == "22222222-2222-2222-2222-222222222222"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") is True
                        assert config.get("SCRUB_HYPHENLESS_UUIDS") is False
                        log_output = log_stream.getvalue()
                        assert f"Found local config: {local_config_path.resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Found local config: {local_config_path.resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        # Third precedence: ~/.prepdir/config
                        local_config_path.unlink()
                        config = load_config("prepdir", quiet=False)
                        assert config.get("REPLACEMENT_UUID") == "11111111-1111-1111-1111-111111111111"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") is False
                        assert config.get("SCRUB_HYPHENLESS_UUIDS") is True
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

                        # Last precedence: bundled config
                        global_config_path.unlink()
                        config = load_config("prepdir", quiet=False)
                        assert config.get("REPLACEMENT_UUID") == "00000000-0000-0000-0000-000000000000"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") is False
                        assert config.get("SCRUB_HYPHENLESS_UUIDS") is False
                        log_output = log_stream.getvalue()
                        assert "_prepdir_bundled_config.yaml" in log_output
                        assert "Attempting to load bundled config" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert "Will use default config" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_invalid_yaml(clean_cwd):
    """Test loading a config with invalid YAML raises an error and logs."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    config_path = Path("invalid.yaml")
    config_path.write_text("invalid: yaml: : :")
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch('sys.stdout', new=stdout_capture):
        with patch('sys.stderr', new=stderr_capture):
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_config("prepdir", str(config_path), quiet=False)
    log_output = log_stream.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in log_output
    assert "Invalid YAML in config file(s)" in log_output
    stderr_output = stderr_capture.getvalue()
    assert "Invalid YAML in config file(s)" in stderr_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_empty_yaml(clean_cwd):
    """Test loading an empty YAML config file."""
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
    assert config.get("EXCLUDE.DIRECTORIES", []) == []
    assert config.get("EXCLUDE.FILES", []) == []
    assert config.get("SCRUB_HYPHENATED_UUIDS", True) is True
    log_output = log_stream.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in log_output
    stdout_output = stdout_capture.getvalue()
    assert f"Using custom config path: {config_path.resolve()}" in stdout_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_missing_file(clean_cwd):
    """Test loading a non-existent config file."""
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
    stderr_output = stderr_capture.getvalue()
    assert f"Custom config path '{config_path.resolve()}' does not exist" in stderr_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_load_config_namespace_variants(sample_config_content, clean_cwd, monkeypatch):
    """Test loading configuration with different namespaces (prepdir, applydir, vibedir)."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    namespaces = ["prepdir", "applydir", "vibedir"]
    home_dir = Path("home")
    home_dir.mkdir()

    for namespace in namespaces:
        home_config_path = home_dir / f".{namespace}" / "config.yaml"
        home_config_path.parent.mkdir(parents=True, exist_ok=True)
        home_config = sample_config_content.copy()
        home_config["REPLACEMENT_UUID"] = f"11111111-{namespace}-1111-1111-111111111111"
        home_config_path.write_text(yaml.safe_dump(home_config))
        show_config_lines(home_config_path, f"{namespace}_home_config")

        local_config_path = Path(f".{namespace}") / "config.yaml"
        local_config_path.parent.mkdir(parents=True, exist_ok=True)
        local_config = sample_config_content.copy()
        local_config["REPLACEMENT_UUID"] = f"22222222-{namespace}-2222-2222-222222222222"
        local_config_path.write_text(yaml.safe_dump(local_config))
        show_config_lines(local_config_path, f"{namespace}_local_config")

        custom_config_path = Path(f"{namespace}_custom.yaml")
        custom_config = sample_config_content.copy()
        custom_config["REPLACEMENT_UUID"] = f"33333333-{namespace}-3333-3333-333333333333"
        custom_config_path.write_text(yaml.safe_dump(custom_config))
        show_config_lines(custom_config_path, f"{namespace}_custom_config")

        if namespace == "prepdir":
            bundled_path = Path("src") / namespace / "config.yaml"
            bundled_path.parent.mkdir(parents=True)
            bundled_config = sample_config_content.copy()
            bundled_config["REPLACEMENT_UUID"] = f"00000000-{namespace}-0000-0000-000000000000"
            bundled_path.write_text(yaml.safe_dump(bundled_config))
            show_config_lines(bundled_path, f"{namespace}_bundled_config")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "false")

    for namespace in namespaces:
        mock_files = MagicMock()
        mock_resource = MagicMock()
        if namespace == "prepdir":
            mock_resource.__str__.return_value = str(Path("src") / namespace / "config.yaml")
            mock_file = Mock()
            mock_file.read.return_value = (Path("src") / namespace / "config.yaml").read_text(encoding="utf-8")
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_context.__exit__.return_value = None
            mock_resource.open.return_value = mock_context
        mock_files.__truediv__.return_value = mock_resource

        stdout_capture = StringIO()
        stderr_capture = StringIO()
        with patch("prepdir.config.files", return_value=mock_files):
            with patch("prepdir.config.is_resource", return_value=(namespace == "prepdir")):
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        config = load_config(namespace, str(Path(f"{namespace}_custom.yaml")), quiet=False)
                        assert config.get("REPLACEMENT_UUID") == f"33333333-{namespace}-3333-3333-333333333333"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                        log_output = log_stream.getvalue()
                        assert f"Using custom config path: {Path(f'{namespace}_custom.yaml').resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Using custom config path: {Path(f'{namespace}_custom.yaml').resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        config = load_config(namespace, quiet=False)
                        assert config.get("REPLACEMENT_UUID") == f"22222222-{namespace}-2222-2222-222222222222"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                        log_output = log_stream.getvalue()
                        assert f"Found local config: {(Path(f'.{namespace}') / 'config.yaml').resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Found local config: {(Path(f'.{namespace}') / 'config.yaml').resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        (Path(f".{namespace}") / "config.yaml").unlink()
                        config = load_config(namespace, quiet=False)
                        assert config.get("REPLACEMENT_UUID") == f"11111111-{namespace}-1111-1111-111111111111"
                        assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                        log_output = log_stream.getvalue()
                        assert f"Found home config: {(home_dir / f'.{namespace}' / 'config.yaml').resolve()}" in log_output
                        stdout_output = stdout_capture.getvalue()
                        assert f"Found home config: {(home_dir / f'.{namespace}' / 'config.yaml').resolve()}" in stdout_output
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

                        (home_dir / f".{namespace}" / "config.yaml").unlink()
                        config = load_config(namespace, quiet=False)
                        if namespace == "prepdir":
                            assert config.get("REPLACEMENT_UUID") == f"00000000-{namespace}-0000-0000-000000000000"
                            assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                            log_output = log_stream.getvalue()
                            assert "_prepdir_bundled_config.yaml" in log_output
                            assert "Attempting to load bundled config" in log_output
                            stdout_output = stdout_capture.getvalue()
                            assert "Will use default config" in stdout_output
                        else:
                            assert config.get("REPLACEMENT_UUID", None) is None
                            assert config.get("SCRUB_HYPHENATED_UUIDS", None) is None
                            log_output = log_stream.getvalue()
                            assert f"No bundled config found for {namespace}, using defaults" in log_output
                            stdout_output = stdout_capture.getvalue()
                            assert "Will use default config" not in stdout_output

                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)
                        log_stream.truncate(0)
                        log_stream.seek(0)

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_init_config_existing_file_no_force(sample_config_content, clean_cwd):
    """Test init_config raises SystemExit when config file exists and force=False."""
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
    stderr_output = stderr_capture.getvalue()
    assert f"Error: Config file '{config_path}' already exists. Use force=True to overwrite" in stderr_output.strip()
    log_output = log_stream.getvalue()
    assert f"Config file '{config_path}' already exists. Use force=True to overwrite" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_init_config_force_overwrite(sample_config_content, clean_cwd):
    """Test init_config with force=True overwrites existing config file using a bundled config."""
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

    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding="utf-8")
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
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

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_init_config_permission_error(sample_config_content, clean_cwd):
    """Test init_config with permission error when writing config file."""
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

    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding="utf-8")
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource

    stdout_capture = StringIO()
    stderr_capture = StringIO()
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch("pathlib.Path.open", side_effect=PermissionError("Permission denied")):
                with patch('sys.stdout', new=stdout_capture):
                    with patch('sys.stderr', new=stderr_capture):
                        with pytest.raises(SystemExit, match="Failed to create config file"):
                            init_config(namespace="prepdir", config_path=str(config_path), force=True)
    stderr_output = stderr_capture.getvalue()
    assert f"Error: Failed to create config file '{config_path}'" in stderr_output
    log_output = log_stream.getvalue()
    assert f"Failed to create config file '{config_path}'" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_init_config_missing_bundled(clean_cwd):
    """Test init_config with missing bundled config."""
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
                with pytest.raises(SystemExit, match="No bundled config found"):
                    init_config(namespace="prepdir", config_path=str(config_path), force=True)
    stderr_output = stderr_capture.getvalue()
    assert f"Error: No bundled config found for prepdir" in stderr_output
    log_output = log_stream.getvalue()
    assert "No bundled config found for prepdir, cannot initialize" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_init_config_invalid_directory(clean_cwd):
    """Test init_config with invalid directory path."""
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
    stderr_output = stderr_capture.getvalue()
    assert f"Error: Failed to create config file '{config_path}'" in stderr_output
    log_output = log_stream.getvalue()
    assert f"Failed to create config file '{config_path}'" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()

def test_version_package_not_found(clean_cwd):
    """Test __version__ assignment when package is not found."""
    logger.handlers.clear()
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Remove prepdir.config from sys.modules to ensure fresh import
    if "prepdir.config" in sys.modules:
        del sys.modules["prepdir.config"]

    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        import importlib
        import prepdir.config
        importlib.reload(prepdir.config)
        from prepdir.config import __version__
    assert __version__ == "0.0.0"
    log_output = log_stream.getvalue()
    assert "Failed to load package version" in log_output

    logger.removeHandler(handler)
    logger.handlers.clear()

if __name__ == "__main__":
    pytest.main([__file__])