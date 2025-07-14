import pytest
import yaml
from pathlib import Path
import logging
import tempfile
import dynaconf
from datetime import datetime
from io import StringIO
from prepdir.prepdir_processor import PrepdirProcessor
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.prepdir_file_entry import BINARY_CONTENT_PLACEHOLDER
from prepdir.config import __version__
from prepdir import prepdir_logging
from unittest.mock import patch

logger = logging.getLogger(__name__)


# Fixtures
@pytest.fixture(autouse=True)
def reset_logger():
    """Reset logger state before and after each test."""
    for name in ["prepdir.prepdir_processor", "prepdir.prepdir_output_file", "prepdir.prepdir_file_entry", __name__]:
        log = logging.getLogger(name)
        log.handlers.clear()
        log.setLevel(logging.NOTSET)
        log.propagate = True  # Ensure propagation is enabled during tests
    yield
    for name in ["prepdir.prepdir_processor", "prepdir.prepdir_output_file", "prepdir.prepdir_file_entry", __name__]:
        log = logging.getLogger(name)
        log.handlers.clear()
        log.setLevel(logging.NOTSET)
        log.propagate = True


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
        'print("Hello")\n'
        "# UUID: PREPDIR_UUID_PLACEHOLDER_1\n"
        "=-=-= End File: 'file1.py' =-=-=\n",
        encoding="utf-8",
    )
    return project_dir


@pytest.fixture
def config_values():
    """Create temporary configuration values for tests."""
    yield {
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
    yield str(config_path)


# Test PrepdirProcessor
def test_init_valid(temp_dir, config_path):
    """Test initialization with valid parameters."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt"],
        specific_files=None,
        output_file="output.txt",
        config_path=config_path,
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
        use_unique_placeholders=True,
        ignore_exclusions=False,
        include_prepdir_files=False,
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
    assert isinstance(processor.config, dynaconf.base.LazySettings)
    assert processor.logger is not None
    assert len(logger.handlers) == 2
    assert logger.handlers[0].level == logging.DEBUG
    assert logger.handlers[1].level == logging.WARNING


def test_init_invalid_directory(config_path):
    """Test initialization with invalid directory."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    with pytest.raises(ValueError, match="Directory '.*' does not exist"):
        PrepdirProcessor(directory="/nonexistent", config_path=config_path)
    with tempfile.NamedTemporaryFile() as f:
        with pytest.raises(ValueError, match="'/.*' is not a directory"):
            PrepdirProcessor(directory=f.name, config_path=config_path)


def test_init_invalid_replacement_uuid(temp_dir, config_path, config_values, caplog):
    """Test initialization with invalid replacement UUID."""

    prepdir_logging.configure_logging(logger, level=logging.ERROR)
    with caplog.at_level(logging.ERROR):
        caplog.clear()
        processor = PrepdirProcessor(
            directory=str(temp_dir),
            replacement_uuid="invalid-uuid",
            config_path=config_path,
        )
    print(f"caplog text is:\n{caplog.text}")
    assert processor.replacement_uuid == config_values.get("REPLACEMENT_UUID")
    assert "Invalid replacement UUID: 'invalid-uuid'" in caplog.text


def test_load_config(config_path, config_values):
    """Test loading configuration."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory="/tmp", config_path=config_path)
    assert processor.config is not None
    assert processor.config.get("EXCLUDE.DIRECTORIES", []) == config_values.get("EXCLUDE", {}).get("DIRECTORIES")
    assert processor.config.get("EXCLUDE.FILES", []) == config_values.get("EXCLUDE", {}).get("FILES")


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


def test_traverse_directory_specific_extension(temp_dir, config_path, caplog):
    """Test directory traversal with a specific extension (.py) set."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
    )
    with caplog.at_level(logging.INFO):
        caplog.clear()
        files = list(processor._traverse_directory())
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "Skipping file: file2.txt (extension not in ['py'])" in caplog.text
    assert "Skipping file: app.log (extension not in ['py'])" in caplog.text


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

    print(f"caplog text is:\n{caplog.text}\n--")
    assert len(files) == 3  # file1.py, file2.txt, logs/app.log
    assert temp_dir / "file1.py" in files
    assert temp_dir / "file2.txt" in files
    assert temp_dir / "logs" / "app.log" in files
    assert temp_dir / "output.txt" not in files  # Still excluded as output file
    assert "Skipping file: output.txt (excluded output file)" in caplog.text


