import sys
import json
import pytest
import yaml
import logging
import os
from contextlib import redirect_stderr
from unittest.mock import patch
from importlib.metadata import PackageNotFoundError
from prepdir import (
    run,
    scrub_uuids,
    validate_output_file,
    is_prepdir_generated,
    display_file_content,
    traverse_directory,
)
from prepdir.main import configure_logging
from prepdir.core import init_config, __version__


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set TEST_ENV=true for all tests to skip real config loading."""
    monkeypatch.setenv("TEST_ENV", "true")


@pytest.fixture
def uuid_test_file(tmp_path):
    """Create a test file with UUIDs."""
    file = tmp_path / "test.txt"
    file.write_text("UUID: 12345678-1234-5678-1234-567812345678\nHyphenless: 12345678123456781234567812345678")
    return file


def test_run_loglevel_debug(tmp_path, monkeypatch, caplog):
    """Test run() function with LOGLEVEL=DEBUG, ensuring debug logs are recorded."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, world!")
    monkeypatch.setenv("LOGLEVEL", "DEBUG")
    configure_logging()
    caplog.set_level(logging.DEBUG, logger="prepdir")
    content, _ = run(directory=str(tmp_path), config_path=str(tmp_path / "nonexistent_config.yaml"))
    logs = caplog.text
    assert "Running prepdir on directory: " in logs
    assert "Set logging level to DEBUG" in logs
    assert "Hello, world!" in content


def test_run_with_config(tmp_path):
    """Test run() function with a custom config file overriding default settings."""
    test_file = tmp_path / "test.txt"
    test_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    test_file.write_text(f"Sample UUID: {test_uuid}")
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES: ['.prepdir/config.yaml']
SCRUB_UUIDS: False
REPLACEMENT_UUID: 123e4567-e89b-12d3-a456-426614174000
""")
    content, _ = run(directory=str(tmp_path), config_path=str(config_file))
    assert test_uuid in content
    assert "123e4567-e89b-12d3-a456-426614174000" not in content


def test_scrub_hyphenless_uuids():
    """Test UUID scrubbing for hyphen-less UUIDs."""
    content = """
    Hyphenated: 11111111-1111-1111-1111-111111111111
    Hyphenless: aaaaaaaa111111111111111111111111
    """
    expected = """
    Hyphenated: 00000000-0000-0000-0000-000000000000
    Hyphenless: 00000000000000000000000000000000
    """
    result_str, result_bool, _, _ = scrub_uuids(content, "00000000-0000-0000-0000-000000000000", scrub_hyphenless=True)
    assert result_str.strip() == expected.strip()
    assert result_bool is True


def test_run_excludes_global_config(tmp_path, monkeypatch):
    """Test that ~/.prepdir/config.yaml is excluded by default."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config_path.write_text("sensitive: data")
    monkeypatch.setenv("HOME", str(home_dir))
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES:
    - ~/.prepdir/config.yaml
SCRUB_UUIDS: True
REPLACEMENT_UUID: "00000000-0000-0000-0000-000000000000"
""")
    with monkeypatch.context() as m:
        m.setenv("TEST_ENV", "true")
        content, _ = run(directory=str(home_dir), config_path=str(config_file))
    assert "sensitive: data" not in content
    assert ".prepdir/config.yaml" not in content


def test_run_excludes_global_config_bundled(tmp_path, monkeypatch):
    """Test that ~/.prepdir/config.yaml is excluded using bundled config."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config_path.write_text(yaml.safe_dump({"sensitive": "data"}))
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("TEST_ENV", "true")
    bundled_config_dir = tmp_path / "src" / "prepdir"
    bundled_config_dir.mkdir(parents=True)
    bundled_path = bundled_config_dir / "config.yaml"
    bundled_path.write_text(
        yaml.safe_dump(
            {
                "EXCLUDE": {"DIRECTORIES": [], "FILES": ["~/.prepdir/config.yaml"]},
                "SCRUB_UUIDS": True,
                "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000",
            }
        )
    )
    if (tmp_path / ".prepdir").exists():
        import shutil

        shutil.rmtree(tmp_path / ".prepdir")
    content, _ = run(directory=str(home_dir), config_path=str(bundled_path))
    assert "sensitive: data" not in content
    assert ".prepdir/config.yaml" not in content


