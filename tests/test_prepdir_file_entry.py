import os
import tempfile
from pathlib import Path
import logging
import pytest
from unittest.mock import patch, Mock
from io import StringIO
from pydantic import ValidationError
import sys
from prepdir import PrepdirFileEntry, BINARY_CONTENT_PLACEHOLDER, PREPDIR_DASHES
from typing import Union

# Configure logging for testing
logger = logging.getLogger(__name__)


def create_temp_file(content: Union[str, bytes], suffix: str = ".txt") -> Path:
    """Create a temporary file with given content."""
    with tempfile.NamedTemporaryFile(
        mode="wb" if isinstance(content, bytes) else "w", suffix=suffix, delete=False
    ) as f:
        if isinstance(content, bytes):
            f.write(content)
        else:
            f.write(content)
    return Path(f.name)


@pytest.fixture
def capture_log():
    """Capture log output during tests for the prepdir package."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)

    # Configure logger at the parent 'prepdir' level to capture all sub-loggers
    prepdir_logger = logging.getLogger("prepdir")

    # Store original state
    original_handlers = prepdir_logger.handlers[:]
    original_level = prepdir_logger.level
    original_propagate = prepdir_logger.propagate

    # Clear existing handlers, set level to DEBUG, and disable propagation
    prepdir_logger.handlers = []
    prepdir_logger.setLevel(logging.DEBUG)
    prepdir_logger.propagate = False
    prepdir_logger.addHandler(handler)

    # Debug print to verify logger state
    print(
        f"capture_log setup: Logger=prepdir, Level={prepdir_logger.level}, Handlers={prepdir_logger.handlers}, Propagate={prepdir_logger.propagate}"
    )

    yield log_stream

    # Clean up
    prepdir_logger.removeHandler(handler)
    prepdir_logger.handlers = original_handlers
    prepdir_logger.setLevel(original_level)
    prepdir_logger.propagate = original_propagate
    print(
        f"capture_log cleanup: Logger=prepdir, Level={prepdir_logger.level}, Handlers={prepdir_logger.handlers}, Propagate={prepdir_logger.propagate}"
    )


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_from_file_path_success(capture_log, tmp_dir):
    """Test successful file reading and UUID scrubbing with quiet settings."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Content with UUID 123e4567-e89b-12d3-a456-426614174000")

    # Capture stdout for print statements
    stdout_capture = StringIO()
    with patch("sys.stdout", stdout_capture):
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(tmp_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            use_unique_placeholders=True,
            quiet=False,
        )
    assert isinstance(entry, PrepdirFileEntry)
    assert entry.relative_path == "test.txt"
    assert entry.absolute_path == file_path
    assert entry.is_scrubbed
    assert "PREPDIR_UUID_PLACEHOLDER_1" in entry.content
    assert not entry.is_binary
    assert entry.error is None
    assert isinstance(uuid_mapping, dict)
    assert "123e4567-e89b-12d3-a456-426614174000" in uuid_mapping.values()
    assert counter == 2
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_success, quiet=False): {log_output}")
    assert f"instantiating from {file_path}" in log_output
    assert "decoded with utf-8" in log_output
    assert f"Scrubbed UUID: 123e4567-e89b-12d3-a456-426614174000 -> PREPDIR_UUID_PLACEHOLDER_1" in log_output
    stdout_output = stdout_capture.getvalue()
    assert "Scrubbed UUIDs in test.txt" in stdout_output

    # Test with quiet=True, using a fresh uuid_mapping
    capture_log.truncate(0)
    capture_log.seek(0)
    stdout_capture.truncate(0)
    stdout_capture.seek(0)
    with patch("sys.stdout", stdout_capture):
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(tmp_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            use_unique_placeholders=True,
            quiet=True,
            uuid_mapping={},  # Reset uuid_mapping to avoid state leakage
        )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_success, quiet=True): {log_output}")
    assert f"instantiating from {file_path}" in log_output
    assert f"Scrubbed UUID: 123e4567-e89b-12d3-a456-426614174000 -> PREPDIR_UUID_PLACEHOLDER_1" in log_output
    assert stdout_capture.getvalue() == ""  # No print output in quiet mode


