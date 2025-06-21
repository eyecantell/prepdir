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
