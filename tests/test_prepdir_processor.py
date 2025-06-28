import pytest
import os
from pathlib import Path
import logging
import tempfile
import dynaconf
from datetime import datetime
from prepdir.prepdir_processor import PrepdirProcessor
from prepdir.prepdir_file_entry import PrepdirFileEntry
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.config import load_config, __version__

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Fixtures
@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with sample files."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.py").write_text(
        'print("Hello")\n# UUID: 123e4567-e89b-12d3-a456-426614174000\n', encoding="utf-8"
    )
    (project_dir / "file2.txt").write_text("Sample text\n", encoding="utf-8")
    (project_dir / "logs").mkdir()
    (project_dir / "logs" / "app.log").write_text("Log entry\n", encoding="utf-8")
    (project_dir / ".git").mkdir()
    (project_dir / "output.txt").write_text(
        f"File listing generated {datetime.now().isoformat()} by prepdir version {__version__}\n"
        f"Base directory is '{project_dir}'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        'print("Hello")\n# UUID: PREPDIR_UUID_PLACEHOLDER_1\n'
        "=-=-= End File: 'file1.py' =-=-=\n",
        encoding="utf-8",
    )
    return project_dir


@pytest.fixture
def config(tmp_path):
    """Create a temporary configuration for tests."""
    os.environ["PREPDIR_SKIP_CONFIG_LOAD"] = "true"
    config = load_config("prepdir")
    config.set("EXCLUDE", {"DIRECTORIES": ["logs", ".git"], "FILES": ["*.txt"]})
    config.set("DEFAULT_EXTENSIONS", ["py", "txt"])
    config.set("DEFAULT_OUTPUT_FILE", "prepped_dir.txt")
    config.set("SCRUB_HYPHENATED_UUIDS", True)
    config.set("SCRUB_HYPHENLESS_UUIDS", True)
    config.set("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000")
    config.set("USE_UNIQUE_PLACEHOLDERS", False)
    config.set("IGNORE_EXCLUSIONS", False)
    config.set("INCLUDE_PREPDIR_FILES", False)
    config.set("VERBOSE", False)
    yield config
    os.environ.pop("PREPDIR_SKIP_CONFIG_LOAD", None)


# Test PrepdirProcessor
def test_init_valid(temp_dir, config):
    """Test initialization with valid parameters."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt"],
        specific_files=None,
        output_file="output.txt",
        config_path=None,
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        use_unique_placeholders=True,
        ignore_exclusions=False,
        include_prepdir_files=False,
        verbose=True,
    )
    assert processor.directory == str(temp_dir.resolve())
    assert processor.extensions == ["py", "txt"]
    assert processor.specific_files == []
    assert processor.output_file == "output.txt"
    assert processor.scrub_hyphenated_uuids is True
    assert processor.scrub_hyphenless_uuids is True
    assert processor.replacement_uuid == "00000000-0000-0000-0000-000000000000"
    assert processor.use_unique_placeholders is True
    assert processor.ignore_exclusions is False
    assert processor.include_prepdir_files is False
    assert processor.verbose is True
    assert isinstance(processor.config, dynaconf.base.LazySettings)
    assert processor.logger is not None


def test_init_invalid_directory(config):
    """Test initialization with invalid directory."""
    with pytest.raises(ValueError, match="Directory '.*' does not exist"):
        PrepdirProcessor(directory="/nonexistent", config_path=None)
    with tempfile.NamedTemporaryFile() as f:
        with pytest.raises(ValueError, match="'/.*' is not a directory"):
            PrepdirProcessor(directory=f.name, config_path=None)


def test_init_invalid_replacement_uuid(temp_dir, config, caplog):
    """Test initialization with invalid replacement UUID."""
    with caplog.at_level(logging.ERROR):
        processor = PrepdirProcessor(
            directory=str(temp_dir),
            replacement_uuid="invalid-uuid",
            config_path=None,
        )
    assert processor.replacement_uuid == config.get("REPLACEMENT_UUID")
    assert "Invalid replacement UUID: 'invalid-uuid'" in caplog.text


def test_load_config(config):
    """Test loading configuration."""
    processor = PrepdirProcessor(directory="/tmp", config_path=None)
    assert processor.config is not None
    assert processor.config.get("EXCLUDE", {}).get("DIRECTORIES", []) == ["logs", ".git"]
    assert processor.config.get("EXCLUDE", {}).get("FILES", []) == ["*.txt"]


def test_is_excluded_dir(temp_dir, config):
    """Test directory exclusion logic."""
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=None)
    processor.config = config
    assert processor.is_excluded_dir("logs", str(temp_dir)) is True
    assert processor.is_excluded_dir(".git", str(temp_dir)) is True
    assert processor.is_excluded_dir("src", str(temp_dir)) is False
    processor.ignore_exclusions = True
    assert processor.is_excluded_dir("logs", str(temp_dir)) is False


def test_is_excluded_file(temp_dir, config):
    """Test file exclusion logic."""
    processor = PrepdirProcessor(directory=str(temp_dir), output_file="output.txt", config_path=None)
    processor.config = config
    assert processor.is_excluded_file("file2.txt", str(temp_dir)) is True
    assert processor.is_excluded_file("output.txt", str(temp_dir)) is True
    assert processor.is_excluded_file("file1.py", str(temp_dir)) is False
    processor.include_prepdir_files = True
    assert processor.is_excluded_file("output.txt", str(temp_dir)) is True  # Still excluded as output file
    processor.ignore_exclusions = True
    assert processor.is_excluded_file("file2.txt", str(temp_dir)) is False


def test_is_excluded_file_io_error(temp_dir, config, caplog):
    """Test is_excluded_file with IOError when checking prepdir format."""
    processor = PrepdirProcessor(directory=str(temp_dir), output_file="output.txt", config_path=None)
    processor.config = config
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        assert processor.is_excluded_file("output.txt", str(temp_dir)) is True  # Excluded as output file
        assert processor.is_excluded_file("file1.py", str(temp_dir)) is False


def test_traverse_specific_files(temp_dir, config, caplog):
    """Test traversal of specific files."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py", "nonexistent.txt", "logs"],
        config_path=None,
        verbose=True,
    )
    processor.config = config
    with caplog.at_level(logging.INFO):
        files = list(processor._traverse_specific_files())
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "File 'nonexistent.txt' does not exist" in caplog.text
    assert "'logs' is not a file" in caplog.text