def test_from_file_path_binary(capture_log, tmp_dir):
    """Test handling of binary files with quiet settings."""
    file_path = tmp_dir / "test.jpg"
    file_path.write_bytes(b"\xff\xd8\xff")

    # Test with quiet=False
    stdout_capture = StringIO()
    with patch("sys.stdout", stdout_capture):
        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(tmp_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            quiet=False,
        )
    assert entry.is_binary
    assert entry.content == BINARY_CONTENT_PLACEHOLDER
    assert not entry.is_scrubbed
    assert uuid_mapping == {}
    assert counter == 1
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_binary, quiet=False): {log_output}")
    assert "got UnicodeDecodeError with utf-8, presuming binary" in log_output
    assert "File test.jpg is binary or encoding not supported" in stdout_capture.getvalue()

    # Test with quiet=True
    capture_log.truncate(0)
    capture_log.seek(0)
    stdout_capture.truncate(0)
    stdout_capture.seek(0)
    with patch("sys.stdout", stdout_capture):
        entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(tmp_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            quiet=True,
        )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_binary, quiet=True): {log_output}")
    assert "got UnicodeDecodeError with utf-8, presuming binary" in log_output
    assert stdout_capture.getvalue() == ""  # No print output in quiet mode


def test_from_file_path_error(capture_log, tmp_dir):
    """Test handling of file not found with quiet settings."""
    file_path = tmp_dir / "nonexistent.txt"

    # Test with quiet=False
    stderr_capture = StringIO()
    with patch("sys.stderr", stderr_capture):
        with pytest.raises(FileNotFoundError, match=f"File not found: {file_path}"):
            PrepdirFileEntry.from_file_path(
                file_path=file_path,
                base_directory=str(tmp_dir),
                scrub_hyphenated_uuids=True,
                scrub_hyphenless_uuids=False,
                quiet=False,
            )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_error, quiet=False): {log_output}")
    assert f"File not found: {file_path}" in log_output
    assert f"Error: File not found: {file_path}" in stderr_capture.getvalue()

    # Test with quiet=True
    capture_log.truncate(0)
    capture_log.seek(0)
    stderr_capture.truncate(0)
    stderr_capture.seek(0)
    with patch("sys.stderr", stderr_capture):
        with pytest.raises(FileNotFoundError, match=f"File not found: {file_path}"):
            PrepdirFileEntry.from_file_path(
                file_path=file_path,
                base_directory=str(tmp_dir),
                scrub_hyphenated_uuids=True,
                scrub_hyphenless_uuids=False,
                quiet=True,
            )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_error, quiet=True): {log_output}")
    assert f"File not found: {file_path}" in log_output
    assert stderr_capture.getvalue() == ""  # No print output in quiet mode


def test_from_file_path_read_error(capture_log, tmp_dir):
    """Test from_file_path with non-UnicodeDecodeError exception."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Sample content")

    stderr_capture = StringIO()
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with patch("sys.stderr", stderr_capture):
            entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
                file_path=file_path,
                base_directory=str(tmp_dir),
                scrub_hyphenated_uuids=False,
                scrub_hyphenless_uuids=False,
                quiet=False,
            )
    assert entry.error == "Permission denied"
    assert entry.content == "[Error reading file: Permission denied]"
    assert not entry.is_scrubbed
    assert not entry.is_binary
    assert uuid_mapping == {}
    assert counter == 1
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_read_error): {log_output}")
    assert f"Failed to read {file_path}: Permission denied" in log_output
    assert f"Error: Failed to read {file_path}: Permission denied" in stderr_capture.getvalue()


def test_from_file_path_empty_file(capture_log, tmp_dir):
    """Test from_file_path with empty file and scrubbing enabled."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("")

    entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=True,
        scrub_hyphenless_uuids=True,
        use_unique_placeholders=True,
        quiet=False,
    )
    assert entry.content == ""
    assert not entry.is_scrubbed
    assert not entry.is_binary
    assert entry.error is None
    assert uuid_mapping == {}
    assert counter == 1
    log_output = capture_log.getvalue()
    print(f"Log Output (test_from_file_path_empty_file): {log_output}")
    assert f"instantiating from {file_path}" in log_output
    assert "decoded with utf-8" in log_output


