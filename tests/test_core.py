from io import StringIO
import pytest
from contextlib import redirect_stderr
from prepdir import run, scrub_uuids, validate_output_file
from prepdir.main import configure_logging
import logging
import yaml

@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set TEST_ENV=true for all tests to skip real config loading."""
    monkeypatch.setenv("TEST_ENV", "true")
    
def test_run_loglevel_debug(tmp_path, monkeypatch, caplog):
    """
    Test run() function with LOGLEVEL=DEBUG, ensuring debug logs are captured.
    """
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, world!")

    # Set LOGLEVEL to DEBUG
    monkeypatch.setenv("LOGLEVEL", "DEBUG")

    # Configure logging explicitly
    configure_logging()

    # Set caplog to capture DEBUG level logs
    caplog.set_level(logging.DEBUG, logger="prepdir")

    # Run prepdir on the temporary directory
    content = run(
        directory=str(tmp_path),
        config_path=str(tmp_path / "nonexistent_config.yaml")  # Ensure default config is used
    )

    # Check for expected debug log messages
    logs = caplog.text
    assert "Running prepdir on directory: " in logs, "Debug log message not found"
    assert "Set logging level to DEBUG" in logs
    assert "Hello, world!" in content

def test_run_with_config(tmp_path):
    """
    Test run() function with a custom config file overriding default settings.
    """
    # Create a test file with a UUID
    test_file = tmp_path / "test.txt"
    test_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    test_file.write_text(f"Sample UUID: {test_uuid}")

    # Create a custom config file
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES: ['.prepdir/config.yaml']  # Exclude the config file itself
SCRUB_UUIDS: false
REPLACEMENT_UUID: 123e4567-e89b-12d3-a456-426614174000
""")

    # Run prepdir with the custom config
    content = run(
        directory=str(tmp_path),
        config_path=str(config_file)
    )

    # Verify that UUIDs were not scrubbed (SCRUB_UUIDS: false)
    assert test_uuid in content
    assert "123e4567-e89b-12d3-a456-426614174000" not in content

def test_scrub_hyphenless_uuids():
    """Test UUID scrubbing for hyphen-less UUIDs."""
    content = """
    Hyphenated: 11111111-1111-1111-1111-111111111111
    Hyphenless: aaaaaaaa1111111111111111aaaaaaaa
    """
    expected = """
    Hyphenated: 00000000-0000-0000-0000-000000000000
    Hyphenless: 00000000000000000000000000000000
    """
    result_str, result_bool = scrub_uuids(content, "00000000-0000-0000-0000-000000000000", scrub_hyphenless=True)
    assert result_str.strip() == expected.strip()
    assert result_bool == True

def test_run_excludes_global_config(tmp_path, monkeypatch):
    """Test that ~/.prepdir/config.yaml is excluded by default."""
    # Create temporary home directory with global config
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config_path.write_text("sensitive: data")
    
    # Set HOME environment variable
    monkeypatch.setenv("HOME", str(home_dir))
    
    # Create a custom config that mirrors the bundled config's exclusions
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES:
    - ~/.prepdir/config.yaml
SCRUB_UUIDS: true
REPLACEMENT_UUID: "00000000-0000-0000-0000-000000000000"
""")
    
    # Set TEST_ENV=true to skip default configs
    with monkeypatch.context() as m:
        m.setenv("TEST_ENV", "true")
        content = run(directory=str(home_dir), config_path=str(config_file))
    
    # Verify that global config content and path are not included
    assert "sensitive: data" not in content
    assert ".prepdir/config.yaml" not in content



def test_run_excludes_global_config_bundled(tmp_path, monkeypatch):
    """Test that ~/.prepdir/config.yaml is excluded using bundled config."""
    # Create temporary home directory with global config
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    global_config_path = home_dir / ".prepdir" / "config.yaml"
    global_config_path.parent.mkdir()
    global_config_path.write_text(yaml.safe_dump({"sensitive": "data"}))

    # Set HOME environment variable
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("TEST_ENV", "true")  # Skip default config loading

    # Create a temporary bundled config file
    bundled_config_dir = tmp_path / "src" / "prepdir"
    bundled_config_dir.mkdir(parents=True)
    bundled_config_path = bundled_config_dir / "config.yaml"
    bundled_config_path.write_text(yaml.safe_dump({
        "EXCLUDE": {
            "DIRECTORIES": [],
            "FILES": ["~/.prepdir/config.yaml"]
        },
        "SCRUB_UUIDS": True,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
    }))

    # Ensure no local config exists in tmp_path
    if (tmp_path / ".prepdir").exists():
        import shutil
        shutil.rmtree(tmp_path / ".prepdir")

    # Run prepdir with the temporary bundled config
    content = run(directory=str(home_dir), config_path=str(bundled_config_path))

    # Verify that global config content and path are not included
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

def test_scrub_uuids_no_matches():
    """Test scrub_uuids() with content containing no UUIDs."""
    content = "No UUIDs here"
    result_str, result_bool = scrub_uuids(content, "00000000-0000-0000-0000-000000000000")
    assert result_str == content
    assert result_bool is False

def test_validate_output_file_invalid(tmp_path):
    """Test validate_output_file() with an invalid file structure."""
    output_file = tmp_path / "invalid.txt"
    output_file.write_text("""
File listing generated 2025-06-16 01:36:06.139010 by prepdir (pip install prepdir)
Base directory is '/test'
=-=-=-=-=-=-=-= Begin File: 'test.txt' =-=-=-=-=-=-=-=
content
""")  # Missing footer
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert any("Header for 'test.txt' has no matching footer" in err for err in result["errors"])

def test_validate_output_file_empty(tmp_path):
    """Test validate_output_file() with an empty file."""
    output_file = tmp_path / "empty.txt"
    output_file.write_text("")
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert "File is empty." in result["errors"]