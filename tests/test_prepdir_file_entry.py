import os
import tempfile
from pathlib import Path
import logging
from unittest.mock import patch, Mock
from pydantic import ValidationError
from prepdir.prepdir_file_entry import PrepdirFileEntry

# Configure logging for testing
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_temp_file(content: str | bytes, suffix: str = ".txt") -> Path:
    """Create a temporary file with given content."""
    with tempfile.NamedTemporaryFile(
        mode="wb" if isinstance(content, bytes) else "w", suffix=suffix, delete=False
    ) as f:
        if isinstance(content, bytes):
            f.write(content)
        else:
            f.write(content)
    return Path(f.name)


def test_from_file_path_success():
    """Test successful file reading and UUID scrubbing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Content with UUID 123e4567-e89b-12d3-a456-426614174000")
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            use_unique_placeholders=True,
            verbose=True,
        )
        assert isinstance(entry, PrepdirFileEntry)
        assert entry.relative_path == "test.txt"
        assert entry.absolute_path == file_path
        assert entry.is_scrubbed
        assert not entry.is_binary
        assert entry.error is None
        assert isinstance(uuid_mapping, dict)
        assert counter > 0
        os.unlink(file_path)


def test_from_file_path_binary():
    """Test handling of binary files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.jpg"
        file_path.write_bytes(b"\xff\xd8\xff")
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path, base_directory=str(base_dir), scrub_hyphenated_uuids=True, scrub_hyphenless_uuids=False
        )
        assert entry.is_binary
        assert entry.content == "[Binary file or encoding not supported]"
        assert not entry.is_scrubbed
        assert uuid_mapping == {}
        assert counter == 1
        os.unlink(file_path)


def test_from_file_path_error():
    """Test handling of file read errors."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "nonexistent.txt"
        try:
            PrepdirFileEntry.from_file_path(
                file_path=file_path,
                base_directory=str(base_dir),
                scrub_hyphenated_uuids=True,
                scrub_hyphenless_uuids=False,
            )
        except FileNotFoundError:
            pass  # Expected behavior
        else:
            assert False, "Should raise FileNotFoundError"


def test_restore_uuids():
    """Test UUID restoration with valid and invalid uuid_mapping."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        entry.is_scrubbed = True
        # Valid mapping
        restored = entry.restore_uuids({"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"})
        assert "123e4567-e89b-12d3-a456-426614174000" in restored
        # Invalid mapping
        try:
            entry.restore_uuids(None)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
        os.unlink(file_path)


def test_apply_changes():
    """Test applying changes to a file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Original content with PREPDIR_UUID_PLACEHOLDER_1")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        entry.is_scrubbed = True
        # Successful apply
        success = entry.apply_changes({"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"})
        assert success
        with open(file_path, "r", encoding="utf-8") as f:
            assert "123e4567-e89b-12d3-a456-426614174000" in f.read()
        # Binary file skip
        binary_file = base_dir / "test.jpg"
        binary_file.write_bytes(b"\xff\xd8\xff")
        binary_entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=binary_file,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        assert not binary_entry.apply_changes({})
        os.unlink(file_path)
        os.unlink(binary_file)


def test_validation_errors():
    """Test Pydantic validation errors."""
    # Invalid absolute_path (relative)
    try:
        PrepdirFileEntry(absolute_path=Path("relative/path"), relative_path="rel", content="")
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass
    # Invalid relative_path (absolute)
    try:
        PrepdirFileEntry(absolute_path=Path("/abs/path"), relative_path="/abs/rel", content="")
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass


def test_from_file_path_separate_paths():
    """Test handling of separate relative and absolute paths."""
    with tempfile.TemporaryDirectory() as tmp_dir1, tempfile.TemporaryDirectory() as tmp_dir2:
        base_dir = Path(tmp_dir1)  # Base directory
        file_path = create_temp_file(
            "Content with UUID 123e4567-e89b-12d3-a456-426614174000", suffix=".txt"
        )  # File in a different temp dir
        # Ensure file_path is outside base_dir but exists
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            use_unique_placeholders=True,
        )
        assert isinstance(entry, PrepdirFileEntry)
        # relative_path should be the full path relative to base_dir
        expected_rel_path = os.path.relpath(file_path, base_dir)
        assert entry.relative_path == expected_rel_path
        assert entry.absolute_path == file_path
        assert entry.is_scrubbed  # Should be True due to valid UUID
        assert not entry.is_binary
        assert entry.error is None
        assert isinstance(uuid_mapping, dict)
        assert counter > 0
        os.unlink(file_path)

def test_to_output_text():
    """Test to_output method for text files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Sample content")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        output = entry.to_output(format="text")
        assert "=-= Begin File: 'test.txt' =-=" in output
        assert "Sample content" in output
        assert "=-= End File: 'test.txt' =-=" in output
        os.unlink(file_path)