def test_restore_uuids(capture_log, tmp_dir):
    """Test UUID restoration with valid and invalid uuid_mapping."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")

    # Create entry
    entry, _, _ = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        quiet=True,
    )
    entry.is_scrubbed = True

    # Valid mapping with quiet=False
    stdout_capture = StringIO()
    capture_log.truncate(0)
    capture_log.seek(0)
    with patch("sys.stdout", stdout_capture):
        restored = entry.restore_uuids(
            uuid_mapping={"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"},
            quiet=False,
        )
    assert "123e4567-e89b-12d3-a456-426614174000" in restored
    log_output = capture_log.getvalue()
    print(f"Log Output (test_restore_uuids, valid mapping): {log_output}")
    assert f"Restored UUIDs in test.txt" in log_output
    assert "Restored UUIDs in test.txt" in stdout_capture.getvalue()

    # Invalid mapping with quiet=False
    stderr_capture = StringIO()
    capture_log.truncate(0)
    capture_log.seek(0)
    with patch("sys.stderr", stderr_capture):
        with pytest.raises(ValueError, match="uuid_mapping must be a non-empty dictionary when is_scrubbed is True"):
            entry.restore_uuids(
                uuid_mapping=None,
                quiet=False,
            )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_restore_uuids, invalid mapping, quiet=False): {log_output}")
    assert f"No valid uuid_mapping provided for test.txt" in log_output
    assert "Error: No valid uuid_mapping provided for test.txt" in stderr_capture.getvalue()

    # Invalid mapping with quiet=True
    capture_log.truncate(0)
    capture_log.seek(0)
    stderr_capture.truncate(0)
    stderr_capture.seek(0)
    with patch("sys.stderr", stderr_capture):
        with pytest.raises(ValueError, match="uuid_mapping must be a non-empty dictionary when is_scrubbed is True"):
            entry.restore_uuids(
                uuid_mapping=None,
                quiet=True,
            )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_restore_uuids, invalid mapping, quiet=True): {log_output}")
    assert f"No valid uuid_mapping provided for test.txt" in log_output
    assert stderr_capture.getvalue() == ""  # No print output in quiet mode


def test_restore_uuids_empty_mapping(capture_log, tmp_dir):
    """Test restore_uuids with empty mapping when is_scrubbed=True."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")

    entry, _, _ = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        quiet=True,
    )
    entry.is_scrubbed = True

    stderr_capture = StringIO()
    with patch("sys.stderr", stderr_capture):
        with pytest.raises(ValueError, match="uuid_mapping must be a non-empty dictionary when is_scrubbed is True"):
            entry.restore_uuids(
                uuid_mapping={},
                quiet=False,
            )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_restore_uuids_empty_mapping): {log_output}")
    assert f"No valid uuid_mapping provided for test.txt" in log_output
    assert "Error: No valid uuid_mapping provided for test.txt" in stderr_capture.getvalue()


def test_apply_changes(capture_log, tmp_dir):
    """Test applying changes to a file with quiet settings."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")

    # Create entry
    entry, _, _ = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        quiet=True,
    )
    entry.is_scrubbed = True

    # Successful apply with quiet=False
    stdout_capture = StringIO()
    capture_log.truncate(0)
    capture_log.seek(0)
    with patch("sys.stdout", stdout_capture):
        success = entry.apply_changes(
            uuid_mapping={"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"},
            quiet=False,
        )
    assert success
    assert "123e4567-e89b-12d3-a456-426614174000" in file_path.read_text()
    log_output = capture_log.getvalue()
    print(f"Log Output (test_apply_changes, success): {log_output}")
    assert f"Restored UUIDs in test.txt" in log_output
    assert f"Applied changes to test.txt" in log_output
    assert "Applied changes to test.txt" in stdout_capture.getvalue()

    # Binary file skip with quiet=False
    binary_file = tmp_dir / "test.jpg"
    binary_file.write_bytes(b"\xff\xd8\xff")
    capture_log.truncate(0)
    capture_log.seek(0)
    stdout_capture.truncate(0)
    stdout_capture.seek(0)
    with patch("sys.stdout", stdout_capture):
        binary_entry, _, _ = PrepdirFileEntry.from_file_path(
            file_path=binary_file,
            base_directory=str(tmp_dir),
            scrub_hyphenated_uuids=False,
            scrub_hyphenless_uuids=False,
            quiet=False,
        )
        success = binary_entry.apply_changes(
            uuid_mapping={},
            quiet=False,
        )
    log_output = capture_log.getvalue()
    print(f"Log Output (test_apply_changes, binary skip): {log_output}")
    assert "Skipping apply_changes for test.jpg: binary" in log_output
    assert "Warning: Skipping apply_changes for test.jpg: binary" in stdout_capture.getvalue()


def test_apply_changes_write_error(capture_log, tmp_dir):
    """Test apply_changes with write failure."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Content with PREPDIR_UUID_PLACEHOLDER_1")

    entry, _, _ = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        quiet=True,
    )
    entry.is_scrubbed = True

    stderr_capture = StringIO()
    with patch.object(Path, "write_text", side_effect=OSError("Write error")):
        with patch("sys.stderr", stderr_capture):
            success = entry.apply_changes(
                uuid_mapping={"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"},
                quiet=False,
            )
    assert not success
    assert entry.error == "Write error"
    assert "PREPDIR_UUID_PLACEHOLDER_1" in file_path.read_text()
    log_output = capture_log.getvalue()
    print(f"Log Output (test_apply_changes_write_error): {log_output}")
    assert f"Failed to apply changes to test.txt: Write error" in log_output
    assert f"Error: Failed to apply changes to test.txt: Write error" in stderr_capture.getvalue()