def test_run_invalid_directory(tmp_path):
    """Test run() with a non-existent directory raises ValueError."""
    with pytest.raises(ValueError, match="Directory '.*' does not exist"):
        run(directory=str(tmp_path / "nonexistent"))


def test_run_non_directory(tmp_path):
    """Test run() with a file instead of a directory raises ValueError."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("content")
    with pytest.raises(ValueError, match="'.*' is not a directory"):
        run(directory=str(test_file))


def test_run_empty_directory(tmp_path):
    """Test run() with an empty directory outputs 'No files found'."""
    content, _ = run(directory=str(tmp_path))
    assert "No files found." in content


def test_run_with_extensions_no_match(tmp_path):
    """Test run() with extensions that don't match any files."""
    test_file = tmp_path / "test.bin"
    test_file.write_text("binary")
    content, _ = run(directory=str(tmp_path), extensions=["py", "txt"])
    assert "No files with extension(s) py, txt found." in content


def test_version_fallback(monkeypatch):
    """Test __version__ fallback when package metadata is unavailable."""
    monkeypatch.setattr("prepdir.core.version", lambda *args, **kwargs: (_ for _ in ()).throw(PackageNotFoundError))
    import importlib

    importlib.reload(sys.modules["prepdir.core"])
    assert sys.modules["prepdir.core"].__version__ == "0.13.0"


def test_scrub_uuids_verbose_logs(caplog, uuid_test_file):
    """Test UUID scrubbing logs with verbose=True."""
    caplog.set_level(logging.DEBUG, logger="prepdir")
    with open(uuid_test_file, "r", encoding="utf-8") as f:
        content = f.read()
    result_str, result_bool, _, _ = scrub_uuids(
        content, "00000000-0000-0000-0000-000000000000", scrub_hyphenless=True, verbose=True
    )
    assert result_bool is True
    logs = caplog.text
    assert "Scrubbed 1 hyphenated UUID(s): ['12345678-1234-5678-1234-567812345678']" in logs
    assert "Scrubbed 1 hyphen-less UUID(s): ['12345678123456781234567812345678']" in logs


def test_scrub_uuids_no_matches():
    """Test scrub_uuids() with content containing no UUIDs."""
    content = "No UUIDs here"
    result_str, result_bool, _, _ = scrub_uuids(content, "00000000-0000-0000-0000-000000000000")
    assert result_str == content
    assert result_bool is False


def test_is_prepdir_generated_exceptions(tmp_path, monkeypatch):
    """Test is_prepdir_generated handles exceptions."""
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\xff")
    assert is_prepdir_generated(str(test_file)) is False
    with monkeypatch.context() as m:
        m.setattr("builtins.open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Permission denied")))
        assert is_prepdir_generated(str(test_file)) is False


def test_init_config_permission_denied(tmp_path, capfd, monkeypatch):
    """Test init_config handles permission errors."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    monkeypatch.setattr(
        "pathlib.Path.open", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("No access"))
    )
    with pytest.raises(SystemExit) as exc:
        init_config(config_path, force=False, stdout=sys.stdout, stderr=sys.stderr)
    assert exc.value.code == 1
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capfd.readouterr()
    assert f"Error: Failed to create '{config_path}': No access" in captured.err


def test_traverse_directory_uuid_notes(tmp_path, capsys):
    """Test traverse_directory prints UUID scrubbing notes."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    traverse_directory(
        str(tmp_path),
        excluded_files=[],
        scrub_uuids_enabled=True,
        scrub_hyphenless_uuids_enabled=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000",
    )
    captured = capsys.readouterr()
    assert (
        "Note: Valid UUIDs in file contents will be scrubbed and replaced with '00000000-0000-0000-0000-000000000000'."
        in captured.out
    )
    assert (
        "Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with '00000000000000000000000000000000'."
        in captured.out
    )


