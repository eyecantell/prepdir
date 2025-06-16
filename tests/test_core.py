import sys
from io import StringIO
import pytest
import yaml
import logging
import os
from contextlib import redirect_stderr
from unittest.mock import patch
from importlib.metadata import PackageNotFoundError
from prepdir import run, scrub_uuids, validate_output_file, is_prepdir_generated, display_file_content, traverse_directory
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
    content = run(directory=str(tmp_path), config_path=str(tmp_path / "nonexistent_config.yaml"))
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
    content = run(directory=str(tmp_path), config_path=str(config_file))
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
    result_str, result_bool = scrub_uuids(content, "00000000-0000-0000-0000-000000000000", scrub_hyphenless=True)
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
        content = run(directory=str(home_dir), config_path=str(config_file))
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
    bundled_path.write_text(yaml.safe_dump({
        "EXCLUDE": {
            "DIRECTORIES": [],
            "FILES": ["~/.prepdir/config.yaml"]
        },
        "SCRUB_UUIDS": True,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
    }))
    if (tmp_path / ".prepdir").exists():
        import shutil
        shutil.rmtree(tmp_path / ".prepdir")
    content = run(directory=str(home_dir), config_path=str(bundled_path))
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
    content = run(directory=str(tmp_path))
    assert "No files found." in content

def test_run_with_extensions_no_match(tmp_path):
    """Test run() with extensions that don't match any files."""
    test_file = tmp_path / "test.bin"
    test_file.write_text("binary")
    content = run(directory=str(tmp_path), extensions=["py", "txt"])
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
    with open(uuid_test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    result_str, result_bool = scrub_uuids(
        content,
        "00000000-0000-0000-0000-000000000000",
        scrub_hyphenless=True,
        verbose=True
    )
    assert result_bool is True
    logs = caplog.text
    assert "Scrubbed 1 hyphenated UUID(s): ['12345678-1234-5678-1234-567812345678']" in logs
    assert "Scrubbed 1 hyphen-less UUID(s): ['12345678123456781234567812345678']" in logs

def test_scrub_uuids_no_matches():
    """Test scrub_uuids() with content containing no UUIDs."""
    content = "No UUIDs here"
    result_str, result_bool = scrub_uuids(content, "00000000-0000-0000-0000-000000000000")
    assert result_str == content
    assert result_bool is False

def test_is_prepdir_generated_exceptions(tmp_path, monkeypatch):
    """Test is_prepdir_generated handles exceptions."""
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\xFF")
    assert is_prepdir_generated(str(test_file)) is False
    with monkeypatch.context() as m:
        m.setattr("builtins.open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Permission denied")))
        assert is_prepdir_generated(str(test_file)) is False

def test_init_config_permission_denied(tmp_path, capfd, monkeypatch):
    """Test init_config handles permission errors."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    monkeypatch.setattr("pathlib.Path.open", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("No access")))
    with pytest.raises(SystemExit) as exc:
        init_config(config_path, force=False, stdout=sys.stdout, stderr=sys.stderr)
    assert exc.value.code == 1
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capfd.readouterr()
    assert f"Error: Failed to create '{config_path}': No access" in captured.err

@pytest.mark.parametrize("content,expected_error_substring", [
    ("", "File is empty"),
    ("File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\nBase directory is '/test'\n=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=", "Footer for 'test.txt' without matching header"),
    ("Invalid header\nBase directory is '/test'\n=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\ncontent\n=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=", "Missing or invalid prepdir header"),
    ("File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\nBase directory is '/test'\n=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=\ncontent", "Header for 'test.txt' has no matching footer"),
])
def test_validate_output_file_cases(tmp_path, content, expected_error_substring):
    """Test validate_output_file with various invalid cases."""
    output_file = tmp_path / "output.txt"
    output_file.write_text(content)
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert any(expected_error_substring in error for error in result["errors"]), f"Expected '{expected_error_substring}' in errors: {result['errors']}"

def test_validate_output_file_unicode_error(tmp_path):
    """Test validate_output_file handles UnicodeDecodeError."""
    output_file = tmp_path / "invalid.bin"
    output_file.write_bytes(b"\xFF\xFE")
    with pytest.raises(UnicodeDecodeError):
        validate_output_file(str(output_file))

def test_validate_output_file_invalid_header_and_warnings(tmp_path):
    """Test validate_output_file with malformed header."""
    output_file = tmp_path / "invalid.txt"
    output_file.write_text(
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0 (pip install prepdir)\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= Begin File: test.txt =-=-=-=-=-=-=-=\n"
        "content\n"
        "=-=-=-=-=-=-=-= End File: test.txt =-=-=-=-=-=-=-=\n"
    )
    result = validate_output_file(str(output_file))
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
    assert result["is_valid"] is True
    assert any("Malformed header" in warning for warning in result["warnings"])

def test_validate_output_file_footer_no_header(tmp_path):
    """Test validate_output_file with footer but no header."""
    output_file = tmp_path / "invalid.txt"
    output_file.write_text(
        "File listing generated 2025-06-16 01:36:06.139010 by prepdir version 0.13.0\n"
        "Base directory is '/test'\n"
        "=-=-=-=-=-=-=-= End File: 'test.txt' =-=-=-=-=-=-=-=\n"
    )
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert any("Footer for 'test.txt' without matching header" in error for error in result["errors"])

def test_traverse_directory_uuid_notes(tmp_path, capsys):
    """Test traverse_directory prints UUID scrubbing notes."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    traverse_directory(
        str(tmp_path),
        excluded_files=[],
        scrub_uuids_enabled=True,
        scrub_hyphenless_uuids_enabled=True,
        replacement_uuid="00000000-0000-0000-0000-000000000000"
    )
    captured = capsys.readouterr()
    assert "Note: Valid UUIDs in file contents will be scrubbed and replaced with '00000000-0000-0000-0000-000000000000'." in captured.out
    assert "Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with '00000000-0000-0000-0000-000000000000'." in captured.out