def test_traverse_directory(temp_dir, config, caplog):
    """Test directory traversal."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=None,
        verbose=True,
    )
    processor.config = config
    with caplog.at_level(logging.INFO):
        files = list(processor._traverse_directory(["logs", ".git"], ["*.txt"]))
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "Skipping file: file2.txt (excluded in config)" in caplog.text
    assert "Skipping file: app.log (excluded in config)" in caplog.text


def test_generate_output_basic(temp_dir, config):
    """Test generating output for a basic project directory."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        use_unique_placeholders=True,
        config_path=None,
        verbose=True,
    )
    processor.config = config
    output = processor.generate_output()
    assert isinstance(output, PrepdirOutputFile)
    assert output.path is None
    assert len(output.files) == 1
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "PREPDIR_UUID_PLACEHOLDER_1" in output.content
    assert "file2.txt" not in output.content
    assert output.metadata["version"] == __version__
    assert output.metadata["base_directory"] == str(temp_dir)
    assert output.uuid_mapping.get("PREPDIR_UUID_PLACEHOLDER_1") == "123e4567-e89b-12d3-a456-426614174000"


def test_generate_output_specific_files(temp_dir, config):
    """Test generating output with specific files."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py"],
        scrub_hyphenated_uuids=True,
        use_unique_placeholders=True,
        config_path=None,
    )
    processor.config = config
    output = processor.generate_output()
    assert len(output.files) == 1
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "PREPDIR_UUID_PLACEHOLDER_1" in output.content


def test_generate_output_empty_directory(tmp_path, config):
    """Test generating output for an empty directory."""
    processor = PrepdirProcessor(directory=str(tmp_path), extensions=["py"], config_path=None)
    processor.config = config
    output = processor.generate_output()
    assert isinstance(output, PrepdirOutputFile)
    assert len(output.files) == 0
    assert "No files found" in output.content
    assert output.uuid_mapping == {}
    assert output.metadata["base_directory"] == str(tmp_path)


def test_generate_output_binary_file(temp_dir, config):
    """Test handling of binary files."""
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\xff\xfe\x00\x01")
    processor = PrepdirProcessor(directory=str(temp_dir), extensions=["bin"], config_path=None)
    processor.config = config
    output = processor.generate_output()
    assert isinstance(output, PrepdirOutputFile)
    assert len(output.files) == 1
    entry = output.files[Path(temp_dir) / "binary.bin"]
    assert entry.is_binary
    assert entry.error is not None
    assert "[Binary file or encoding not supported]" in entry.content


def test_generate_output_exclusions(temp_dir, config):
    """Test file and directory exclusions."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt", "log"],
        config_path=None,
    )
    processor.config = config
    output = processor.generate_output()
    assert len(output.files) == 1  # Only file1.py
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "logs/app.log" not in output.content


