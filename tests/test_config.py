import pytest
import sys
from unittest.mock import patch
from pathlib import Path
import logging
from io import StringIO
from dynaconf import Dynaconf
from prepdir.config import load_config
from unittest.mock import MagicMock, Mock, patch

@pytest.fixture
def sample_config_content():
    """Fixture for sample configuration content."""
    return {
        "EXCLUDE": {
            "DIRECTORIES": [".git", "__pycache__"],
            "FILES": ["*.pyc", "*.log"]
        }
    }

@pytest.fixture
def capture_log():
    """Capture logging output."""
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
    yield log_output
    logging.getLogger().handlers = []
    logging.getLogger().setLevel(logging.NOTSET)

def test_load_config_custom_path(sample_config_content, capture_log, tmp_path):
    """Test loading configuration from a custom path."""
    config_path = tmp_path / "custom.yaml"
    config_path.write_text("""
EXCLUDE:
  DIRECTORIES:
    - custom_dir
  FILES:
    - "*.custom"
""")
    config = load_config("prepdir", str(config_path))
    
    assert config.EXCLUDE.DIRECTORIES == ["custom_dir"]
    assert config.EXCLUDE.FILES == ["*.custom"]
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['{config_path}']" in log_output

def test_load_config_local_path(sample_config_content, capture_log, tmp_path):
    """Test loading configuration from .prepdir/config.yaml."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("""
EXCLUDE:
  DIRECTORIES:
    - local_dir
  FILES:
    - "*.local"
""")
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        config = load_config("prepdir", str(config_path))  # Specify config_path to avoid merging
        
    assert config.EXCLUDE.DIRECTORIES == ["local_dir"]
    assert config.EXCLUDE.FILES == ["*.local"]
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['{config_path}']" in log_output

def test_load_config_global_path(sample_config_content, capture_log, tmp_path):
    """Test loading configuration from ~/.prepdir/config.yaml."""
    home_path = tmp_path / "home"
    home_path.mkdir()
    config_path = home_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("""
EXCLUDE:
  DIRECTORIES:
    - global_dir
  FILES:
    - "*.global"
""")
    with patch("pathlib.Path.home", return_value=home_path):
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config = load_config("prepdir", str(config_path))  # Specify config_path to avoid merging
            
    assert config.EXCLUDE.DIRECTORIES == ["global_dir"]
    assert config.EXCLUDE.FILES == ["*.global"]
    log_output = capture_log.getvalue()
    assert f"Attempted config files for prepdir: ['{config_path}']" in log_output

def test_load_config_bundled(sample_config_content, capture_log, tmp_path):
    """Test loading bundled configuration."""
    bundled_path = tmp_path / "src" / "prepdir" / "config.yaml"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("""
EXCLUDE:
  DIRECTORIES:
    - bundled_dir
  FILES:
    - "*.py"
""")
    # Create mock for resources.files
    mock_files = Mock()
    # Create mock for joinpath result (context manager)
    mock_cm = MagicMock()  # Use MagicMock to support __enter__/__exit__
    mock_cm.__enter__.return_value = bundled_path
    mock_cm.__exit__.return_value = None
    # Configure files().joinpath to return the context manager
    mock_files.joinpath.return_value = mock_cm
    # Patch the correct module based on Python version
    patch_target = "importlib_resources.files" if sys.version_info < (3, 9) else "importlib.resources.files"
    with patch(patch_target, return_value=mock_files):
        config = load_config("prepdir")
    
    assert config.EXCLUDE.DIRECTORIES == ["bundled_dir"]
    assert config.EXCLUDE.FILES == ["*.py"]
    log_output = capture_log.getvalue()
    expected_home = Path.home() / ".prepdir" / "config.yaml"
    assert f"Attempted config files for prepdir: ['.prepdir/config.yaml', '{expected_home}', '{bundled_path}']" in log_output

def test_load_config_bundled_missing(capture_log):
    """Test handling missing bundled config."""
    # Patch the correct module based on Python version
    patch_target = "importlib_resources.files" if sys.version_info < (3, 9) else "importlib.resources.files"
    with patch(patch_target, side_effect=Exception("Resource error")):
        config = load_config("prepdir")
    
    assert isinstance(config, Dynaconf)
    assert config.get("EXCLUDE", {}).get("DIRECTORIES", []) == []  # Empty config
    log_output = capture_log.getvalue()
    assert "Failed to load bundled config for prepdir: Resource error" in log_output

def test_load_config_lowercase_keys(sample_config_content, capture_log, tmp_path):
    """Test loading configuration with lowercase keys raises ValueError."""
    config_path = tmp_path / "custom.yaml"
    config_path.write_text("""
exclude:
  directories:
    - custom_dir
  files:
    - "*.custom"
""")
    with pytest.raises(ValueError) as exc_info:
        load_config("prepdir", str(config_path))
    
    assert "Lowercase configuration keys ['exclude'] found in" in str(exc_info.value)
    assert "Starting with version 0.10.0, prepdir requires uppercase keys" in str(exc_info.value)
    assert "See https://github.com/eyecantell/prepdir#configuration for details" in str(exc_info.value)