def test_generate_output_basic(temp_dir, config_path, config_values):
    """Test generating output for a basic project directory."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        use_unique_placeholders=True,
        config_path=config_path,
    )
    output = processor.generate_output()
    assert isinstance(output, PrepdirOutputFile)
    assert output.path == Path(config_values.get("DEFAULT_OUTPUT_FILE", "prepped_dir.txt"))
    assert len(output.files) == 1
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "PREPDIR_UUID_PLACEHOLDER_1" in output.content
    assert "file2.txt" not in output.content
    assert output.metadata["version"] == __version__
    assert output.metadata["base_directory"] == str(temp_dir)
    assert output.uuid_mapping.get("PREPDIR_UUID_PLACEHOLDER_1") == "123e4567-e89b-12d3-a456-426614174000"


def test_generate_output_specific_files(temp_dir, config_path):
    """Test generating output with specific files."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py"],
        scrub_hyphenated_uuids=True,
        use_unique_placeholders=True,
        config_path=config_path,
    )
    output = processor.generate_output()
    assert len(output.files) == 1
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "PREPDIR_UUID_PLACEHOLDER_1" in output.content


def test_generate_output_empty_directory(tmp_path, config_path):
    """Test generating output for an empty directory."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(tmp_path), extensions=["py"], config_path=config_path)
    with pytest.raises(ValueError, match="No files found!"):
        processor.generate_output()


def test_generate_output_binary_file(temp_dir, config_path):
    """Test handling of binary files."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\xff\xfe\x00\x01")
    processor = PrepdirProcessor(directory=str(temp_dir), extensions=["bin"], config_path=config_path)
    output = processor.generate_output()
    assert isinstance(output, PrepdirOutputFile)
    assert len(output.files) == 1
    entry = output.files[Path(temp_dir) / "binary.bin"]
    assert entry is not None
    assert entry.is_binary
    assert entry.error is None
    assert BINARY_CONTENT_PLACEHOLDER in entry.content


def test_generate_output_exclusions(temp_dir, config_path):
    """Test file and directory exclusions."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        config_path=config_path,
    )
    output = processor.generate_output()
    assert len(output.files) == 1  # Only file1.py
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "logs/app.log" not in output.content


def test_generate_output_exclusions_with_extensions(temp_dir, config_path):
    """Test file and directory exclusions when extensions are specified."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        config_path=config_path,
        extensions=["py", "txt", "log"],
    )
    output = processor.generate_output()
    assert len(output.files) == 1  # Only file1.py
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "logs/app.log" not in output.content


def test_generate_output_include_all(temp_dir, config_path):
    """Test including all files, ignoring exclusions."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt", "log"],
        ignore_exclusions=True,
        config_path=config_path,
    )
    output = processor.generate_output()
    assert len(output.files) == 3  # file1.py, file2.txt, logs/app.log
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" in [entry.relative_path for entry in output.files.values()]
    assert "logs/app.log" in [entry.relative_path for entry in output.files.values()]


def test_generate_output_no_scrubbing(temp_dir, config_path):
    """Test output without UUID scrubbing."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        config_path=config_path,
    )
    output = processor.generate_output()
    assert "123e4567-e89b-12d3-a456-426614174000" in output.content
    assert not any(entry.is_scrubbed for entry in output.files.values())
    assert output.uuid_mapping == {}