def test_run_uuid_mapping_unique_placeholders(tmp_path):
    """Test run() returns correct UUID mapping with unique placeholders."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("UUID: 12345678-1234-5678-1234-567812345678\nHyphenless: aaaaaaaa111111111111111111111111")
    content, uuid_mapping = run(
        directory=str(tmp_path), scrub_uuids=True, scrub_hyphenless_uuids=True, use_unique_placeholders=True
    )
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content
    assert "PREPDIR_UUID_PLACEHOLDER_2" in content
    assert uuid_mapping == {
        "PREPDIR_UUID_PLACEHOLDER_1": "12345678-1234-5678-1234-567812345678",
        "PREPDIR_UUID_PLACEHOLDER_2": "aaaaaaaa111111111111111111111111",
    }
    assert content.count("PREPDIR_UUID_PLACEHOLDER_1") == 1
    assert content.count("PREPDIR_UUID_PLACEHOLDER_2") == 1


def test_run_uuid_mapping_no_placeholders(tmp_path):
    """Test run() with use_unique_placeholders=False uses replacement_uuid."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("UUID: 12345678-1234-5678-1234-567812345678\nHyphenless: aaaaaaaa111111111111111111111111")
    replacement_uuid = "00000000-0000-0000-0000-000000000000"
    content, uuid_mapping = run(
        directory=str(tmp_path),
        scrub_uuids=True,
        scrub_hyphenless_uuids=True,
        replacement_uuid=replacement_uuid,
        use_unique_placeholders=False,
    )
    assert replacement_uuid in content
    assert replacement_uuid.replace("-", "") in content
    assert uuid_mapping == {}
    # Extract file content section to avoid counting header notes
    file_content = content.split("Begin File: 'test.txt'")[1].split("End File: 'test.txt'")[0]
    assert file_content.count(replacement_uuid) == 1  # Hyphenated UUID replacement in file content
    assert file_content.count(replacement_uuid.replace("-", "")) == 1  # Hyphen-less UUID replacement in file content


def test_run_uuid_mapping_no_uuids(tmp_path):
    """Test run() returns empty UUID mapping when no UUIDs are found."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("No UUIDs here")
    content, uuid_mapping = run(
        directory=str(tmp_path), scrub_uuids=True, scrub_hyphenless_uuids=True, use_unique_placeholders=True
    )
    assert "No UUIDs here" in content
    assert uuid_mapping == {}
    assert not any(
        f"PREPDIR_UUID_PLACEHOLDER_{i}" in content for i in range(1, 10)
    )  # Check no placeholders in file content


def test_run_uuid_mapping_multiple_files(tmp_path):
    """Test run() correctly maps UUIDs across multiple files."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("UUID: 11111111-1111-1111-1111-111111111111")
    file2 = tmp_path / "file2.txt"
    file2.write_text("Hyphenless: aaaaaaaa222222222222222222222222")
    content, uuid_mapping = run(
        directory=str(tmp_path), scrub_uuids=True, scrub_hyphenless_uuids=True, use_unique_placeholders=True
    )
    assert "PREPDIR_UUID_PLACEHOLDER_1" in content
    assert "PREPDIR_UUID_PLACEHOLDER_2" in content
    assert uuid_mapping == {
        "PREPDIR_UUID_PLACEHOLDER_1": "11111111-1111-1111-1111-111111111111",
        "PREPDIR_UUID_PLACEHOLDER_2": "aaaaaaaa222222222222222222222222",
    }
    assert content.count("PREPDIR_UUID_PLACEHOLDER_1") == 1
    assert content.count("PREPDIR_UUID_PLACEHOLDER_2") == 1


# =============================================================================
# IMPROVED validate_output_file TESTS
# =============================================================================


def test_validate_output_file_empty_file(tmp_path):
    """Test validate_output_file with an empty file."""
    output_file = tmp_path / "empty.txt"
    output_file.write_text("")
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "File is empty." in result["errors"][0]
    assert result["warnings"] == []
    assert result["files"] == {}


