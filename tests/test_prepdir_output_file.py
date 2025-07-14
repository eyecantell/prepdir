import pytest
from pathlib import Path
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.prepdir_file_entry import PrepdirFileEntry
from prepdir.config import __version__
from prepdir import prepdir_logging
from io import StringIO
import logging
from unittest.mock import patch

logger = logging.getLogger(__name__)


# Test fixtures
@pytest.fixture
def temp_file(tmp_path):
    def _create_file(content):
        file_path = tmp_path / "test_prepped_dir.txt"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_file


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset logger state before and after each test."""
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = False  # Disable propagation to prevent parent handlers
    yield
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


@pytest.fixture
def streams():
    stdout = StringIO()
    stderr = StringIO()
    yield stdout, stderr
    stdout.close()
    stderr.close()


@pytest.fixture
def configure_logger(streams):
    stdout, stderr = streams

    def _configure(level=logging.INFO):
        prepdir_logging.configure_logging(logger, level=level, stdout_stream=stdout, stderr_stream=stderr)
        assert len(logger.handlers) == 2, (
            f"Expected 2 handlers, got {len(logger.handlers)}: {[h.__class__.__name__ for h in logger.handlers]}"
        )
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.handlers[0].stream is stdout
        assert logger.handlers[0].level == logging.DEBUG
        assert isinstance(logger.handlers[1], logging.StreamHandler)
        assert logger.handlers[1].stream is stderr
        assert logger.handlers[1].level == logging.WARNING

    return _configure


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


def test_manual_instance(temp_file, configure_logger):
    configure_logger(level=logging.DEBUG)  # Enable DEBUG logs
    content = "=-=-= Begin File: 'file1.txt' =-=-=\nContent\n=-=-= End File: 'file1.txt' =-=-="
    file_path = temp_file(content)
    instance = PrepdirOutputFile(
        path=Path(file_path),
        content=content,
        files={},
        metadata={
            "base_directory": "test_dir",
            "date": "2025-06-26T12:15:00",
            "creator": "prepdir",
            "version": __version__,
        },
        uuid_mapping={},
        use_unique_placeholders=False,
        placeholder_counter=1,
    )
    assert isinstance(instance, PrepdirOutputFile)


def test_from_file(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = SAMPLE_CONTENT
    file_path = temp_file(content)
    metadata = {
        "base_directory": "/test_dir",
        "version": "0.14.1",
        "date": "2025-06-26T12:15:00.123456",
        "creator": "prepdir version 0.14.1 (pip install prepdir)",
    }
    with caplog.at_level(logging.DEBUG):
        instance = PrepdirOutputFile.from_file(str(file_path), metadata=metadata, use_unique_placeholders=False)
    assert isinstance(instance, PrepdirOutputFile)
    assert instance.path == file_path
    assert instance.content == content
    assert instance.metadata["date"] == "2025-06-26T12:15:00.123456"
    assert instance.metadata["creator"] == "prepdir version 0.14.1 (pip install prepdir)"
    assert instance.metadata["base_directory"] == "/test_dir"
    assert instance.metadata["version"] == "0.14.1"
    assert instance.use_unique_placeholders == False
    entries = instance.files  # parse is called in from_file
    assert len(entries) == 2
    assert Path("/test_dir/file1.txt") in entries
    assert Path("/test_dir/file2.txt") in entries
    assert entries[Path("/test_dir/file1.txt")].content == "Content for file1\n"
    assert (
        entries[Path("/test_dir/file2.txt")].content == "Content for file2\nExtra =-=-= Begin File: 'file3.txt' =-=-=\n"
    )
    # Verify DEBUG logs from from_content and parse
    assert "Got 11 lines of content" in caplog.text
    assert "Found begin file pattern in line" in caplog.text
    assert "11 lines to parse" in caplog.text


def test_from_file_no_headers(temp_file, configure_logger):
    configure_logger(level=logging.DEBUG)
    content = "No headers here"
    file_path = temp_file(content)
    with pytest.raises(ValueError, match="No begin file patterns found!"):
        PrepdirOutputFile.from_file(str(file_path), metadata={"base_directory": "test_dir"})


def test_from_file_noseconds_date(temp_file, configure_logger):
    configure_logger(level=logging.INFO)
    content = """File listing generated 2025-06-26 01:02 by Grok 3
