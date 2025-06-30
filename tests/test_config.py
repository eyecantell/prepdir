import sys
import os
import yaml
import pytest
import logging
from io import StringIO
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from dynaconf import Dynaconf
from prepdir.config import load_config, check_namespace_value

# Set up logging for capturing output
logger = logging.getLogger("prepdir.config")
logger.setLevel(logging.DEBUG)

@pytest.fixture
def capture_log():
    """Capture log output during tests."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)
    yield log_stream
    logger.removeHandler(handler)

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
        "VERBOSE": False,
    }

def show_config_lines(config_file_path: str, name: str = "Test"):
    """Print config file contents for debugging."""
    with open(config_file_path, "r") as f:
        config_lines = f.read()
    print(f"{name} config lines in '{config_file_path}':\n--\n{config_lines}\n--\n")

def test_check_namespace_value():
    """Test namespace validation."""
    check_namespace_value("prepdir")
    check_namespace_value("applydir")
    check_namespace_value("vibedir_123")
    with pytest.raises(ValueError, match="Invalid namespace '': must be non-empty"):
        check_namespace_value("")
    with pytest.raises(ValueError, match="Invalid namespace 'invalid@name': must be non-empty"):
        check_namespace_value("invalid@name")

def test_load_config_from_specific_path(sample_config_content, capture_log, tmp_path, clean_cwd):
    """Test loading local configuration from .prepdir/config.yaml."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(config_path)

    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
        config = load_config("prepdir", str(config_path), verbose=True)

    assert config.get("EXCLUDE.DIRECTORIES") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE.FILES") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("REPLACEMENT_UUID") == sample_config_content["REPLACEMENT_UUID"]
    assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("SCRUB_HYPHENLESS_UUIDS") == sample_config_content["SCRUB_HYPHENLESS_UUIDS"]
    assert config.get("VERBOSE") == sample_config_content["VERBOSE"]

    log_output = capture_log.getvalue()
    assert f"Loaded config for prepdir from: ['{config_path}']" in log_output
    assert f"Using custom config path: {config_path}" in log_output
    assert "Loading config with namespace='prepdir'" in log_output
    assert "Final config values for UUIDS:\n" in log_output

