import os
import tempfile
from pathlib import Path
import logging
from pydantic import ValidationError
from prepdir import PrepdirFileEntry

# Configure logging for testing
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_temp_file(content: str, suffix: str = ".txt") -> Path:
    """Create a temporary file with given content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(content)
    return Path(f.name)

def test_from_file_path_success():
    """Test successful file reading and UUID scrubbing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = create_temp_file("Content with UUID 123e4567-e89b-12d3-a456-426614174000")
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            use_unique_placeholders=True,
            verbose=True
        )
        assert isinstance(entry, PrepdirFileEntry)
        assert entry.relative_path == str(file_path.relative_to(base_dir))
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
        # Create a binary file (e.g., a JPEG header)
        file_path = create_temp_file(b"\xff\xd8\xff".decode("utf-8", errors="ignore"), suffix=".jpg")
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False
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
        # Use a non-existent file
        file_path = base_dir / "nonexistent.txt"
        try:
            PrepdirFileEntry.from_file_path(
                file_path=file_path,
                base_directory=str(base_dir),
                scrub_hyphenated_uuids=True,
                scrub_hyphenless_uuids=False
            )
        except FileNotFoundError:
            pass  # Expected behavior
        else:
            assert False, "Should raise FileNotFoundError"

def test_restore_uuids():
    """Test UUID restoration with valid and invalid uuid_mapping."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        file_path = create_temp_file("Content with PREPDIR_UUID_PLACEHOLDER_1")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False
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
        file_path = create_temp_file("Original content with PREPDIR_UUID_PLACEHOLDER_1")
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False
        )
        entry.is_scrubbed = True
        # Successful apply
        success = entry.apply_changes({"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"})
        assert success
        with open(file_path, "r", encoding="utf-8") as f:
            assert "123e4567-e89b-12d3-a456-426614174000" in f.read()
        # Binary file skip
        binary_file = create_temp_file(b"\xff\xd8\xff".decode("utf-8", errors="ignore"), suffix=".jpg")
        binary_entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=binary_file,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False
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

if __name__ == "__main__":
    import unittest
    unittest.main()