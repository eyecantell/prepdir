import pytest
from pathlib import Path
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.prepdir_file_entry import PrepdirFileEntry
from unittest.mock import patch
import logging
import re

# Set up logging for capturing warnings
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Test fixtures
@pytest.fixture
def temp_file(tmp_path):
    def _create_file(content):
        file_path = tmp_path / "test_prepped_dir.txt"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_file


# Test data
SAMPLE_CONTENT = """File listing generated 2025-06-26T12:15:00.123456 by prepdir version 0.14.1 (pip install prepdir)
Base directory is '/test_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content for file1
=-=-= End File: 'file1.txt' =-=-=

=-=-= Begin File: 'file2.txt' =-=-=
Content for file2
Extra =-=-= Begin File: 'file3.txt' =-=-=
=-=-= End File: 'file2.txt' =-=-=
"""


def test_manual_instance(temp_file):
    content = "=-=-= Begin File: 'file1.txt' =-=-=\nContent\n=-=-= End File: 'file1.txt' =-=-="
    file_path = temp_file(content)
    instance = PrepdirOutputFile(
        path=Path(file_path), content=content, files={}, metadata={}, uuid_mapping={}, placeholder_counter=1
    )
    assert isinstance(instance, PrepdirOutputFile)


@pytest.mark.parametrize(
    "content, expected_base_dir",
    [
        (SAMPLE_CONTENT, "/test_dir"),
        ("=-=-= Begin File: 'file1.txt' =-=-=\nContent\n=-=-= End File: 'file1.txt' =-=-=", "/test_dir"),
    ],
)
def test_from_file(temp_file, content, expected_base_dir, caplog):
    file_path = temp_file(content)
    with caplog.at_level(logging.WARNING):
        instance = (
            PrepdirOutputFile.from_file(str(file_path), expected_base_dir)
            if expected_base_dir
            else PrepdirOutputFile.from_file(str(file_path), None)
        )
    print(f"content:\n{content}\n{instance.metadata=}")
    assert isinstance(instance, PrepdirOutputFile)
    assert instance.path == file_path
    assert instance.content == content
    if "File listing generated" in content:
        assert instance.metadata["date"] == "2025-06-26T12:15:00.123456"
        assert instance.metadata["creator"] == "prepdir version 0.14.1 (pip install prepdir)"
    elif expected_base_dir:
        assert "No header found" in caplog.text
    if "Base directory is" in content and expected_base_dir:
        assert instance.metadata["base_directory"] == expected_base_dir
    elif expected_base_dir:
        assert instance.metadata["base_directory"] == expected_base_dir
        assert "No base directory found" in caplog.text
    else:
        assert instance.metadata["base_directory"] == "."
    if expected_base_dir:
        entries = instance.parse(expected_base_dir)
        assert isinstance(entries, dict)
        if "=-=-= Begin File" in content:
            assert len(entries) > 0
            for abs_path, entry in entries.items():
                assert isinstance(entry, PrepdirFileEntry)
                assert entry.relative_path in content
                assert entry.absolute_path == Path(expected_base_dir) / entry.relative_path


def test_from_file_no_headers(temp_file):
    file_path = temp_file("No headers here")
    with pytest.raises(ValueError, match="No begin file patterns found!"):
        PrepdirOutputFile.from_file(str(file_path), "test_dir")


def test_from_file_noseconds_date(temp_file):
    content = """File listing generated 2025-06-26 01:02 by Grok 3
Base directory is '/test_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    instance = PrepdirOutputFile.from_file(str(file_path), None)
    assert instance.metadata["date"] == "2025-06-26 01:02"
    assert instance.metadata["creator"] == "Grok 3"


def test_from_file_base_dir_mismatch(temp_file):
    content = """File listing generated 2025-06-26 12:15:00 by prepdir
Base directory is '/invalid_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    with pytest.raises(ValueError, match="Base directory mismatch"):
        PrepdirOutputFile.from_file(str(file_path), "/test_dir")


def test_parse_no_header_simple(temp_file):
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content for file1
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    instance = PrepdirOutputFile(path=file_path, content=content)
    entries = instance.parse("test_dir")
    assert isinstance(entries, dict)
    assert len(entries) == 1
    abs_path = Path("test_dir").absolute() / "file1.txt"
    assert abs_path in entries
    entry = entries[abs_path]
    assert isinstance(entry, PrepdirFileEntry)
    assert entry.relative_path == "file1.txt"
    assert entry.absolute_path == abs_path
    assert entry.content == "Content for file1\n"
    assert not entry.is_binary
    assert not entry.is_scrubbed


def test_parse_extra_header_as_content(temp_file, caplog):
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= Begin File: 'file2.txt' =-=-=
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    instance = PrepdirOutputFile(path=file_path, content=content, metadata={"base_directory": "test_dir"})
    with caplog.at_level(logging.WARNING):
        entries = instance.parse("test_dir")
    assert len(entries) == 1
    abs_path = Path("test_dir").absolute() / "file1.txt"
    assert abs_path in entries
    entry = entries[abs_path]
    assert "Extra header/footer" in caplog.text
    assert entry.content == "Content\n=-=-= Begin File: 'file2.txt' =-=-=\n"
    assert not entry.is_binary
    assert not entry.is_scrubbed
    assert "Extra header/footer" in caplog.text