def test_to_output_invalid_format():
    """Test to_output with unsupported format."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Sample content")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        try:
            entry.to_output(format="json")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert str(e) == "Unsupported output format: json"
        os.unlink(file_path)

def test_is_prepdir_outputfile_format_valid():
    """Test is_prepdir_outputfile_format with valid content."""
    with patch("prepdir.PrepdirOutputFile.from_content", return_value=Mock()):
        content = (
            "=-==-==-==-==-==-==-==-==-==-==-== Begin File: 'test.txt' =-==-==-==-==-==-==-==-==-==-==-==\n"
            "Sample content\n"
            "=-==-==-==-==-==-==-==-==-==-==-== End File: 'test.txt' =-==-==-==-==-==-==-==-==-==-==-=="
        )
        assert PrepdirFileEntry.is_prepdir_outputfile_format(content, expected_base_directory="/tmp")


def test_is_prepdir_outputfile_format_invalid():
    """Test is_prepdir_outputfile_format with invalid content."""
    with patch("prepdir.PrepdirOutputFile.from_content", side_effect=ValueError("Invalid format")):
        content = "Invalid content"
        assert not PrepdirFileEntry.is_prepdir_outputfile_format(content)
        
def test_from_file_path_read_error():
    """Test from_file_path with non-UnicodeDecodeError exception."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Sample content")
        # Simulate PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
                file_path=file_path,
                base_directory=str(base_dir),
                scrub_hyphenated_uuids=False,
                scrub_hyphenless_uuids=False,
            )
            assert entry.error == "Permission denied"
            assert entry.content == "[Error reading file: Permission denied]"
            assert not entry.is_scrubbed
            assert not entry.is_binary
            assert uuid_mapping == {}
            assert counter == 1
        os.unlink(file_path)

def test_apply_changes_write_error():
    """Test apply_changes with write failure."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        entry.is_scrubbed = True
        # Simulate write error
        with patch.object(Path, "write_text", side_effect=OSError("Write error")):
            success = entry.apply_changes({"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"})
            assert not success
            assert entry.error == "Write error"
            assert "PREPDIR_UUID_PLACEHOLDER_1" in file_path.read_text()
        os.unlink(file_path)

def test_from_file_path_empty_file():
    """Test from_file_path with empty file and scrubbing enabled."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("")
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=True,
            use_unique_placeholders=True,
        )
        assert entry.content == ""
        assert not entry.is_scrubbed
        assert not entry.is_binary
        assert entry.error is None
        assert uuid_mapping == {}
        assert counter == 1
        os.unlink(file_path)

def test_restore_uuids_empty_mapping():
    """Test restore_uuids with empty mapping when is_scrubbed=True."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = base_dir / "test.txt"
        file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
        )
        entry.is_scrubbed = True
        try:
            entry.restore_uuids({})
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert str(e) == "uuid_mapping must be a non-empty dictionary when is_scrubbed is True"
        os.unlink(file_path)

if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