def test_validate_output_file_valid_complete(tmp_path):
    """Test validate_output_file with a valid, complete prepdir output."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0 (pip install prepdir)\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'file1.txt' =-=-=-=-=-=-=-=\n"
        "Content of file1\n"
        "Line 2\n"
        "=-=-=-=-=-=-=-= End File: 'file1.txt' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'file2.py' =-=-=-=-=-=-=-=\n"
        "print('hello')\n"
        "=-=-=-=-=-=-=-= End File: 'file2.py' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"file1.txt": "Content of file1\nLine 2", "file2.py": "print('hello')"}


def test_validate_output_file_missing_base_directory(tmp_path):
    """Test validate_output_file with missing base directory line."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert len(result["warnings"]) == 1
    assert "Missing or invalid base directory line" in result["warnings"][0]
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_unmatched_footer(tmp_path):
    """Test validate_output_file with footer without matching header."""
    output_file = tmp_path / "invalid.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Footer for 'test.txt' without matching header" in result["errors"][0]
    assert result["files"] == {}


def test_validate_output_file_unclosed_header(tmp_path):
    """Test validate_output_file with header that has no matching footer."""
    output_file = tmp_path / "invalid.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content without footer\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Header for 'test.txt' has no matching footer" in result["errors"][0]
    assert result["files"] == {"test.txt": "content without footer"}


def test_validate_output_file_malformed_delimiters(tmp_path):
    """Test validate_output_file with malformed header/footer delimiters."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File:\n"  # Missing filename in header
        "content\n"
        "=-=-=-=-=-=-=-= End File:\n"  # Missing filename in footer
        "=-=-=-=-=-=-=-= Begin File: 'good.txt' =-=-=-=-=-=-=-=\n"
        "good content\n"
        "=-=-=-=-=-=-=-= End File: 'good.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))

    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert any("Malformed header" in error for error in result["errors"])
    assert any("Malformed footer" in error for error in result["errors"])
    assert len(result["warnings"]) == 0
    assert result["files"] == {"good.txt": "good content"}


def test_validate_output_file_large_file(tmp_path):
    """Test validate_output_file with a large file to ensure performance."""
    output_file = tmp_path / "large.txt"
    content = "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\nBase directory is '/test'\n"
    # Generate a large file with 10,000 lines across 10 files
    for i in range(10):
        content += f"=-=-=-=-=-=-=-= Begin File: 'file{i}.txt' =-=-=-=-=-=-=-=\n"
        content += "\n".join(f"Line {j}" for j in range(1000)) + "\n"
        content += f"=-=-=-=-=-=-=-= End File: 'file{i}.txt' =-=-=-=-=-=-=-=\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert len(result["files"]) == 10
    for i in range(10):
        assert f"file{i}.txt" in result["files"]
        assert result["files"][f"file{i}.txt"].count("\n") == 999  # 1000 lines minus one for joining


def test_validate_output_file_empty_files(tmp_path):
    """Test validate_output_file with files that have no content."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'empty.txt' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= End File: 'empty.txt' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'whitespace.txt' =-=-=-=-=-=-=-=\n"
        "   \n"
        "\t\n"
        "=-=-=-=-=-=-=-= End File: 'whitespace.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"]["empty.txt"] == ""
    assert result["files"]["whitespace.txt"] == "   \n\t"


