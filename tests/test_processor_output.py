import pytest
import yaml
from pathlib import Path
import logging
from datetime import datetime
from prepdir.prepdir_processor import PrepdirProcessor
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.prepdir_file_entry import BINARY_CONTENT_PLACEHOLDER
from prepdir.config import __version__
from prepdir import prepdir_logging

logger = logging.getLogger(__name__)
logging.getLogger("applydir").setLevel(logging.DEBUG)

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
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    outputs = processor.generate_output()
    assert len(outputs) == 1
    output = outputs[0]
    assert output.path == Path(temp_dir / "prepped_dir.txt")
    assert len(output.files) == 1
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "PREPDIR_UUID_PLACEHOLDER_1" in output.content
    assert "file2.txt" not in output.content
    assert outputs[0].metadata["version"] == __version__
    assert outputs[0].metadata["base_directory"] == str(temp_dir)
    assert outputs[0].uuid_mapping.get("PREPDIR_UUID_PLACEHOLDER_1") == "123e4567-e89b-12d3-a456-426614174000"

def test_generate_output_specific_files(temp_dir, config_path):
    """Test generating output with specific files."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        specific_files=["file1.py"],
        scrub_hyphenated_uuids=True,
        use_unique_placeholders=True,
        config_path=config_path,
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    outputs = processor.generate_output()
    assert len(outputs) == 1
    output = outputs[0]
    assert output.path == Path(temp_dir / "prepped_dir.txt")
    assert len(output.files) == 1
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "PREPDIR_UUID_PLACEHOLDER_1" in output.content

def test_generate_output_empty_directory(tmp_path, config_path):
    """Test generating output for an empty directory."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(tmp_path), extensions=["py"], config_path=config_path, output_file=None)
    with pytest.raises(ValueError, match="No files found!"):
        processor.generate_output()

def test_generate_output_binary_file(temp_dir, config_path):
    """Test handling of binary files."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\xff\xfe\x00\x01")
    processor = PrepdirProcessor(directory=str(temp_dir), extensions=["bin"], config_path=config_path, output_file=str(temp_dir / "prepped_dir.txt"))
    outputs = processor.generate_output()
    assert len(outputs) == 1
    output = outputs[0]
    assert output.path == Path(temp_dir / "prepped_dir.txt")
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
        extensions=["py", "txt", "log"],
        config_path=config_path,
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    outputs = processor.generate_output()
    assert len(outputs) == 1
    output = outputs[0]
    assert len(output.files) == 1  # Only file1.py
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" not in output.content
    assert "app.log" not in output.content

def test_generate_output_include_prepdir_files(temp_dir, config_path):
    """Test generating output with include_prepdir_files=True."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt"],
        include_prepdir_files=True,
        config_path=config_path,
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    outputs = processor.generate_output()
    assert len(outputs) == 1
    output = outputs[0]
    assert len(output.files) == 1  # file1.py, file2.txt excluded by config, output.txt included but extension not matching
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]

def test_generate_output_ignore_exclusions(temp_dir, config_path):
    """Test generating output with ignore_exclusions=True."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py", "txt", "log"],
        ignore_exclusions=True,
        include_prepdir_files=False,
        config_path=config_path,
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    with open(str(temp_dir / "file1.py"), "r") as f:  # Read as binary first
        raw_content = f.read()
        print(f"{raw_content=}")
    outputs = processor.generate_output()
    assert len(outputs) == 1
    output = outputs[0]
    assert len(output.files) == 3  # file1.py, file2.txt, logs/app.log (output.txt skipped as prepdir file)
    assert "file1.py" in [entry.relative_path for entry in output.files.values()]
    assert "file2.txt" in [entry.relative_path for entry in output.files.values()]
    assert "logs/app.log" in [entry.relative_path for entry in output.files.values()]

def test_generate_output_with_max_chars(temp_dir, config_path):
    """Test generating output with max_chars set to split into multiple files."""
    (temp_dir / "file3.py").write_text('print("World")\n', encoding="utf-8")
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        use_unique_placeholders=True,
        max_chars=300,
        config_path=config_path,
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    outputs = processor.generate_output()
    assert len(outputs) == 2
    assert "Part 1 of 2" in outputs[0].content
    assert "Part 2 of 2" in outputs[1].content
    assert "file1.py" in outputs[0].content
    assert "file3.py" in outputs[1].content
    assert len(outputs[0].files) == 1
    assert len(outputs[1].files) == 1
    assert outputs[0].path == Path(temp_dir / "prepped_dir_part1of2.txt")
    assert outputs[1].path == Path(temp_dir / "prepped_dir_part2of2.txt")

def test_validate_output_invalid_content(temp_dir, config_path):
    """Test validate_output with invalid content."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with pytest.raises(ValueError, match="Invalid prepdir output"):
        processor.validate_output(content="invalid content")

def test_save_output_invalid_path(temp_dir, config_path):
    """Test save_output with invalid path."""
    prepdir_logging.configure_logging(logger, level=logging.INFO)
    processor = PrepdirProcessor(
        directory=str(temp_dir),
        extensions=["py"],
        config_path=config_path,
        output_file=str(temp_dir / "prepped_dir.txt"),
    )
    outputs = processor.generate_output()
    with pytest.raises(ValueError, match="Could not save output"):
        processor.save_output(outputs[0], "/invalid/path/output.txt")

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

def test_generate_output_large_single_file(temp_dir, config_path, caplog):
    large_file = temp_dir / "large.py"
    large_file.write_text("a" * 1000)  # > max_chars
    processor = PrepdirProcessor(directory=str(temp_dir), extensions=["py"], max_chars=500, config_path=config_path)
    with caplog.at_level(logging.INFO):
        outputs = processor.generate_output()
    assert len(outputs) == 2 # One for file.py and one for large.py
    assert "exceeds max_chars" in caplog.text

def test_validate_output_invalid_paths(temp_dir, config_path):
    processor = PrepdirProcessor(directory=str(temp_dir), config_path=config_path)
    with open(str(temp_dir / "output.txt"), "r") as f:
        output_file_content = f.read()
        print(f"{output_file_content=}")
    with pytest.raises(ValueError, match="outside highest base directory"):
        processor.validate_output(content=output_file_content, highest_base_directory="/invalid")
    with pytest.raises(ValueError, match="Invalid prepdir output"):
        processor.validate_output(content="invalid content")

def test_generate_output_no_files(temp_dir, config_path):
    processor = PrepdirProcessor(directory=str(temp_dir), extensions=["nonexistent_ext"], config_path=config_path)
    with pytest.raises(ValueError, match="No files found!"):
        processor.generate_output()

def test_init_invalid_directory(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        PrepdirProcessor(directory=str(tmp_path / "nonexistent"))
    with pytest.raises(ValueError, match="does not exist"):
        PrepdirProcessor(directory=str(tmp_path / "file.txt"))  # Create a file first

def test_init_invalid_replacement_uuid(caplog):
    with caplog.at_level(logging.ERROR):
        processor = PrepdirProcessor(directory=".", replacement_uuid=123)  # Invalid type
        assert "Invalid replacement UUID type" in caplog.text
    with caplog.at_level(logging.ERROR):
        processor = PrepdirProcessor(directory=".", replacement_uuid="invalid-uuid")
        assert "Invalid replacement UUID" in caplog.text