def test_parse_unclosed_file(temp_file):
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
"""
    file_path = temp_file(content)
    instance = PrepdirOutputFile(path=file_path, content=content, metadata={"base_directory": "test_dir"})
    with pytest.raises(ValueError, match="Unclosed file 'file1.txt'"):
        instance.parse("test_dir")


def test_get_changes(temp_file):
    # Create original and updated instances
    orig_content = """=-=-= Begin File: 'file1.txt' =-=-=
File1 original content (file1 content will be changed)
=-=-= End File: 'file1.txt' =-=-=
=-=-= Begin File: 'file2.txt' =-=-=
File2 content (file2 will be removed)
=-=-= End File: 'file2.txt' =-=-=
=-=-= Begin File: 'file3.txt' =-=-=
File3 content (file3 will be unchanged)
=-=-= End File: 'file3.txt' =-=-=
"""
    updated_content = """=-=-= Begin File: 'file4.txt' =-=-=
File4 content (file4 is new)
=-=-= End File: 'file4.txt' =-=-=
=-=-= Begin File: 'file3.txt' =-=-=
File3 content (file3 will be unchanged)
=-=-= End File: 'file3.txt' =-=-=
=-=-= Begin File: 'file1.txt' =-=-=
File1 changed content
=-=-= End File: 'file1.txt' =-=-=
"""
    orig = PrepdirOutputFile.from_content(orig_content, "test_dir")
    updated = PrepdirOutputFile.from_content(updated_content, "test_dir")
    changes = updated.get_changed_files(orig)
    print(f"{changes=}")
    assert len(changes["added"]) == 1
    assert any(entry.relative_path == "file4.txt" for entry in changes["added"])
    assert len(changes["changed"]) == 1
    assert any(entry.relative_path == "file1.txt" for entry in changes["changed"])
    assert len(changes["removed"]) == 1
    assert any(entry.relative_path == "file2.txt" for entry in changes["removed"])


def test_is_prepdir_outputfile_format():
    # Test with valid prepdir format
    valid_content = """File listing generated 2025-06-26 12:15:00 by prepdir
Base directory is 'test_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    assert PrepdirFileEntry.is_prepdir_outputfile_format(valid_content, None) == True
    # Test with invalid content (no headers)
    invalid_content = "Just some text"
    assert PrepdirFileEntry.is_prepdir_outputfile_format(invalid_content, None) == False
    # Test with partial valid content
    partial_content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
"""  # Missing footer
    assert PrepdirFileEntry.is_prepdir_outputfile_format(partial_content, None) == False
    # Test with empty content
    empty_content = ""
    assert PrepdirFileEntry.is_prepdir_outputfile_format(empty_content, None) == False

def test_save_no_content(temp_file, caplog):
    """Test save method with no content."""
    file_path = temp_file("")
    instance = PrepdirOutputFile(path=file_path, content="")
    with caplog.at_level(logging.WARNING):
        instance.save()
    assert "No content specified, content not saved" in caplog.text

def test_save_no_path(caplog):
    """Test save method with no path."""
    instance = PrepdirOutputFile(content="Some content")
    with caplog.at_level(logging.WARNING):
        instance.save()
    assert "No path specified, content not saved" in caplog.text

def test_parse_footer_without_header(temp_file, caplog):
    """Test parse with footer but no matching header."""
    content = """=-=-= End File: 'file1.txt' =-=-=
Content
"""
    file_path = temp_file(content)
    instance = PrepdirOutputFile(path=file_path, content=content, metadata={"base_directory": "test_dir"})
    with caplog.at_level(logging.WARNING):
        entries = instance.parse("test_dir")
    assert len(entries) == 0
    assert "Footer found without matching header" in caplog.text

def test_parse_mismatched_footer(temp_file, caplog):
    """Test parse with mismatched footer name."""
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file2.txt' =-=-=
"""
    file_path = temp_file(content)
    instance = PrepdirOutputFile(path=file_path, content=content, metadata={"base_directory": "test_dir"})
    with pytest.raises(ValueError, match="Unclosed file 'file1.txt' at end of content"):
        entries = instance.parse("test_dir")

    assert "Mismatched footer 'file2.txt' for header 'file1.txt'" in caplog.text

def test_from_content_empty_with_headers(temp_file):
    """Test from_content with empty content but valid headers."""
    content = """File listing generated 2025-06-26T12:15:00 by prepdir
Base directory is '/test_dir'
"""
    file_path = temp_file(content)
    with pytest.raises(ValueError, match="No begin file patterns found!"):
        PrepdirOutputFile.from_content(content, "/test_dir", file_path)

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])