def test_generate_output_non_unique_placeholders(temp_dir, config_path, config_values, caplog):
    """Test generate_output with non-unique placeholders."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        use_unique_placeholders=False,
        config_path=config_path,
    )
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        output = processor.generate_output()

    print(f"caplog text is:\n{caplog.text}\n--")
    print(f"output.content is:\n{output.content}\n--")
    assert f"replaced with '{processor.replacement_uuid}'" in output.content
    assert "file1.py" in output.content
    replacement_uuid = config_values.get("REPLACEMENT_UUID")
    assert replacement_uuid
    assert replacement_uuid in output.content
    assert replacement_uuid in output.uuid_mapping
    assert "Scrubbed UUIDs in file1.py" in caplog.text


def test_validate_output_valid(temp_dir, config_path):
    """Test validating a valid prepdir output file."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    output_file = temp_dir / "output.txt"
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    output = processor.validate_output(file_path=str(output_file))
    assert isinstance(output, PrepdirOutputFile)
    assert len(output.files) == 1
    assert output.files[Path(temp_dir) / "file1.py"].relative_path == "file1.py"
    assert 'print("Hello")' in output.files[Path(temp_dir) / "file1.py"].content
    assert output.metadata["base_directory"] == str(temp_dir)


def test_validate_output_invalid(tmp_path, config_path):
    """Test validating an invalid prepdir output file."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    content = (
        f"File listing generated {datetime.now().isoformat()} by prepdir version {__version__}\n"
        "Base directory is '/test_dir'\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        "print('Hello')\n"
        # Missing footer
    )
    output_file = tmp_path / "output.txt"
    output_file.write_text(content, encoding="utf-8")
    processor = PrepdirProcessor(directory=tmp_path, config_path=config_path)
    with pytest.raises(ValueError, match="Unclosed file 'file1.py'"):
        processor.validate_output(file_path=str(output_file))


def test_save_output(temp_dir, config_path, tmp_path):
    """Test saving output to a file."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir), extensions=["py"], config_path=config_path, use_unique_placeholders=True
    )
    output_file = tmp_path / "prepped_dir.txt"
    assert not output_file.exists()
    output = processor.generate_output()
    processor.save_output(output, str(output_file))
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "file1.py" in content
    assert "file2.txt" not in content
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content


def test_init_config(tmp_path, caplog):
    """Test initializing a local config file."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    config_path = tmp_path / ".prepdir/config.yaml"
    with caplog.at_level(logging.INFO):
        caplog.clear()
        PrepdirProcessor.init_config(str(config_path))
    assert config_path.exists()
    with config_path.open("r", encoding="utf-8") as f:
        content = f.read()
    assert "exclude:" in content.lower()
    assert "directories:" in content.lower()
    assert "files:" in content.lower()
    print(f"caplog text is:\n{caplog.text}\n--")
    assert f"Created '{config_path}' with default configuration." in caplog.text
    with caplog.at_level(logging.ERROR):
        caplog.clear()
        with pytest.raises(SystemExit):
            PrepdirProcessor.init_config(str(config_path), force=False)
    assert "already exists. Use force=True to overwrite" in caplog.text


def test_prepdir_processor_uuid_mapping_consistency(temp_dir, config_path):
    """Test UUID mapping consistency across multiple files."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    (temp_dir / "file3.py").write_text(
        f'print("File3 Hellow World")\n# UUID: 123e4567-e89b-12d3-a456-426614174000\n', encoding="utf-8"
    )
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        use_unique_placeholders=True,
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        config_path=config_path,
    )
    output = processor.generate_output()
    assert len(output.uuid_mapping) == 1, "Should have one UUID mapping"
    placeholder = list(output.uuid_mapping.keys())[0]
    assert output.uuid_mapping[placeholder] == "123e4567-e89b-12d3-a456-426614174000"
    for file_entry in output.files.values():
        assert "123e4567-e89b-12d3-a456-426614174000" not in file_entry.content
        assert placeholder in file_entry.content