def test_generate_output_include_all(temp_dir, config):
    """Test including all files, ignoring exclusions."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt", "log"],
        ignore_exclusions=True,
        config_path=None,
    )
    processor.config = config
    output = processor.generate_output()
    assert len(output.files) == 3  # file1.py, file2.txt, logs/app.log
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" in [entry.relative_path for entry in output.files.values()]
    assert "logs/app.log" in [entry.relative_path for entry in output.files.values()]


def test_generate_output_no_scrubbing(temp_dir, config):
    """Test output without UUID scrubbing."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        config_path=None,
    )
    processor.config = config
    output = processor.generate_output()
    assert "123e4567-e89b-12d3-a456-426614174000" in output.content
    assert not any(entry.is_scrubbed for entry in output.files.values())
    assert output.uuid_mapping == {}


def test_generate_output_non_unique_placeholders(temp_dir, config, caplog):
    """Test generate_output with non-unique placeholders."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        use_unique_placeholders=False,
        config_path=None,
        verbose=True,
    )
    processor.config = config
    with caplog.at_level(logging.INFO):
        output = processor.generate_output()
    assert f"replaced with '{processor.replacement_uuid}'" in output.content
    assert "file1.py" in output.content
    assert "00000000-0000-0000-0000-000000000000" in output.content
    assert not output.uuid_mapping  # Non-unique placeholders don't populate uuid_mapping


def test_validate_output_valid(temp_dir, config):
    """Test validating a valid prepdir output file."""
    output_file = temp_dir / "output.txt"
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=None)
    processor.config = config
    output = processor.validate_output(str(output_file))
    assert isinstance(output, PrepdirOutputFile)
    assert len(output.files) == 1
    assert output.files[Path(temp_dir) / "file1.py"].relative_path == "file1.py"
    assert 'print("Hello")' in output.files[Path(temp_dir) / "file1.py"].content
    assert output.metadata["base_directory"] == str(temp_dir)


def test_validate_output_invalid(tmp_path, config):
    """Test validating an invalid prepdir output file."""
    content = (
        f"File listing generated {datetime.now().isoformat()} by prepdir version {__version__}\n"
        "Base directory is '/test_dir'\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        "print('Hello')\n"
        # Missing footer
    )
    output_file = tmp_path / "output.txt"
    output_file.write_text(content, encoding="utf-8")
    processor = PrepdirProcessor(directory="/test_dir", config_path=None)
    processor.config = config
    with pytest.raises(ValueError, match="Unclosed file 'file1.py'"):
        processor.validate_output(str(output_file))


def test_save_output(temp_dir, config, tmp_path):
    """Test saving output to a file."""
    output_file = tmp_path / "output.txt"
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=None,
    )
    processor.config = config
    output = processor.generate_output()
    processor.save_output(output, str(output_file))
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "file1.py" in content
    assert "file2.txt" not in content
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content


def test_init_config(tmp_path, config, capsys):
    """Test initializing a local config file."""
    config_path = tmp_path / ".prepdir/config.yaml"
    PrepdirProcessor.init_config(str(config_path))
    assert config_path.exists()
    with config_path.open("r", encoding="utf-8") as f:
        content = f.read()
    assert "exclude:" in content
    assert "directories:" in content
    assert "files:" in content
    with pytest.raises(SystemExit):
        PrepdirProcessor.init_config(str(config_path), force=False)
    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_prepdir_processor_uuid_mapping_consistency(temp_dir, config):
    """Test UUID mapping consistency across multiple files."""
    # Add a second file with the same UUID
    (temp_dir / "file3.py").write_text(
        'print("World")\n# UUID: 123e4567-e89b-12d3-a456-426614174000\n', encoding="utf-8"
    )
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        use_unique_placeholders=True,
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        config_path=None,
        verbose=True,
    )
    processor.config = config
    output = processor.generate_output()
    assert len(output.uuid_mapping) == 1, "Should have one UUID mapping"
    placeholder = list(output.uuid_mapping.keys())[0]
    assert output.uuid_mapping[placeholder] == "123e4567-e89b-12d3-a456-426614174000"
    for file_entry in output.files.values():
        assert "123e4567-e89b-12d3-a456-426614174000" not in file_entry.content
        assert placeholder in file_entry.content


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
