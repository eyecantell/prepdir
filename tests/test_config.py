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
    with patch.dict(os.environ, {"TEST_ENV": "true"}):
        config = load_config("prepdir")
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == []
    assert config.get("EXCLUDE", {}).get("FILES", []) == []
    assert config.get("SCRUB_UUIDS", True) is True
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == "00000000-0000-0000-0000-000000000000"
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: []" in log_output
    assert "Skipping default config files due to TEST_ENV=true" in log_output
    assert "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files" in log_output

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
    
    # Create mock for resources.files
    mock_files = Mock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = bundled_path.open('r', encoding='utf-8')
    mock_cm.__exit__.return_value = None
    mock_files.joinpath.return_value = mock_cm
    
    # Patch the correct module based on Python version
    patch_target = "importlib_resources.files" if sys.version_info < (3, 9) else "importlib.resources.files"
    with patch(patch_target, return_value=mock_files):
        with patch.dict(os.environ, {"TEST_ENV": "true"}):
            config = load_config("prepdir")
    
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == []
    assert config.get("EXCLUDE", {}).get("FILES", []) == []
    assert config.get("SCRUB_UUIDS", True) is True
    assert config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000") == "00000000-0000-0000-0000-000000000000"
    
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: []" in log_output
    assert "Skipping default config files due to TEST_ENV=true" in log_output
    assert "Skipping bundled config loading due to TEST_ENV=true, custom config_path, or existing config files" in log_output

def test_load_config_bundled_missing(capture_log, tmp_path, clean_cwd):
    """Test handling missing bundled config."""
    # Patch the correct module based on Python version
    patch_target = "importlib_resources.files" if sys.version_info < (3, 9) else "importlib.resources.files"
    with patch(patch_target, side_effect=Exception("Resource error")):
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

def test_load_config_custom_path_excludes_bundled(sample_config_content, capture_log, tmp_path, clean_cwd):
    """Test that a custom config path excludes the bundled config."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(sample_config_content))
    
    # Create mock to ensure bundled config is not accessed
    patch_target = "importlib_resources.files" if sys.version_info < (3, 9) else "importlib.resources.files"
    with patch(patch_target) as mock_files:
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
    # Create a real .prepdir/config.yaml in the test directory
    real_config_path = tmp_path / ".prepdir" / "config.yaml"
    real_config_path.parent.mkdir()
    real_config_path.write_text(yaml.safe_dump(sample_config_content))
    
    # Create a real ~/.prepdir/config.yaml
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