def test_validate_output_file_with_blank_lines(tmp_path):
    """Test validate_output_file preserves blank lines within file content."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "line 1\n"
        "\n"
        "line 3\n"
        "\n"
        "\n"
        "line 6\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    expected_content = "line 1\n\nline 3\n\n\nline 6"
    assert result["files"]["test.txt"] == expected_content
    assert result["files"]["test.txt"].count("\n") == 5


def test_validate_output_file_unicode_error(tmp_path):
    """Test validate_output_file handles UnicodeDecodeError."""
    output_file = tmp_path / "invalid.bin"
    output_file.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(UnicodeDecodeError, match="Invalid encoding"):
        validate_output_file(str(output_file))


def test_validate_output_file_file_not_found(tmp_path):
    """Test validate_output_file with non-existent file."""
    with pytest.raises(FileNotFoundError, match="File '.*' does not exist"):
        validate_output_file(str(tmp_path / "nonexistent.txt"))


def test_validate_output_file_multiple_files_complex(tmp_path):
    """Test validate_output_file with multiple files and complex content."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 12:00:00.000000 by prepdir version 0.13.0\n"
        "Base directory is '/complex/test'\n"
        "Note: Valid UUIDs in file contents will be scrubbed\n"
        "\n"
        "=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=\n"
        "#!/usr/bin/env python3\n"
        "def main():\n"
        "    print('Hello, World!')\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
        "=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=\n"
        "# Project Title\n"
        "\n"
        "This is a sample project.\n"
        "\n"
        "## Usage\n"
        "\n"
        "```bash\n"
        "python main.py\n"
        "```\n"
        "=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=\n"
        "=-=-=-=-=-=-=-= Begin File: 'config.json' =-=-=-=-=-=-=-=\n"
        "{\n"
        '  "name": "test",\n'
        '  "version": "1.0.0"\n'
        "}\n"
        "=-=-=-=-=-=-=-= End File: 'config.json' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert len(result["files"]) == 3
    assert "def main():" in result["files"]["src/main.py"]
    assert "# Project Title" in result["files"]["README.md"]
    assert '"name": "test"' in result["files"]["config.json"]
    assert result["files"]["src/main.py"].count("\n") == 5
    assert result["files"]["README.md"].count("\n") == 8
    assert result["files"]["config.json"].count("\n") == 3


def test_validate_output_file_malformed_timestamp(tmp_path):
    """Test validate_output_file with a malformed timestamp in header."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-13-99 25:99:99.999999 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_missing_version(tmp_path):
    """Test validate_output_file with missing version in header."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_mismatched_header_footer(tmp_path):
    """Test validate_output_file with mismatched header and footer."""
    output_file = tmp_path / "invalid.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'file1.txt' =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: 'file2.txt' =-=-=-=-=-=-=-=\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 2
    assert "Footer for 'file2.txt' does not match open header 'file1.txt'" in result["errors"][0]
    assert "Header for 'file1.txt' has no matching footer" in result["errors"][1]
    assert result["files"] == {"file1.txt": "content"}


def test_validate_output_file_partial_content(tmp_path):
    """Test validate_output_file with partial file content (incomplete delimiters)."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\n"
        "partial content\n"
        "incomplete delimiter =-=-=-\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Header for 'test.txt' has no matching footer" in result["errors"][0]
    assert result["files"] == {"test.txt": "partial content\nincomplete delimiter =-=-=-"}


def test_validate_output_file_lenient_delimiters(tmp_path):
    """Test validate_output_file with lenient delimiters (various =/- combinations and whitespace)."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'file1.txt' ===\n"  # Short delimiter, equal signs
        "Content of file1\n"
        "--- End File: 'file1.txt' ---\n"  # Short delimiter, dashes
        "=-=-=  Begin File: 'file2.py'  =-=-=\n"  # Mixed delimiter with extra whitespace
        "print('hello')\n"
        "===== End File: 'file2.py' =====\n"  # Equal signs only
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"file1.txt": "Content of file1", "file2.py": "print('hello')"}