def test_validate_output_valid_content(temp_dir, config_path):
    """Test validating valid content."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '{temp_dir}'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        'print("Hello, modified")\n# UUID: PREPDIR_UUID_PLACEHOLDER_1\n'
        "=-=-= End File: 'file1.py' =-=-=\n"
        "=-=-= Begin File: 'new_file.py' =-=-=\n"
        'print("New file")\n'
        "=-=-= End File: 'new_file.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path, use_unique_placeholders=True)
    metadata = {"creator": "test_validator"}
    output = processor.validate_output(
        content=content, metadata=metadata, highest_base_directory=str(temp_dir), validate_files_exist=True
    )
    assert isinstance(output, PrepdirOutputFile)
    assert output.metadata["creator"] == "test_validator"
    assert output.metadata["base_directory"] == str(temp_dir)
    assert output.use_unique_placeholders is True
    assert len(output.files) == 2
    assert output.files[Path(temp_dir) / "file1.py"].relative_path == "file1.py"
    assert 'print("Hello, modified")' in output.files[Path(temp_dir) / "file1.py"].content
    assert output.files[Path(temp_dir) / "new_file.py"].relative_path == "new_file.py"


def test_validate_output_valid_file(temp_dir, config_path):
    """Test validating a valid prepdir output file."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    output_file = temp_dir / "output.txt"
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path, use_unique_placeholders=True)
    metadata = {"creator": "test_validator"}
    output = processor.validate_output(
        file_path=str(output_file), metadata=metadata, highest_base_directory=str(temp_dir)
    )
    assert isinstance(output, PrepdirOutputFile)
    assert output.metadata["base_directory"] == str(temp_dir)
    assert output.use_unique_placeholders is True
    assert len(output.files) == 1
    assert output.files[Path(temp_dir) / "file1.py"].relative_path == "file1.py"


def test_validate_output_invalid_content(temp_dir, config_path):
    """Test validating invalid content."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Invalid prepdir output: No begin file patterns found!"):
        processor.validate_output(content="Invalid content", highest_base_directory=str(temp_dir))


def test_validate_output_path_outside_highest_base(temp_dir, config_path):
    """Test validating content with base directory outside highest base."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '/outside'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        'print("Hello")\n'
        "=-=-= End File: 'file1.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Base directory '/outside' is outside highest base directory"):
        processor.validate_output(content=content, highest_base_directory=str(temp_dir))


def test_validate_output_file_path_outside_highest_base(temp_dir, config_path):
    """Test validating content with file path outside highest base."""

    prepdir_logging.configure_logging(logger, level=logging.INFO)
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '{temp_dir}'\n\n"
        "=-=-= Begin File: '../outside.py' =-=-=\n"
        'print("Outside")\n'
        "=-=-= End File: '../outside.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="File path '.*outside.py' is outside highest base directory"):
        processor.validate_output(content=content, highest_base_directory=str(temp_dir))


def test_init_invalid_config_path(temp_dir):
    """Test initialization with invalid config path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    with pytest.raises(ValueError, match="Custom config path '/nonexistent/invalid.yaml' does not exist"):
        PrepdirProcessor(
            directory=str(temp_dir),
            config_path="/nonexistent/invalid.yaml",
        )


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


def test_traverse_specific_files_permission_error(temp_dir, config_path, caplog):
    """Test _traverse_specific_files with permission error."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py"],
        config_path=config_path,
    )
    print(f"caplog.text is:\n{caplog.text}\n--")
    with patch("pathlib.Path.resolve", side_effect=PermissionError("Permission denied")):
        with caplog.at_level(logging.INFO):
            caplog.clear()
            files = list(processor._traverse_specific_files())

    print(f"caplog.text is:\n{caplog.text}\n--")
    assert len(files) == 1
    assert "Permission denied accessing 'file1.py'" in caplog.text


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


def test_save_output_invalid_path(temp_dir, config_path):
    """Test save_output with invalid path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
    )
    output = processor.generate_output()
    with pytest.raises(ValueError, match="Could not save output"):
        processor.save_output(output, "/invalid/path/output.txt")


def test_validate_output_both_content_and_file_path(temp_dir, config_path):
    """Test validate_output with both content and file_path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Cannot provide both content and file_path"):
        processor.validate_output(content="some content", file_path=str(temp_dir / "output.txt"))


def test_validate_output_neither_content_nor_file_path(temp_dir, config_path):
    """Test validate_output with neither content nor file_path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Must provide either content or file_path"):
        processor.validate_output()


def test_validate_output_partial_file_existence(temp_dir, config_path, caplog):
    """Test validate_output with validate_files_exist=True and partial file existence."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '{temp_dir}'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        'print("Hello")\n'
        "=-=-= End File: 'file1.py' =-=-=\n"
        "=-=-= Begin File: 'nonexistent.py' =-=-=\n"
        'print("Missing")\n'
        "=-=-= End File: 'nonexistent.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        output = processor.validate_output(
            content=content,
            highest_base_directory=str(temp_dir),
            validate_files_exist=True,
        )
    assert len(output.files) == 2
    assert "File " + str(temp_dir / "nonexistent.py") + " does not exist in filesystem" in caplog.text


