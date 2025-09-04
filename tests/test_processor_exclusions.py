import pytest
import yaml
from pathlib import Path
import logging
from prepdir.prepdir_processor import PrepdirProcessor
from prepdir import prepdir_logging
from unittest.mock import patch

logger = logging.getLogger(__name__)

@pytest.fixture
def config_values():
    """Create temporary configuration values for tests."""
    return {
        "EXCLUDE": {
            "DIRECTORIES": ["logs", ".git"],
            "FILES": ["*.txt"],
        },
        "DEFAULT_EXTENSIONS": ["py", "txt"],
        "DEFAULT_OUTPUT_FILE": "prepped_dir.txt",
        "SCRUB_HYPHENATED_UUIDS": True,
        "SCRUB_HYPHENLESS_UUIDS": True,
        "REPLACEMENT_UUID": "1a000000-2b00-3c00-4d00-5e0000000000",
        "USE_UNIQUE_PLACEHOLDERS": False,
        "IGNORE_EXCLUSIONS": False,
        "INCLUDE_PREPDIR_FILES": False,
    }

@pytest.fixture
def config_path(tmp_path, config_values):
    """Create a temporary configuration file for tests."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config_values, f)
    return str(config_path)

def test_is_excluded_dir(temp_dir, config_path):
    """Test directory exclusion logic."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    assert processor.is_excluded_dir("logs", str(temp_dir)) is True
    assert processor.is_excluded_dir(".git", str(temp_dir)) is True
    assert processor.is_excluded_dir("src", str(temp_dir)) is False
    processor.ignore_exclusions = True
    assert processor.is_excluded_dir("logs", str(temp_dir)) is False

def test_is_excluded_file(temp_dir, config_path):
    """Test file exclusion logic."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), output_file="output.txt", config_path=config_path)
    assert processor.is_excluded_file("file2.txt", str(temp_dir)) is True
    assert processor.is_excluded_file("output.txt", str(temp_dir)) is True
    assert processor.is_excluded_file("file1.py", str(temp_dir)) is False
    processor.include_prepdir_files = True
    assert processor.is_excluded_file("output.txt", str(temp_dir)) is True  # Still excluded as output file
    processor.ignore_exclusions = True
    assert processor.is_excluded_file("file2.txt", str(temp_dir)) is False

def test_is_excluded_file_io_error(temp_dir, config_path):
    """Test is_excluded_file with IOError when checking prepdir format."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), output_file="output.txt", config_path=config_path)
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        assert processor.is_excluded_file("output.txt", str(temp_dir)) is True  # Excluded as output file
        assert processor.is_excluded_file("file1.py", str(temp_dir)) is False

def test_is_excluded_output_file_non_prepdir_with_include(temp_dir, config_path):
    """Test is_excluded_output_file with non-prepdir file when include_prepdir_files=True."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        output_file="different_output.txt",
        include_prepdir_files=True,
        config_path=config_path,
    )
    assert processor.is_excluded_output_file("file1.py", str(temp_dir)) is False

def test_is_excluded_output_file_unicode_decode_error(temp_dir, config_path, caplog):
    """Test is_excluded_output_file with UnicodeDecodeError."""
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        output_file="different_output.txt",
        include_prepdir_files=True,
        config_path=config_path,
    )
    with patch("builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")):
        assert processor.is_excluded_output_file("file1.py", str(temp_dir)) is False

def test_is_excluded_output_file_valid_prepdir_file(temp_dir, config_path, caplog):
    """Test is_excluded_output_file with a valid prepdir output file."""
    prepdir_logging.configure_logging(logger, level=logging.DEBUG)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        output_file="different_output.txt",
        include_prepdir_files=False,
        config_path=config_path,
    )
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        assert processor.is_excluded_output_file("output.txt", str(temp_dir)) is True
        assert "Found " + str(temp_dir / "output.txt") + " is an output file" in caplog.text