def test_validate_output_file_lenient_delimiters_with_extra_whitespace(tmp_path):
    """Test validate_output_file with lenient delimiters and excessive whitespace."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "==-==-==   Begin File: 'test.txt'    ==--==\n"  # Mixed delimiter, extra spaces
        "content\n"
        "--==--   End File: 'test.txt'   --==--\n"  # Mixed delimiter, extra spaces
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_mixed_lenient_malformed_delimiters(tmp_path):
    """Test validate_output_file with a mix of lenient and malformed delimiters."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"  # Valid lenient delimiter
        "content\n"
        "=== End File: 'test.txt' =--=\n"  # Valid lenient delimiters
        "==- Begin File:\n"  # Malformed header (no filename) - expect this to generate an error
        "malformed content\n"
        "--==-- End File: 'other.txt' ---\n"  # Valid footer but no matching header  - expect this to generate an error
        "===== Begin File: 'valid.txt' ====-\n"  # Valid lenient delimiter
        "valid content\n"
        "=== End File: 'valid.txt' ---\n"  # Valid lenient delimiter
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    print(f"{result['errors']=}")
    print(f"{result['warnings']=}")

    assert result["is_valid"] is False
    assert len(result["errors"]) == 2
    assert any("Footer for 'other.txt' without matching header" in error for error in result["errors"])
    assert any("Malformed header" in error for error in result["errors"])
    assert len(result["warnings"]) == 0
    assert result["files"] == {"test.txt": "content", "valid.txt": "valid content"}


def test_validate_output_file_lenient_header_variations(tmp_path):
    """Test validate_output_file with variations in generated header."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010\n"  # No version or pip
        "Base directory is '/test'\n"
        "==-== Begin File: 'test.txt' ==-==\n"
        "content\n"
        "==--== End File: 'test.txt' ==--==\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_single_character_delimiters(tmp_path):
    """Test validate_output_file with single-character delimiters."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "= Begin File: 'test.txt' =\n"  # Single = delimiter is not recognized
        "content\n"
        "- End File: 'test.txt' -\n"  # Single - delimiter is not recognized
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is False
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {} 


def test_validate_output_file_first_line_header(tmp_path):
    """Test validate_output_file with a header on the first line."""
    output_file = tmp_path / "output.txt"
    content = "=== Begin File: 'test.txt' ===\ncontent\n=== End File: 'test.txt' ===\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert any(
        "Missing or invalid file listing header" in warning for warning in result["warnings"]
    )  # No generated header
    assert result["files"] == {"test.txt": "content"}


def test_validate_output_file_creation_complete_header(tmp_path):
    """Test validate_output_file parses complete generated header into creation dict."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06.139876 by prepdir version 0.13.0 (pip install prepdir)\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"
        "content\n"
        "=== End File: 'test.txt' ===\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {"date": "2025-06-16 01:36:06.139876", "creator": "prepdir", "version": "0.13.0"}


def test_validate_output_file_creation_no_version(tmp_path):
    """Test validate_output_file parses header with no version into creation dict."""
    output_file = tmp_path / "output.txt"
    content = (
        "File listing generated 2025-06-16 01:36:06 by some-tool\n"
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"
        "content\n"
        "=== End File: 'test.txt' ===\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {"date": "2025-06-16 01:36:06", "creator": "some-tool", "version": "unknown"}

def test_validate_output_file_creation_starts_with_basedir(tmp_path):
    """Test validate_output_file parses header with base dir header but no main header line into creation dict."""
    output_file = tmp_path / "output.txt"
    content = (
        "Base directory is '/test'\n"
        "=== Begin File: 'test.txt' ===\n"
        "content\n"
        "=== End File: 'test.txt' ===\n"
    )
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert len(result['warnings']) == 1
    assert any("Missing or invalid file listing header" in warning for warning in result["warnings"])
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] == {
        "date": "unknown",
        "creator": "unknown",
        "version": "unknown"
    }


def test_validate_output_file_creation_no_header(tmp_path): # PRW current fails
    """Test validate_output_file with no generated header returns empty creation dict."""
    output_file = tmp_path / "output.txt"
    content = "=== Begin File: 'test.txt' ===\ncontent\n=== End File: 'test.txt' ===\n"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    print(f"result is:\n{json.dumps(result, indent=4)}")
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert any("Missing or invalid file listing header" in warning for warning in result["warnings"])
    assert result["files"] == {"test.txt": "content"}
    assert result["creation"] ==  {
        "date": "unknown",
        "creator": "unknown",
        "version": "unknown"
    }