Base directory is '/test_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    metadata = {"base_directory": "/test_dir", "version": __version__, "date": "2025-06-26 01:02", "creator": "Grok 3"}
    instance = PrepdirOutputFile.from_file(
        str(file_path),
        metadata=metadata,
        use_unique_placeholders=False,
    )
    assert instance.metadata["date"] == "2025-06-26 01:02"
    assert instance.metadata["creator"] == "Grok 3"
    assert instance.metadata["base_directory"] == "/test_dir"
    assert len(instance.files) == 1
    assert instance.files[Path("/test_dir/file1.txt")].content == "Content\n"


def test_from_file_base_dir_mismatch(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = """File listing generated 2025-06-26 12:15:00 by prepdir
Base directory is '/invalid_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    metadata = {
        "base_directory": "/test_dir",
        "version": __version__,
        "date": "2025-06-26 12:15:00",
        "creator": "prepdir",
    }
    with caplog.at_level(logging.DEBUG):
        instance = PrepdirOutputFile.from_file(str(file_path), metadata=metadata, use_unique_placeholders=False)
    assert "header base dir (/invalid_dir) do not match" in caplog.text
    assert instance.metadata["base_directory"] == "/invalid_dir"  # Header wins
    assert "Got 6 lines of content" in caplog.text
    assert "6 lines to parse" in caplog.text


def test_from_content_with_uuid_mapping(temp_file, configure_logger):
    configure_logger(level=logging.INFO)
    content = """File listing generated 2025-06-26T12:15:00 by prepdir
Base directory is '/test_dir'
=-=-= Begin File: 'file1.txt' =-=-=
Content with PREPDIR_UUID_PLACEHOLDER_1
=-=-= End File: 'file1.txt' =-=-=
"""
    uuid_mapping = {"PREPDIR_UUID_PLACEHOLDER_1": "123e4567-e89b-12d3-a456-426614174000"}
    metadata = {
        "base_directory": "/test_dir",
        "version": __version__,
        "date": "2025-06-26T12:15:00",
        "creator": "prepdir",
    }
    instance = PrepdirOutputFile.from_content(
        content, uuid_mapping=uuid_mapping, metadata=metadata, use_unique_placeholders=True
    )
    assert instance.uuid_mapping == uuid_mapping
    assert len(instance.files) == 1
    assert instance.files[Path("/test_dir/file1.txt")].content == "Content with PREPDIR_UUID_PLACEHOLDER_1\n"


def test_from_content_no_metadata(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = """File listing generated 2025-06-26T12:15:00 by prepdir
Base directory is '/test_dir'
=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    with caplog.at_level(logging.DEBUG):
        instance = PrepdirOutputFile.from_content(content, path_obj=file_path)
    assert instance.metadata["base_directory"] == "/test_dir"
    assert instance.metadata["date"] == "2025-06-26T12:15:00"
    assert instance.metadata["creator"] == "prepdir"
    assert instance.use_unique_placeholders == False
    assert instance.metadata["version"] == ""
    assert "Got 5 lines of content" in caplog.text
    assert "5 lines to parse" in caplog.text


def test_from_content_metadata_mismatch(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = """File listing generated 2025-06-26T12:15:00 by prepdir
Base directory is '/header_dir'
=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    metadata = {
        "base_directory": "/test_dir",
        "version": __version__,
        "date": "2025-06-26T12:00:00",
        "creator": "other",
    }
    file_path = temp_file(content)
    with caplog.at_level(logging.DEBUG):
        instance = PrepdirOutputFile.from_content(content, path_obj=file_path, metadata=metadata)
    assert (
        "Passed metadata for date (2025-06-26T12:00:00) and header date (2025-06-26T12:15:00) do not match"
        in caplog.text
    )
    assert "Passed metadata for creator (other) and header date (prepdir) do not match" in caplog.text
    assert (
        "Passed metadata for base_directory (/test_dir) and header base dir (/header_dir) do not match" in caplog.text
    )
    assert instance.metadata["date"] == "2025-06-26T12:15:00"
    assert instance.metadata["creator"] == "prepdir"
    assert instance.metadata["base_directory"] == "/header_dir"
    assert instance.metadata["version"] == __version__
    assert "Got 5 lines of content" in caplog.text
    assert "5 lines to parse" in caplog.text


def test_parse_no_header_simple(temp_file, configure_logger):
    configure_logger(level=logging.INFO)
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content for file1
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content=content, metadata=metadata, use_unique_placeholders=False)
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


def test_parse_extra_header_as_content(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= Begin File: 'file2.txt' =-=-=
=-=-= End File: 'file1.txt' =-=-=
"""
    file_path = temp_file(content)
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content=content, metadata=metadata, use_unique_placeholders=False)
    with caplog.at_level(logging.DEBUG):
        entries = instance.parse("test_dir")
    assert len(entries) == 1
    abs_path = Path("test_dir").absolute() / "file1.txt"
    assert abs_path in entries
    entry = entries[abs_path]
    assert "Extra header/footer" in caplog.text
    assert entry.content == "Content\n=-=-= Begin File: 'file2.txt' =-=-=\n"
    assert not entry.is_binary
    assert not entry.is_scrubbed
    assert "4 lines to parse" in caplog.text


def test_parse_unclosed_file(temp_file, configure_logger):
    configure_logger(level=logging.INFO)
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
"""
    file_path = temp_file(content)
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content=content, metadata=metadata, use_unique_placeholders=False)
    with pytest.raises(ValueError, match="Unclosed file 'file1.txt'"):
        instance.parse("test_dir")


def test_get_changes(temp_file, configure_logger):
    configure_logger(level=logging.INFO)
    orig_content = """=-=-= Begin File: 'file1.txt' =-=-=
File1 original content
=-=-= End File: 'file1.txt' =-=-=
=-=-= Begin File: 'file2.txt' =-=-=
File2 content
=-=-= End File: 'file2.txt' =-=-=
=-=-= Begin File: 'file3.txt' =-=-=
File3 content
=-=-= End File: 'file3.txt' =-=-=
"""
    updated_content = """=-=-= Begin File: 'file4.txt' =-=-=
File4 content
=-=-= End File: 'file4.txt' =-=-=
=-=-= Begin File: 'file3.txt' =-=-=
File3 content
=-=-= End File: 'file3.txt' =-=-=
=-=-= Begin File: 'file1.txt' =-=-=
File1 changed content
=-=-= End File: 'file1.txt' =-=-=
"""
    metadata = {
        "base_directory": "test_dir",
        "version": __version__,
        "date": "2025-06-26T12:15:00",
        "creator": "prepdir",
    }
    orig = PrepdirOutputFile.from_content(orig_content, metadata=metadata, use_unique_placeholders=False)
    updated = PrepdirOutputFile.from_content(updated_content, metadata=metadata, use_unique_placeholders=False)
    changes = updated.get_changed_files(orig)
    assert len(changes["added"]) == 1
    assert any(entry.relative_path == "file4.txt" for entry in changes["added"])
    assert len(changes["changed"]) == 1
    assert any(entry.relative_path == "file1.txt" for entry in changes["changed"])
    assert len(changes["removed"]) == 1
    assert any(entry.relative_path == "file2.txt" for entry in changes["removed"])


def test_is_prepdir_outputfile_format(configure_logger):
    configure_logger(level=logging.INFO)
    valid_content = """File listing generated 2025-06-26 12:15:00 by prepdir
Base directory is 'test_dir'

=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file1.txt' =-=-=
"""
    assert PrepdirFileEntry.is_prepdir_outputfile_format(valid_content, None) == True
    invalid_content = "Just some text"
    assert PrepdirFileEntry.is_prepdir_outputfile_format(invalid_content, None) == False
    partial_content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
"""
    assert PrepdirFileEntry.is_prepdir_outputfile_format(partial_content, None) == False
    empty_content = ""
    assert PrepdirFileEntry.is_prepdir_outputfile_format(empty_content, None) == False


def test_save_no_content(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.INFO)
    caplog.clear()  # Clear configure_logging's logs
    file_path = temp_file("")
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content="", metadata=metadata, use_unique_placeholders=False)
    with caplog.at_level(logging.WARNING):
        instance.save()
    assert "No content specified, content not saved" in caplog.text