def test_validation_errors():
    """Test Pydantic validation errors."""
    # Invalid absolute_path (relative)
    with pytest.raises(ValidationError):
        PrepdirFileEntry(absolute_path=Path("relative/path"), relative_path="test.txt", content="")

    # Invalid relative_path (absolute)
    with pytest.raises(ValidationError):
        PrepdirFileEntry(absolute_path=Path("/abs/path"), relative_path="/abs/valid", content="")


def test_from_file_path_separate_paths():
    """Test handling of separate relative and absolute paths."""
    with tempfile.TemporaryDirectory() as tmp_dir1:
        base_dir = Path(tmp_dir1)
        file_path = create_temp_file("Content with UUID 123e4567-e89b-12d3-a456-426614174000", suffix=".txt")

        entry, uuid_mapping, counter = PrepdirFileEntry.from_file_path(
            file_path=file_path,
            base_directory=str(base_dir),
            scrub_hyphenated_uuids=True,
            scrub_hyphenless_uuids=False,
            use_unique_placeholders=True,
            quiet=True,
        )
        assert isinstance(entry, PrepdirFileEntry)
        expected_rel_path = os.path.relpath(file_path, base_dir)
        assert entry.relative_path == expected_rel_path
        assert entry.absolute_path == file_path
        assert entry.is_scrubbed
        assert not entry.is_binary
        assert entry.error is None
        assert isinstance(uuid_mapping, dict)
        assert counter > 0
        os.unlink(file_path)


def test_to_output_text(tmp_dir):
    """Test to_output method for text files."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Sample content")

    entry, _, _ = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        quiet=True,
    )
    output = entry.to_output(format="text")
    assert f"{PREPDIR_DASHES} Begin File: 'test.txt' {PREPDIR_DASHES}" in output
    assert "Sample content" in output
    assert f"{PREPDIR_DASHES} End File: 'test.txt' {PREPDIR_DASHES}" in output


def test_to_output_invalid_format(tmp_dir):
    """Test to_output with unsupported format."""
    file_path = tmp_dir / "test.txt"
    file_path.write_text("Sample content")

    entry, _, _ = PrepdirFileEntry.from_file_path(
        file_path=file_path,
        base_directory=str(tmp_dir),
        scrub_hyphenated_uuids=False,
        scrub_hyphenless_uuids=False,
        quiet=True,
    )
    with pytest.raises(ValueError, match="Unsupported output format: json"):
        entry.to_output(format="json")


def test_is_prepdir_outputfile_format_valid():
    """Test is_prepdir_outputfile_format with valid content."""
    with patch("prepdir.prepdir_output_file.PrepdirOutputFile.from_content", return_value=Mock()):
        content = (
            f"{PREPDIR_DASHES} Begin File: 'test.txt' {PREPDIR_DASHES}\n"
            "Sample content\n"
            f"{PREPDIR_DASHES} End File: 'test.txt' {PREPDIR_DASHES}"
        )
        assert PrepdirFileEntry.is_prepdir_outputfile_format(content, highest_base_directory="/tmp")


def test_is_prepdir_outputfile_format_invalid():
    """Test is_prepdir_outputfile_format with invalid content."""
    with patch("prepdir.prepdir_output_file.PrepdirOutputFile.from_content", side_effect=ValueError("Invalid format")):
        content = "Invalid content"
        assert not PrepdirFileEntry.is_prepdir_outputfile_format(content)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
