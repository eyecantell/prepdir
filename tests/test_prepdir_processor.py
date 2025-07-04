import pytest
import yaml
from pathlib import Path
import logging
import tempfile
import dynaconf
from datetime import datetime
import yaml
from prepdir.prepdir_processor import PrepdirProcessor
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.prepdir_file_entry import BINARY_CONTENT_PLACEHOLDER
from prepdir.config import load_config, __version__
from unittest.mock import patch

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logging.getLogger("prepdir.prepdir_processor").setLevel(logging.DEBUG)
logging.getLogger("prepdir.prepdir_output_file").setLevel(logging.DEBUG)
logging.getLogger("prepdir.prepdir_file_entry").setLevel(logging.DEBUG)

FILE1PY_UUID = "123e4567-e89b-12d3-a456-426614174000"
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
        "VERBOSE": False,
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

def test_init_invalid_directory(config_path):
    """Test initialization with invalid directory."""
    with pytest.raises(ValueError, match="Directory '.*' does not exist"):
        PrepdirProcessor(directory="/nonexistent", config_path=config_path)
    with tempfile.NamedTemporaryFile() as f:
        with pytest.raises(ValueError, match="'/.*' is not a directory"):
            PrepdirProcessor(directory=f.name, config_path=config_path)

def test_init_invalid_replacement_uuid(temp_dir, config_path, config_values, caplog):
    """Test initialization with invalid replacement UUID."""
    with caplog.at_level(logging.ERROR):
        processor = PrepdirProcessor(
            directory=str(temp_dir),
            replacement_uuid="invalid-uuid",
            config_path=config_path,
        )
    assert processor.replacement_uuid == config_values.get("REPLACEMENT_UUID")
    assert "Invalid replacement UUID: 'invalid-uuid'" in caplog.text

def test_load_config(config_path, config_values):
    """Test loading configuration."""
    processor = PrepdirProcessor(directory="/tmp", config_path=config_path)

    print(f"config EXCLUDE = {processor.config.get('EXCLUDE', None)}")
    print(f"config EXCLUDE.DIRECTORIES = {processor.config.get('EXCLUDE.DIRECTORIES', None)}")
    assert processor.config is not None
    assert processor.config.get("EXCLUDE.DIRECTORIES", []) == config_values.get("EXCLUDE", {}).get("DIRECTORIES")
    assert processor.config.get("EXCLUDE.FILES", []) == config_values.get("EXCLUDE", {}).get("FILES")

def test_is_excluded_dir(temp_dir, config_path):
    """Test directory exclusion logic."""
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    print(f"config EXCLUDE = {processor.config.get('EXCLUDE', None)}")
    assert processor.is_excluded_dir("logs", str(temp_dir)) is True
    assert processor.is_excluded_dir(".git", str(temp_dir)) is True
    assert processor.is_excluded_dir("src", str(temp_dir)) is False
    processor.ignore_exclusions = True
    assert processor.is_excluded_dir("logs", str(temp_dir)) is False

def test_is_excluded_file(temp_dir, config_path):
    """Test file exclusion logic."""
    processor = PrepdirProcessor(directory=str(temp_dir), output_file="output.txt", config_path=config_path)
    print(f"config EXCLUDE = {processor.config.get('EXCLUDE', None)}")
    assert processor.is_excluded_file("file2.txt", str(temp_dir)) is True
    assert processor.is_excluded_file("output.txt", str(temp_dir)) is True
    assert processor.is_excluded_file("file1.py", str(temp_dir)) is False
    processor.include_prepdir_files = True
    assert processor.is_excluded_file("output.txt", str(temp_dir)) is True  # Still excluded as output file
    processor.ignore_exclusions = True
    assert processor.is_excluded_file("file2.txt", str(temp_dir)) is False

def test_is_excluded_file_io_error(temp_dir, config_path):
    """Test is_excluded_file with IOError when checking prepdir format."""
    processor = PrepdirProcessor(directory=str(temp_dir), output_file="output.txt", config_path=config_path)
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        assert processor.is_excluded_file("output.txt", str(temp_dir)) is True  # Excluded as output file
        assert processor.is_excluded_file("file1.py", str(temp_dir)) is False

def test_traverse_specific_files(temp_dir, config_path, caplog):
    """Test traversal of specific files."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py", "nonexistent.txt", "logs"],
        config_path=config_path,
        verbose=True,
    )
    with caplog.at_level(logging.INFO):
        files = list(processor._traverse_specific_files())
    print(f"{files=}")
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "File 'nonexistent.txt' does not exist" in caplog.text
    assert "'logs' is not a file" in caplog.text

def test_traverse_directory_specific_extension(temp_dir, config_path, caplog):
    """Test directory traversal with a specific extension (.py) set."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
        verbose=True,
    )
    with caplog.at_level(logging.INFO):
        files = list(processor._traverse_directory())
    print(f"{files=}")
    assert len(files) == 1
    assert files[0] == temp_dir / "file1.py"
    assert "Skipping file: file2.txt (extension not in ['py'])" in caplog.text
    assert "Skipping file: app.log (extension not in ['py'])" in caplog.text

