import pytest
from prepdir.main import main
from prepdir.core import init_config
from unittest.mock import patch
import sys
from pathlib import Path
import yaml

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
        "SCRUB_UUIDS": True,
        "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000",
        "SCRUB_HYPHENLESS_UUIDS": True,
    }
    config_file.write_text(yaml.safe_dump(config_content))
    return config_file

@pytest.fixture
def uuid_test_file(tmp_path):
    """Create a test file with UUIDs."""
    file = tmp_path / "test.txt"
    file.write_text("UUID: 12345678-1234-5678-1234-567812345678\nHyphenless: 12345678123456781234567812345678")
    return file

def test_main_version(capsys):
    """Test main() with --version flag."""
    with patch.object(sys, 'argv', ['prepdir', '--version']):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "prepdir 0.13.0" in captured.out

def test_main_no_scrub_hyphenless_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with --no-scrub-hyphenless-uuids preserves hyphenless UUIDs."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '--no-scrub-hyphenless-uuids', '-o', str(output_file), '--config', str(custom_config)]):
        main()
    content = output_file.read_text()
    assert "Hyphenless: 12345678123456781234567812345678" in content
    assert "UUID: 00000000-0000-0000-0000-000000000000" in content

def test_main_default_hyphenless_uuids(tmp_path, capsys, custom_config, uuid_test_file):
    """Test main() with default hyphenless UUID scrubbing from config."""
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '-o', str(output_file), '--config', str(custom_config)]):
        main()
    content = output_file.read_text()
    assert "Hyphenless: 00000000000000000000000000000000" in content
    assert "UUID: 00000000-0000-0000-0000-000000000000" in content

def test_main_init_config(capfd, tmp_path):
    """Test init_config creates a config file."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    init_config(config_path, force=False, stdout=sys.stdout, stderr=sys.stderr)
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
    init_config(config_path, force=True, stdout=sys.stdout, stderr=sys.stderr)
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
        init_config(config_path, force=False, stdout=sys.stdout, stderr=sys.stderr)
    assert exc.value.code == 1
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capfd.readouterr()
    assert f"Error: '{config_path}' already exists. Use force=True to overwrite." in captured.err

def test_main_verbose_mode(tmp_path, capsys, custom_config):
    """Test main() with --verbose logs skipped files."""
    test_file = tmp_path / "test.pyc"
    test_file.write_text("compiled")
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '-v', '--config', str(custom_config)]):
        main()
    captured = capsys.readouterr()
    assert f"Skipping file: {test_file} (excluded in config)" in captured.err

def test_main_custom_replacement_uuid(tmp_path, capsys, custom_config):
    """Test main() with --replacement-uuid uses custom UUID."""
    test_file = tmp_path / "test.txt"
    original_uuid = "12345678-1234-5678-1234-567812345678"
    replacement_uuid = "00000000-0000-0000-0000-000000000000"
    test_file.write_text(f"UUID: {original_uuid}")
    output_file = tmp_path / "prepped_dir.txt"
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '--replacement-uuid', replacement_uuid, '-o', str(output_file), '--config', str(custom_config)]):
        main()
    content = output_file.read_text()
    assert replacement_uuid in content
    assert original_uuid not in content

def test_main_invalid_directory(capsys, tmp_path):
    """Test main() with a non-existent directory."""
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path / "nonexistent")]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Directory" in captured.err