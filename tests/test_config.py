import sys
import os
import yaml
import pytest
import logging
from io import StringIO
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from dynaconf import Dynaconf
from prepdir.config import load_config

@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set TEST_ENV=true for all tests to skip real config loading."""
    monkeypatch.setenv("TEST_ENV", "true")

@pytest.fixture
def sample_config_content():
    """Provide sample configuration content."""
    return {
        "EXCLUDE": {
            "DIRECTORIES": [".git", "__pycache__"],
            "FILES": ["*.pyc", "*.log"],
        },
        "SCRUB_UUIDS": True,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000",
    }

@pytest.fixture
def capture_log():
    """Capture log output during tests."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("prepdir.config")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield log_stream
    logger.removeHandler(handler)

@pytest.fixture
def clean_cwd(tmp_path):
    """Change working directory to a clean temporary path to avoid loading real configs."""
    original_cwd = os.getcwd()
    prepdir_path = tmp_path / ".prepdir"
    if prepdir_path.exists():
        import shutil
        shutil.rmtree(prepdir_path)
    os.chdir(tmp_path)
    yield
    os.chdir(original_cwd)

def test_load_config_local(sample_config_content, capture_log, tmp_path, clean_cwd):
    """Test loading local configuration from .prepdir/config.yaml."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    
    with patch.dict(os.environ, {"TEST_ENV": "true"}):
        config = load_config("prepdir", str(config_path))
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE", {}).get("FILES", []) == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("SCRUB_UUIDS", True) == sample_config_content["SCRUB_UUIDS"]
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == sample_config_content["REPLACEMENT_UUID"]
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['{config_path}']" in log_output
    assert "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files" in log_output

def test_load_config_home(sample_config_content, capture_log, tmp_path, monkeypatch, clean_cwd):
    """Test loading configuration from ~/.prepdir/config.yaml."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = home_dir / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    
    monkeypatch.setenv("HOME", str(home_dir))
    with patch.dict(os.environ, {"TEST_ENV": "false"}):
        config = load_config("prepdir")
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE", {}).get("FILES", []) == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("SCRUB_UUIDS", True) is sample_config_content["SCRUB_UUIDS"]
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == sample_config_content["REPLACEMENT_UUID"]
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['{config_path}']" in log_output
    assert f"Found home config: {config_path}" in log_output

def test_load_config_bundled(capture_log, tmp_path, clean_cwd):
    """Test loading bundled configuration."""
    bundled_path = tmp_path / "src" / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_config_content = {
        "EXCLUDE": {
            "DIRECTORIES": ["bundled_dir"],
            "FILES": ["*.py"],
        },
        "SCRUB_UUIDS": False,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111",
    }
    bundled_path.write_text(yaml.safe_dump(bundled_config_content))
    
    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding='utf-8')
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource
    
    with patch("prepdir.config.files", return_value=mock_files):
        with patch.dict(os.environ, {"TEST_ENV": "false"}):
            config = load_config("prepdir")
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == ["bundled_dir"]
    assert config.get("EXCLUDE", {}).get("FILES", []) == ["*.py"]
    assert config.get("SCRUB_UUIDS", True) is False
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == "11111111-1111-1111-1111-111111111111"
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['/tmp/prepdir_bundled_config.yaml']" in log_output
    assert f"Attempting to load bundled config from: {bundled_path}" in log_output

def test_load_config_bundled_missing(capture_log, tmp_path, clean_cwd):
    """Test handling missing bundled config."""
    with patch("prepdir.config.files", side_effect=Exception("Resource error")):
        with patch.dict(os.environ, {"TEST_ENV": "true"}):
            config = load_config("prepdir")
    
    assert isinstance(config, Dynaconf)
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == []
    assert config.get("EXCLUDE", {}).get("FILES", []) == []
    assert config.get("SCRUB_UUIDS", True) is True
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == "00000000-0000-0000-0000-000000000000"
    
    log_output = capture_log.getvalue()
    assert "Failed to load bundled config for prepdir: Resource error" not in log_output
    assert f"Attempted config files for prepdir: []" in log_output
    assert "Skipping default config files due to TEST_ENV=true" in log_output
    assert "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files" in log_output

def test_load_config_bundled_failure(capture_log, tmp_path, clean_cwd):
    """Test failure to load bundled config logs warning."""
    with patch("prepdir.config.files", side_effect=Exception("Resource not found")):
        with patch.dict(os.environ, {"TEST_ENV": "false"}):
            config = load_config("prepdir")
    assert isinstance(config, Dynaconf)
    log_output = capture_log.getvalue()
    assert "Failed to load bundled config for prepdir: Resource not found" in log_output