def test_traverse_directory_ignore_exclusions(temp_dir, config_path, caplog):
    """Test directory traversal with ignore exclusions set"""

    # Test with ignore_exclusions=True
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt", "log"],
        ignore_exclusions=True,
        include_prepdir_files=False,
        config_path=config_path,
        verbose=True,
    )

    with caplog.at_level(logging.INFO):
        files = list(processor._traverse_directory())
    
    print(f"{files=}")
    assert len(files) == 3  # file1.py, file2.txt, logs/app.log
    assert temp_dir / "file1.py" in files
    assert temp_dir / "file2.txt" in files
    assert temp_dir / "logs" / "app.log" in files
    assert temp_dir / "output.txt" not in files  # Still excluded as output file

def test_generate_output_basic(temp_dir, config_path, config_values):
    """Test generating output for a basic project directory."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        use_unique_placeholders=True,
        config_path=config_path,
        verbose=True,
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
    assert output.uuid_mapping.get("PREPDIR_UUID_PLACEHOLDER_1") == FILE1PY_UUID

def test_generate_output_specific_files(temp_dir, config_path):
    """Test generating output with specific files."""
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
    processor = PrepdirProcessor(directory=str(tmp_path), extensions=["py"], config_path=config_path)
    with pytest.raises(ValueError, match="No files found!"):
        processor.generate_output()
    
def test_generate_output_binary_file(temp_dir, config_path):
    """Test handling of binary files."""
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\xff\xfe\x00\x01")

    processor = PrepdirProcessor(directory=str(temp_dir), extensions=["bin"], config_path=config_path)
    output = processor.generate_output()
    assert isinstance(output, PrepdirOutputFile)
    assert len(output.files) == 1
    print(f"output.files are: {output.files}")
    entry = output.files[Path(temp_dir) / "binary.bin"]
    assert entry is not None
    assert entry.is_binary
    assert entry.error is None
    assert BINARY_CONTENT_PLACEHOLDER in entry.content

def test_generate_output_exclusions(temp_dir, config_path):
    """Test file and directory exclusions."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        config_path=config_path,
    )
    output = processor.generate_output()
    print(f"output.files = {output.files}")
    assert len(output.files) == 1  # Only file1.py
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "logs/app.log" not in output.content