def test_init_config_invalid_path(tmp_path, caplog):
    """Test init_config with invalid path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    invalid_path = "/invalid/path/config.yaml"
    with caplog.at_level(logging.ERROR):
        caplog.clear()
        with pytest.raises(
            SystemExit,
            match=f"Failed to create config file '{invalid_path}': \\[Errno 13\\] Permission denied: '/invalid'",
        ):
            PrepdirProcessor.init_config(config_path=invalid_path)
    assert f"Failed to create config file '{invalid_path}': [Errno 13] Permission denied: '/invalid'" in caplog.text


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


def test_init_invalid_replacement_uuid_type(temp_dir, config_path, caplog):
    """Test initialization with non-string replacement_uuid when scrubbing is enabled."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    with caplog.at_level(logging.ERROR):
        caplog.clear()
        PrepdirProcessor(
            directory=str(temp_dir),
            scrub_hyphenated_uuids=True,
            replacement_uuid=12345,  # Non-string UUID
            config_path=config_path,
        )
    assert "Invalid replacement UUID type: '<class 'int'>'" in caplog.text


def test_init_invalid_config_path(temp_dir):
    """Test initialization with invalid config path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    with pytest.raises(ValueError, match="Custom config path '/nonexistent/invalid.yaml' does not exist"):
        PrepdirProcessor(
            directory=str(temp_dir),
            config_path="/nonexistent/invalid.yaml",
        )


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


def test_traverse_specific_files(temp_dir, config_path, caplog):
    """Test traversal of specific files."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["nonexistent.txt", "logs"],
        config_path=config_path,
    )
    with caplog.at_level(logging.INFO):
        caplog.clear()
        files = list(processor._traverse_specific_files())
    assert len(files) == 0
    assert "File 'nonexistent.txt' does not exist" in caplog.text
    assert "'logs' is not a file" in caplog.text
    with caplog.at_level(logging.INFO):
        caplog.clear()
        with pytest.raises(ValueError, match="No files found!"):
            processor.generate_output()
    assert "No valid or accessible files found from the provided list." in caplog.text


def test_traverse_specific_files_exclusions(temp_dir, config_path, caplog):
    """Test _traverse_specific_files with excluded files and directories."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file2.txt", "logs/app.log"],
        config_path=config_path,
    )
    with caplog.at_level(logging.INFO):
        caplog.clear()
        files = list(processor._traverse_specific_files())
    assert len(files) == 0
    assert "Skipping file 'file2.txt' (excluded in config)" in caplog.text
    assert "Skipping file 'logs/app.log' (parent directory excluded)" in caplog.text


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


def test_save_output_invalid_path(temp_dir, config_path):
    """Test save_output with invalid path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
    )
    output = processor.generate_output()
    with pytest.raises(ValueError, match="Could not save output"):
        processor.save_output(output, "/invalid/path/output.txt")


def test_validate_output_both_content_and_file_path(temp_dir, config_path):
    """Test validate_output with both content and file_path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Cannot provide both content and file_path"):
        processor.validate_output(content="some content", file_path=str(temp_dir / "output.txt"))


def test_validate_output_neither_content_nor_file_path(temp_dir, config_path):
    """Test validate_output with neither content nor file_path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Must provide either content or file_path"):
        processor.validate_output()


def test_validate_output_partial_file_existence(temp_dir, config_path, caplog):
    """Test validate_output with validate_files_exist=True and partial file existence."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '{temp_dir}'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        'print("Hello")\n'
        "=-=-= End File: 'file1.py' =-=-=\n"
        "=-=-= Begin File: 'nonexistent.py' =-=-=\n"
        'print("Missing")\n'
        "=-=-= End File: 'nonexistent.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        output = processor.validate_output(
            content=content,
            highest_base_directory=str(temp_dir),
            validate_files_exist=True,
        )
    assert len(output.files) == 2
    assert "File " + str(temp_dir / "nonexistent.py") + " does not exist in filesystem" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