def test_load_config_custom_path_excludes_bundled(sample_config_content, capture_log, tmp_path, clean_cwd):
    """Test that a custom config path excludes the bundled config."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    
    with patch("prepdir.config.files") as mock_files:
        with patch.dict(os.environ, {"TEST_ENV": "true"}):
            config = load_config("prepdir", str(config_path))
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == sample_config_content["EXCLUDE"]["DIRECTORIES"]
    assert config.get("EXCLUDE", {}).get("FILES", []) == sample_config_content["EXCLUDE"]["FILES"]
    assert config.get("SCRUB_UUIDS", True) == sample_config_content["SCRUB_UUIDS"]
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == sample_config_content["REPLACEMENT_UUID"]
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['{config_path}']" in log_output
    assert "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files" in log_output
    mock_files.assert_not_called()

def test_load_config_ignore_real_configs(sample_config_content, capture_log, tmp_path, clean_cwd):
    """Test that real config files are ignored when TEST_ENV=true."""
    real_config_path = tmp_path / ".prepdir" / "config.yaml"
    real_config_path.parent.mkdir()
    real_config_path.write_text(yaml.safe_dump(sample_config_content))
    
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    home_config_path = home_dir / ".prepdir" / "config.yaml"
    home_config_path.parent.mkdir()
    home_config_path.write_text(yaml.safe_dump(sample_config_content))
    
    with patch.dict(os.environ, {"HOME": str(home_dir), "TEST_ENV": "true"}):
        config = load_config("prepdir")
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == []
    assert config.get("EXCLUDE", {}).get("FILES", []) == []
    assert config.get("SCRUB_UUIDS", True) is True
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == "00000000-0000-0000-0000-000000000000"
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: []" in log_output
    assert "Skipping default config files due to TEST_ENV=true" in log_output
    assert "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files" in log_output

def test_config_precedence(sample_config_content, capture_log, tmp_path, monkeypatch, clean_cwd):
    """Test configuration precedence: custom > local > global > bundled using non-list fields."""
    bundled_config = {
        "EXCLUDE": {"DIRECTORIES": ["bundled_dir"], "FILES": ["bundled_file"]},
        "SCRUB_UUIDS": False,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
    }
    bundled_path = tmp_path / "src" / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text(yaml.safe_dump(bundled_config))
    
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config = {
        "EXCLUDE": {"DIRECTORIES": ["global_dir"], "FILES": ["global_file"]},
        "SCRUB_UUIDS": True,
        "REPLACEMENT_UUID": "11111111-1111-1111-1111-111111111111"
    }
    global_config_path.write_text(yaml.safe_dump(global_config))
    
    local_config_path = tmp_path / ".prepdir" / "config.yaml"
    local_config_path.parent.mkdir()
    local_config = {
        "EXCLUDE": {"DIRECTORIES": ["local_dir"], "FILES": ["local_file"]},
        "SCRUB_UUIDS": False,
        "REPLACEMENT_UUID": "22222222-2222-2222-2222-222222222222"
    }
    local_config_path.write_text(yaml.safe_dump(local_config))
    
    custom_config_path = tmp_path / "custom.yaml"
    custom_config = {
        "EXCLUDE": {"DIRECTORIES": ["custom_dir"], "FILES": ["custom_file"]},
        "SCRUB_UUIDS": True,
        "REPLACEMENT_UUID": "33333333-3333-3333-3333-333333333333"
    }
    custom_config_path.write_text(yaml.safe_dump(custom_config))
    
    mock_files = MagicMock()
    mock_resource = MagicMock()
    mock_resource.__str__.return_value = str(bundled_path)
    mock_file = Mock()
    mock_file.read.return_value = bundled_path.read_text(encoding='utf-8')
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_file
    mock_context.__exit__.return_value = None
    mock_resource.open.return_value = mock_context
    mock_files.__truediv__.return_value = mock_resource
    with patch("prepdir.config.files", return_value=mock_files):
        with patch.dict(os.environ, {"HOME": str(home_dir), "TEST_ENV": "false"}):
            config = load_config("prepdir", str(custom_config_path))
            assert config.get("SCRUB_UUIDS") is True
            assert config.get("REPLACEMENT_UUID") == "33333333-3333-3333-3333-333333333333"
            
            config = load_config("prepdir")
            assert config.get("SCRUB_UUIDS") is False
            assert config.get("REPLACEMENT_UUID") == "22222222-2222-2222-2222-222222222222"
            
            local_config_path.unlink()
            config = load_config("prepdir")
            assert config.get("SCRUB_UUIDS") is True
            assert config.get("REPLACEMENT_UUID") == "11111111-1111-1111-1111-111111111111"
            
            global_config_path.unlink()
            with open(bundled_path, 'r') as f:
                bundled_config_content = yaml.safe_load(f)
            config = load_config("prepdir")
            assert config.get("SCRUB_UUIDS") is False
            assert config.get("REPLACEMENT_UUID") == "00000000-0000-0000-0000-000000000000"

def test_load_config_invalid_yaml(tmp_path, capture_log, clean_cwd):
    """Test loading a config with invalid YAML raises an error and logs."""
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("invalid: yaml: : :")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config("prepdir", str(config_path))
    log_output = capture_log.getvalue()
    assert f"Using custom config path: {config_path}" in log_output
    assert "Invalid YAML in config file(s)" in log_output

def test_load_config_empty_yaml(tmp_path, capture_log, clean_cwd):
    """Test loading an empty YAML config file."""
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("")
    config = load_config("prepdir", str(config_path))
    assert config.get("EXCLUDE.DIRECTORIES", []) == []
    assert config.get("EXCLUDE.FILES", []) == []
    assert config.get("SCRUB_UUIDS", True) is True
    log_output = capture_log.getvalue()
    assert f"Using custom config path: {config_path}" in log_output

def test_load_config_missing_file(tmp_path, capture_log, clean_cwd):
    """Test loading a non-existent config file."""
    config_path = tmp_path / "nonexistent.yaml"
    config = load_config("prepdir", str(config_path))
    assert config.get("EXCLUDE.DIRECTORIES", []) == []
    assert config.get("EXCLUDE.FILES", []) == []
    assert config.get("SCRUB_UUIDS", True) is True
    log_output = capture_log.getvalue()
    assert f"Using custom config path: {config_path}" in log_output