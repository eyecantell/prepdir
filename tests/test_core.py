from io import StringIO
from contextlib import redirect_stderr
from prepdir import run, init_config, validate_output_file, configure_logging
import logging

# tests/test_core.py
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