def test_save_no_path(caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.INFO)
    caplog.clear()  # Clear configure_logging's logs
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(content="Some content", metadata=metadata, use_unique_placeholders=False)
    with caplog.at_level(logging.WARNING):
        instance.save()
    assert "No path specified, content not saved" in caplog.text


def test_save_success(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.INFO)
    caplog.clear()  # Clear configure_logging's logs
    content = "Some content"
    file_path = temp_file(content)
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content=content, metadata=metadata, use_unique_placeholders=False)
    with caplog.at_level(logging.INFO):
        instance.save()
    assert f"Saved output to {file_path}" in caplog.text


def test_quiet_mode(temp_file, caplog, streams):
    stdout, stderr = streams
    prepdir_logging.configure_logging(logger, level=logging.WARNING, stdout_stream=stdout, stderr_stream=stderr)
    caplog.clear()  # Clear configure_logging's logs
    logger.propagate = False
    content = SAMPLE_CONTENT
    file_path = temp_file(content)
    metadata = {
        "base_directory": "/test_dir",
        "version": "0.14.1",
        "date": "2025-06-26T12:15:00.123456",
        "creator": "prepdir version 0.14.1 (pip install prepdir)",
    }
    with caplog.at_level(logging.WARNING):
        instance = PrepdirOutputFile.from_file(str(file_path), metadata=metadata, use_unique_placeholders=False)
    assert "Got 11 lines of content" not in caplog.text  # DEBUG log suppressed
    assert "Found begin file pattern in line" not in caplog.text  # DEBUG log suppressed
    assert "11 lines to parse" not in caplog.text  # DEBUG log suppressed
    assert len(instance.files) == 2


