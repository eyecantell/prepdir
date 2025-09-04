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

def test_traverse_specific_files(temp_dir, config_path, caplog):
    """Test traversal of specific files."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py", "nonexistent.txt", "logs"],
        config_path=config_path,
    )
    with caplog.at_level(logging.INFO):
        caplog.clear()
        files = list(processor._traverse_specific_files())
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "File 'nonexistent.txt' does not exist" in caplog.text
    assert "'logs' is not a file" in caplog.text

def test_traverse_specific_files_permission_error(temp_dir, config_path, caplog):
    """Test _traverse_specific_files with permission error."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py"],
        config_path=config_path,
    )
    with patch("pathlib.Path.resolve", side_effect=PermissionError("Permission denied")):
        with caplog.at_level(logging.INFO):
            caplog.clear()
            files = list(processor._traverse_specific_files())
    assert len(files) == 0
    assert "Permission denied accessing 'file1.py'" in caplog.text

def test_traverse_specific_files_exclusions(temp_dir, config_path, caplog):
    """Test _traverse_specific_files with excluded files and directories."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file2.txt", "logs/app.log"],
        config_path=config_path,
    )
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        files = list(processor._traverse_specific_files())
    assert len(files) == 0
    assert "Skipping file 'file2.txt' (excluded in config)" in caplog.text
    assert "Skipping file 'logs/app.log' (parent directory excluded)" in caplog.text

def test_traverse_directory_specific_extension(temp_dir, config_path, caplog):
    """Test directory traversal with a specific extension (.py) set."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    logging.getLogger("prepdir").setLevel(logging.DEBUG)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
    )
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        files = list(processor._traverse_directory())
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "Skipping file: file2.txt (extension not in ['py'])" in caplog.text
    assert "Skipping file: output.txt (extension not in ['py'])" in caplog.text
    assert "Directory component 'logs' in logs matched exclusion pattern" in caplog.text

def test_traverse_directory_ignore_exclusions(temp_dir, config_path, caplog):
    """Test directory traversal with ignore exclusions set."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt", "log"],
        ignore_exclusions=True,
        include_prepdir_files=False,
        config_path=config_path,
    )
    with caplog.at_level(logging.INFO):
        caplog.clear()
        files = list(processor._traverse_directory())
    assert len(files) == 3  # file1.py, file2.txt, logs/app.log
    assert temp_dir / "file1.py" in files
    assert temp_dir / "file2.txt" in files
    assert temp_dir / "logs" / "app.log" in files
    assert temp_dir / "output.txt" not in files
    assert "Skipping file: output.txt (excluded output file)" in caplog.text

def test_traverse_directory_permission_error(temp_dir, config_path, caplog):
    """Test _traverse_directory with permission error."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
    )
    with patch("os.walk", side_effect=PermissionError("Permission denied")):
        with caplog.at_level(logging.INFO):
            caplog.clear()
            files = list(processor._traverse_directory())
    assert len(files) == 0
    assert "Permission denied traversing directory" in caplog.text