def test_generate_output_exclusions_with_extensions(temp_dir, config_path):
    """Test file and directory exclusions when extensions are specified."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        config_path=config_path,
        extensions=["py", "txt", "log"],
    )
    output = processor.generate_output()
    print(f"output.files = {output.files}")
    assert len(output.files) == 1  # Only file1.py
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "logs/app.log" not in output.content

def test_generate_output_include_all(temp_dir, config_path):
    """Test including all files, ignoring exclusions."""
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
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        config_path=config_path,
    )
    output = processor.generate_output()
    assert FILE1PY_UUID in output.content
    assert not any(entry.is_scrubbed for entry in output.files.values())
    assert output.uuid_mapping == {}

def test_generate_output_non_unique_placeholders(temp_dir, config_path, config_values, caplog):
    """Test generate_output with non-unique placeholders."""
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        use_unique_placeholders=False,
        config_path=config_path,
        verbose=True,
    )
    with caplog.at_level(logging.INFO):
        output = processor.generate_output()
    assert f"replaced with '{processor.replacement_uuid}'" in output.content
    assert "file1.py" in output.content
    replacement_uuid = config_values.get("REPLACEMENT_UUID")
    assert replacement_uuid
    assert replacement_uuid in output.content
    assert replacement_uuid in output.uuid_mapping 

def test_validate_output_valid(temp_dir, config_path):
    """Test validating a valid prepdir output file."""
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
    content = (
        f"File listing generated {datetime.now().isoformat()} by prepdir version {__version__}\n"
        "Base directory is '/test_dir'\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        "print('Hello')\n"
        # Missing footer
    )
    output_file = tmp_path / "output.txt"
    output_file.write_text(content, encoding="utf-8")
    
    print(f"{tmp_path=}\n{output_file=}")
    processor = PrepdirProcessor(directory=tmp_path, config_path=config_path)

    with pytest.raises(ValueError, match="Unclosed file 'file1.py'"):
        processor.validate_output(file_path=str(output_file))

def test_save_output(temp_dir, config_path, tmp_path):
    """Test saving output to a file."""

    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
        use_unique_placeholders=True
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

def test_init_config(tmp_path, capsys):
    """Test initializing a local config file."""
    config_path = tmp_path / ".prepdir/config.yaml"
    PrepdirProcessor.init_config(str(config_path))
    assert config_path.exists()
    with config_path.open("r", encoding="utf-8") as f:
        content = f.read()
    print(f"content is:\n{content}")
    assert "exclude:" in content.lower()
    assert "directories:" in content.lower()
    assert "files:" in content.lower()
    with pytest.raises(SystemExit):
        PrepdirProcessor.init_config(str(config_path), force=False)
    captured = capsys.readouterr()
    assert "already exists" in captured.err

def test_prepdir_processor_uuid_mapping_consistency(temp_dir, config_path):
    """Test UUID mapping consistency across multiple files."""
    # Add another file with the same UUID
    (temp_dir / "file3.py").write_text(
        f'print("File3 Hellow World")\n# UUID: {FILE1PY_UUID}\n', encoding="utf-8"
    )
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        use_unique_placeholders=True,
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        config_path=config_path,
        verbose=True,
    )

    output = processor.generate_output()
    print(f"content is:\n{output.content}\n")
    assert len(output.uuid_mapping) == 1, "Should have one UUID mapping"
    placeholder = list(output.uuid_mapping.keys())[0]
    assert output.uuid_mapping[placeholder] == FILE1PY_UUID
    for file_entry in output.files.values():
        print(f"file entry is {file_entry}")
        assert FILE1PY_UUID not in file_entry.content
        assert placeholder in file_entry.content

def test_validate_output_valid_content(temp_dir, config_path):
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '{temp_dir}'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        "print(\"Hello, modified\")\n# UUID: PREPDIR_UUID_PLACEHOLDER_1\n"
        "=-=-= End File: 'file1.py' =-=-=\n"
        "=-=-= Begin File: 'new_file.py' =-=-=\n"
        "print(\"New file\")\n"
        "=-=-= End File: 'new_file.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path, use_unique_placeholders=True)

    metadata = {"creator": "test_validator"}
    output = processor.validate_output(content=content, metadata=metadata, highest_base_directory=str(temp_dir), validate_files_exist=True)
    print(f"{content=}\n{output=}")
    assert isinstance(output, PrepdirOutputFile)
    assert output.metadata["creator"] == "test_validator"
    assert output.metadata["base_directory"] == str(temp_dir)
    assert output.use_unique_placeholders is True
    assert len(output.files) == 2
    assert output.files[Path(temp_dir) / "file1.py"].relative_path == "file1.py"
    assert "print(\"Hello, modified\")" in output.files[Path(temp_dir) / "file1.py"].content
    assert output.files[Path(temp_dir) / "new_file.py"].relative_path == "new_file.py"

def test_validate_output_valid_file(temp_dir, config_path):
    output_file = temp_dir / "output.txt"
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path, use_unique_placeholders=True)

    metadata = {"creator": "test_validator"}
    output = processor.validate_output(file_path=str(output_file), metadata=metadata, highest_base_directory=str(temp_dir))
    assert isinstance(output, PrepdirOutputFile)
    assert output.metadata["base_directory"] == str(temp_dir)
    assert output.use_unique_placeholders is True
    assert len(output.files) == 1
    assert output.files[Path(temp_dir) / "file1.py"].relative_path == "file1.py"

def test_validate_output_invalid_content(temp_dir, config_path):
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)

    with pytest.raises(ValueError, match="Invalid prepdir output: No begin file patterns found!"):
        processor.validate_output(content="Invalid content", highest_base_directory=str(temp_dir))

def test_validate_output_path_outside_highest_base(temp_dir, config_path):
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '/outside'\n\n"
        "=-=-= Begin File: 'file1.py' =-=-=\n"
        "print(\"Hello\")\n"
        "=-=-= End File: 'file1.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)

    with pytest.raises(ValueError, match="Base directory '/outside' is outside highest base directory"):
        processor.validate_output(content=content, highest_base_directory=str(temp_dir))

def test_validate_output_file_path_outside_highest_base(temp_dir, config_path):
    content = (
        f"File listing generated {datetime.now().isoformat()} by test_validator\n"
        f"Base directory is '{temp_dir}'\n\n"
        "=-=-= Begin File: '../outside.py' =-=-=\n"
        "print(\"Outside\")\n"
        "=-=-= End File: '../outside.py' =-=-=\n"
    )
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)

    with pytest.raises(ValueError, match="File path '.*outside.py' is outside highest base directory"):
        processor.validate_output(content=content, highest_base_directory=str(temp_dir))

if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])