def test_load_config_home(sample_config_content, capture_log, tmp_path, monkeypatch, clean_cwd):
    """Test loading configuration from ~/.prepdir/config.yaml."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = home_dir / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(config_path)

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "false")

    config = load_config("prepdir", verbose=True)

    assert config.get("EXCLUDE.DIRECTORIES") == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE.FILES") == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
    assert config.get("REPLACEMENT_UUID") == sample_config_content["REPLACEMENT_UUID"]
    log_output = capture_log.getvalue()
    assert f"Found home config: {config_path}" in log_output
    assert f"Loaded config for prepdir from: ['{config_path}']" in log_output
    assert "Loading config with namespace='prepdir'" in log_output

def test_load_config_bundled(capture_log, tmp_path, clean_cwd):
    """Test loading bundled configuration."""
    bundled_path = tmp_path / "src" / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_config_content = {
        "EXCLUDE": {"DIRECTORIES": ["bundled_dir"], "FILES": ["*.py"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111",
        "VERBOSE": True,
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
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
                config = load_config("prepdir", verbose=True)
    assert config.get("EXCLUDE.DIRECTORIES") == ["bundled_dir"]
    assert config.get("EXCLUDE.FILES") == ["*.py"]
    assert config.get("SCRUB_HYPHENATED_UUIDS") is False
    assert config.get("REPLACEMENT_UUID") == "11111111-1111-1111-1111-111111111111"
    assert config.get("VERBOSE") is True
    log_output = capture_log.getvalue()
    assert "_prepdir_bundled_config.yaml" in log_output
    assert "Attempting to load bundled config" in log_output
    assert "Loaded config for prepdir" in log_output
    assert "Loading config with namespace='prepdir'" in log_output
    assert "Final config values for UUIDS:\n" in log_output

def test_load_config_bundled_missing(capture_log, tmp_path, clean_cwd):
    """Test handling missing bundled config."""
    with patch("prepdir.config.is_resource", return_value=False):
        with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
            config = load_config("prepdir", verbose=True)
    assert config.get("REPLACEMENT_UUID", None) is None
    assert config.get("SCRUB_HYPHENATED_UUIDS", None) is None
    log_output = capture_log.getvalue()
    assert "No bundled config found for prepdir, using defaults" in log_output
    assert "Loading config with namespace='prepdir'" in log_output

def test_load_config_bundled_failure(capture_log, tmp_path, clean_cwd):
    """Test failure to load bundled config logs warning."""
    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(tmp_path / "nonexistent.yaml")
    mock_files.__truediv__.return_value = mock_resource
    with patch("prepdir.config.files", return_value=mock_files):
        with patch("prepdir.config.is_resource", return_value=True):
            with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
                with pytest.raises(ValueError, match="Failed to load bundled config for prepdir"):
                    load_config("prepdir", verbose=True)
    log_output = capture_log.getvalue()
    assert "Failed to load bundled config for prepdir" in log_output

def test_load_config_ignore_real_configs(sample_config_content, capture_log, tmp_path, monkeypatch, clean_cwd):
    """Test that real config files are ignored when PREPDIR_SKIP_CONFIG_LOAD=true."""
    real_config_path = tmp_path / ".prepdir" / "config.yaml"
    real_config_path.parent.mkdir()
    real_config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(real_config_path, "real_config_path")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    home_config_path = home_dir / ".prepdir" / "config.yaml"
    home_config_path.parent.mkdir()
    home_config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(home_config_path, "home_config_path")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "true")

    config = load_config("prepdir", verbose=True)

    log_output = capture_log.getvalue()
    assert "Skipping default config files due to PREPDIR_SKIP_CONFIG_LOAD=true" in log_output
    assert config.get("EXCLUDE.DIRECTORIES", []) == []
    assert config.get("EXCLUDE.FILES", []) == []

def test_config_precedence(sample_config_content, capture_log, tmp_path, monkeypatch, clean_cwd):
    """Test configuration precedence: custom > local > global > bundled using non-list fields."""
    bundled_config = {
        "EXCLUDE": {"DIRECTORIES": ["bundled_dir"], "FILES": ["bundled_file"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "SCRUB_HYPHENLESS_UUIDS": False,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000",
        "VERBOSE": False,
    }
    bundled_path = tmp_path / "src" / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(bundled_config))
    show_config_lines(bundled_path, "bundled_path")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config = {
        "EXCLUDE": {"DIRECTORIES": ["global_dir"], "FILES": ["global_file"]},
        "SCRUB_HYPHENATED_UUIDS": False,
        "SCRUB_HYPHENLESS_UUIDS": True,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111",
        "VERBOSE": True,
    }
    global_config_path.write_text(yaml.safe_dump(global_config))
    show_config_lines(global_config_path, "global_config_path")

    local_config_path = tmp_path / ".prepdir" / "config.yaml"
    local_config_path.parent.mkdir()
    local_config = {
        "EXCLUDE": {"DIRECTORIES": ["local_dir"], "FILES": ["local_file"]},
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": False,
        "REPLACEMENT_UUID": "22222222-2222-2222-2222-222222222222",
        "VERBOSE": False,
    }
    local_config_path.write_text(yaml.safe_dump(local_config))
    show_config_lines(local_config_path, "local_config_path")

    custom_config_path = tmp_path / "custom.yaml"
    custom_config = {
        "EXCLUDE": {"DIRECTORIES": ["custom_dir"], "FILES": ["custom_file"]},
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": True,
        "REPLACEMENT_UUID": "33333333-3333-3333-3333-333333333333",
        "VERBOSE": True,
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
                # First precedence: custom config
                config = load_config("prepdir", str(custom_config_path), verbose=True)
                assert config.get("REPLACEMENT_UUID") == "33333333-3333-3333-3333-333333333333"
                assert config.get("SCRUB_HYPHENATED_UUIDS") is True
                assert config.get("SCRUB_HYPHENLESS_UUIDS") is True
                assert config.get("VERBOSE") is True

                # Second precedence: local .prepdir/config
                config = load_config("prepdir", verbose=True)
                assert config.get("REPLACEMENT_UUID") == "22222222-2222-2222-2222-222222222222"
                assert config.get("SCRUB_HYPHENATED_UUIDS") is True
                assert config.get("SCRUB_HYPHENLESS_UUIDS") is False
                assert config.get("VERBOSE") is False

                # Third precedence: ~/.prepdir/config
                local_config_path.unlink()
                config = load_config("prepdir", verbose=True)
                assert config.get("REPLACEMENT_UUID") == "11111111-1111-1111-1111-111111111111"
                assert config.get("SCRUB_HYPHENATED_UUIDS") is False
                assert config.get("SCRUB_HYPHENLESS_UUIDS") is True
                assert config.get("VERBOSE") is True

                # Last precedence: bundled config
                global_config_path.unlink()
                config = load_config("prepdir", verbose=True)
                assert config.get("REPLACEMENT_UUID") == "00000000-0000-0000-0000-000000000000"
                assert config.get("SCRUB_HYPHENATED_UUIDS") is False
                assert config.get("SCRUB_HYPHENLESS_UUIDS") is False
                assert config.get("VERBOSE") is False

def test_load_config_invalid_yaml(tmp_path, capture_log, clean_cwd):
    """Test loading a config with invalid YAML raises an error and logs."""
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("invalid: yaml: : :")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config("prepdir", str(config_path), verbose=True)
    log_output = capture_log.getvalue()
    assert f"Using custom config path: {config_path}" in log_output
    assert "Invalid YAML in config file(s)" in log_output

def test_load_config_empty_yaml(tmp_path, capture_log, clean_cwd):
    """Test loading an empty YAML config file."""
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("")
    config = load_config("prepdir", str(config_path), verbose=True)
    assert config.get("EXCLUDE.DIRECTORIES", []) == []
    assert config.get("EXCLUDE.FILES", []) == []
    assert config.get("SCRUB_HYPHENATED_UUIDS", True) is True
    assert config.get("VERBOSE", False) is False
    log_output = capture_log.getvalue()
    assert f"Using custom config path: {config_path}" in log_output

def test_load_config_missing_file(tmp_path, capture_log, clean_cwd):
    """Test loading a non-existent config file."""
    config_path = tmp_path / "nonexistent.yaml"
    with pytest.raises(ValueError, match=f"Custom config path '{config_path}' does not exist"):
        load_config("prepdir", str(config_path), verbose=True)

def test_load_config_namespace_variants(sample_config_content, capture_log, tmp_path, monkeypatch, clean_cwd):
    """Test loading configuration with different namespaces (prepdir, applydir, vibedir)."""
    namespaces = ["prepdir", "applydir", "vibedir"]
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    # Create config files for each namespace
    for namespace in namespaces:
        # Home config: ~/.namespace/config.yaml
        home_config_path = home_dir / f".{namespace}" / "config.yaml"
        home_config_path.parent.mkdir(parents=True, exist_ok=True)
        home_config = sample_config_content.copy()
        home_config["REPLACEMENT_UUID"] = f"11111111-{namespace}-1111-1111-111111111111"
        home_config_path.write_text(yaml.safe_dump(home_config))
        show_config_lines(home_config_path, f"{namespace}_home_config")

        # Local config: .namespace/config.yaml
        local_config_path = tmp_path / f".{namespace}" / "config.yaml"
        local_config_path.parent.mkdir(parents=True, exist_ok=True)
        local_config = sample_config_content.copy()
        local_config["REPLACEMENT_UUID"] = f"22222222-{namespace}-2222-2222-222222222222"
        local_config_path.write_text(yaml.safe_dump(local_config))
        show_config_lines(local_config_path, f"{namespace}_local_config")

        # Custom config
        custom_config_path = tmp_path / f"{namespace}_custom.yaml"
        custom_config = sample_config_content.copy()
        custom_config["REPLACEMENT_UUID"] = f"33333333-{namespace}-3333-3333-333333333333"
        custom_config_path.write_text(yaml.safe_dump(custom_config))
        show_config_lines(custom_config_path, f"{namespace}_custom_config")

        # Bundled config for prepdir only
        if namespace == "prepdir":
            bundled_path = tmp_path / "src" / namespace / "config.yaml"
            bundled_path.parent.mkdir(parents=True)
            bundled_config = sample_config_content.copy()
            bundled_config["REPLACEMENT_UUID"] = f"00000000-{namespace}-0000-0000-000000000000"
            bundled_path.write_text(yaml.safe_dump(bundled_config))
            show_config_lines(bundled_path, f"{namespace}_bundled_config")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("PREPDIR_SKIP_CONFIG_LOAD", "false")

    for namespace in namespaces:
        # Mock bundled config existence
        mock_files = MagicMock()
        mock_resource = MagicMock()
        if namespace == "prepdir":
            mock_resource.__str__.return_value = str(tmp_path / "src" / namespace / "config.yaml")
            mock_file = Mock()
            mock_file.read.return_value = (tmp_path / "src" / namespace / "config.yaml").read_text(encoding="utf-8")
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_file
            mock_context.__exit__.return_value = None
            mock_resource.open.return_value = mock_context
        mock_files.__truediv__.return_value = mock_resource

        with patch("prepdir.config.files", return_value=mock_files):
            with patch("prepdir.config.is_resource", return_value=(namespace == "prepdir")):
                # Test custom config
                config = load_config(namespace, str(tmp_path / f"{namespace}_custom.yaml"), verbose=True)
                assert config.get("REPLACEMENT_UUID") == f"33333333-{namespace}-3333-3333-333333333333"
                assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                log_output = capture_log.getvalue()
                assert f"Using custom config path: {tmp_path / f'{namespace}_custom.yaml'}" in log_output
                assert f"Loading config with namespace='{namespace}'" in log_output
                capture_log.truncate(0)
                capture_log.seek(0)

                # Test local config
                config = load_config(namespace, verbose=True)
                assert config.get("REPLACEMENT_UUID") == f"22222222-{namespace}-2222-2222-222222222222"
                assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                log_output = capture_log.getvalue()
                assert f"Found local config: {tmp_path / f'.{namespace}' / 'config.yaml'}" in log_output
                capture_log.truncate(0)
                capture_log.seek(0)

                # Test home config
                (tmp_path / f".{namespace}" / "config.yaml").unlink()
                config = load_config(namespace, verbose=True)
                assert config.get("REPLACEMENT_UUID") == f"11111111-{namespace}-1111-1111-111111111111"
                assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                log_output = capture_log.getvalue()
                assert f"Found home config: {home_dir / f'.{namespace}' / 'config.yaml'}" in log_output
                capture_log.truncate(0)
                capture_log.seek(0)

                # Test bundled config (prepdir) or default (applydir, vibedir)
                (home_dir / f".{namespace}" / "config.yaml").unlink()
                config = load_config(namespace, verbose=True)
                if namespace == "prepdir":
                    assert config.get("REPLACEMENT_UUID") == f"00000000-{namespace}-0000-0000-000000000000"
                    assert config.get("SCRUB_HYPHENATED_UUIDS") == sample_config_content["SCRUB_HYPHENATED_UUIDS"]
                    log_output = capture_log.getvalue()
                    assert "_prepdir_bundled_config.yaml" in log_output
                    assert "Attempting to load bundled config" in log_output
                else:
                    assert config.get("REPLACEMENT_UUID", None) is None
                    assert config.get("SCRUB_HYPHENATED_UUIDS", None) is None
                    log_output = capture_log.getvalue()
                    assert f"No bundled config found for {namespace}, using defaults" in log_output
                capture_log.truncate(0)
                capture_log.seek(0)

def test_load_config_verbose_logging(sample_config_content, capture_log, tmp_path, clean_cwd):
    """Test that verbose=True enables debug logging."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    show_config_lines(config_path)

    # Capture original logging level
    original_level = logger.getEffectiveLevel()

    # Test with verbose=False (no debug logs)
    logger.setLevel(logging.INFO)
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
        config = load_config("prepdir", str(config_path), verbose=False)
    log_output = capture_log.getvalue()
    print(f"verbose=False {log_output=}")
    assert f"Loading config with namespace='prepdir'" not in log_output
    assert f"Using custom config path: {config_path}" not in log_output
    capture_log.truncate(0)
    capture_log.seek(0)

    # Restore original logging level
    logger.setLevel(original_level)

    # Test with verbose=True (debug logs enabled)
    with patch.dict(os.environ, {"PREPDIR_SKIP_CONFIG_LOAD": "false"}):
        config = load_config("prepdir", str(config_path), verbose=True)
    log_output = capture_log.getvalue()
    print(f"verbose=True {log_output=}")
    assert f"Loading config with namespace='prepdir'" in log_output
    assert f"Using custom config path: {config_path}" in log_output
    assert config.get("REPLACEMENT_UUID") == sample_config_content["REPLACEMENT_UUID"]