import pytest
from prepdir.main import main, run
from prepdir.config import init_config
from unittest.mock import patch
import sys
import yaml
import logging

HYPHENATED_UUID = "87654321-abcd-0000-0000-eeeeeeeeeeee"
UNHYPHENATED_UUID = "87654321abcd00000000ffffffffffff"
REPLACEMENT_UUID = "12340000-1234-0000-0000-000000000000"

@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset logger levels to avoid interference."""
    logging.getLogger("prepdir.prepdir_processor").setLevel(logging.NOTSET)
    logging.getLogger("prepdir.prepdir_output_file").setLevel(logging.NOTSET)
    logging.getLogger("prepdir.prepdir_file_entry").setLevel(logging.NOTSET)
    yield

@pytest.fixture
def custom_config(tmp_path):
    """Create a custom config file with exclusions for tests."""
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_content = {
        "EXCLUDE": {
            "DIRECTORIES": [],
            "FILES": ["*.pyc"],
        },
        "SCRUB_HYPHENATED_UUIDS": True,
        "REPLACEMENT_UUID": REPLACEMENT_UUID,
        "SCRUB_HYPHENLESS_UUIDS": True,
    }
    config_file.write_text(yaml.safe_dump(config_content))
    return config_file

@pytest.fixture
def uuid_test_file(tmp_path):
    """Create a test file with UUIDs."""
    file = tmp_path / "test.txt"
    file.write_text(f"UUID: {HYPHENATED_UUID}\nHyphenless: {UNHYPHENATED_UUID}")
    return file

def test_main_version(capsys):
    """Test main() with --version flag."""
    with patch.object(sys, "argv", ["prepdir", "--version"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    from importlib.metadata import version
    assert "prepdir " + version("prepdir") in captured.out

def test_main_no_scrub_hyphenless_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with --no-scrub-hyphenless-uuids preserves hyphenless UUIDs."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--no-scrub-hyphenless-uuids",
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    print(f"content is: \n{content}")
    assert f"Hyphenless: {UNHYPHENATED_UUID}" in content  # Hyphenless UUID should be unchanged
    assert f"UUID: {REPLACEMENT_UUID}" in content

def test_main_default_hyphenless_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with default hyphenless UUID scrubbing from config."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(sys, "argv", ["prepdir", str(tmp_path), "-o", str(output_file), "--config", str(custom_config)]):
        main()
    content = output_file.read_text()
    assert f"Hyphenless: {str(REPLACEMENT_UUID).replace('-', '')}" in content
    assert f"UUID: {REPLACEMENT_UUID}" in content

def test_main_init_config(capfd, tmp_path):
    """Test init_config creates a config file."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    init_config("prepdir", config_path, force=False, stdout=sys.stdout, stderr=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capfd.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    assert config_path.exists()

def test_main_init_config_force(capfd, tmp_path):
    """Test init_config with force=True overwrites existing config."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text("existing: content")
    init_config("prepdir", config_path, force=True, stdout=sys.stdout, stderr=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capfd.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    assert config_path.exists()
    content = config_path.read_text()
    assert "EXCLUDE" in content

def test_main_init_config_exists(capfd, tmp_path):
    """Test init_config fails if config exists without force=True."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text("existing: content")
    with pytest.raises(SystemExit) as exc:
        init_config("prepdir", config_path, force=False, stdout=sys.stdout, stderr=sys.stderr)
    assert exc.value.code == 1
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capfd.readouterr()
    assert f"Error: '{config_path}' already exists. Use force=True to overwrite." in captured.err

def test_main_verbose_mode(tmp_path, capsys, custom_config, caplog):
    """Test main() with --verbose logs skipped files."""
    test_file = tmp_path / "test.pyc"
    test_file.write_text("compiled")
    with caplog.at_level(logging.INFO, logger="prepdir"):
        with patch.object(sys, "argv", ["prepdir", str(tmp_path), "-v", "--config", str(custom_config)]):
            main()
    print(f"caplog.text is:\n{caplog.text}")
    assert "Starting prepdir in" in caplog.text
    assert "Skipping file: test.pyc (excluded in config)" in caplog.text

def test_main_custom_replacement_uuid(tmp_path, capsys, custom_config):
    """Test main() with --replacement-uuid uses custom UUID."""
    test_file = tmp_path / "test.txt"
    original_uuid = "12345678-1234-5678-1234-567812345678"
    replacement_uuid = "abcd1234-0000-0000-0000-000000000000"
    test_file.write_text(f"UUID: {original_uuid}")
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(
        sys,
        "argv",
        [
            "prepdir",
            str(tmp_path),
            "--replacement-uuid",
            replacement_uuid,
            "-o",
            str(output_file),
            "--config",
            str(custom_config),
        ],
    ):
        main()
    content = output_file.read_text()
    assert replacement_uuid in content
    assert original_uuid not in content

def test_main_invalid_directory(caplog, tmp_path):
    """Test main() with a non-existent directory."""
    with patch.object(sys, "argv", ["prepdir", str(tmp_path / "nonexistent")]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    assert "Error: Directory" in caplog.text