def test_parse_footer_without_header(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = """=-=-= End File: 'file1.txt' =-=-=
Content
"""
    file_path = temp_file(content)
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content=content, metadata=metadata, use_unique_placeholders=False)
    with caplog.at_level(logging.DEBUG):
        entries = instance.parse("test_dir")
    assert len(entries) == 0
    assert "Footer found without matching header" in caplog.text
    assert "2 lines to parse" in caplog.text


def test_parse_mismatched_footer(temp_file, caplog, configure_logger, streams):
    stdout, _ = streams
    configure_logger(level=logging.DEBUG)
    caplog.clear()  # Clear configure_logging's logs
    content = """=-=-= Begin File: 'file1.txt' =-=-=
Content
=-=-= End File: 'file2.txt' =-=-=
"""
    file_path = temp_file(content)
    metadata = {"base_directory": "test_dir", "version": __version__, "date": "unknown", "creator": "prepdir"}
    instance = PrepdirOutputFile(path=file_path, content=content, metadata=metadata, use_unique_placeholders=False)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError, match="Unclosed file 'file1.txt' at end of content"):
            instance.parse("test_dir")
    assert "Mismatched footer 'file2.txt' for header 'file1.txt', treating as content" in caplog.text
    assert "3 lines to parse" in caplog.text


if __name__ == "__main__":
    pytest.main(["-v", __file__])
