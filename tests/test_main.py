import pytest
from prepdir.main import main
from unittest.mock import patch
import sys

def test_main_version(capsys):
    with patch.object(sys, 'argv', ['prepdir', '--version']):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "prepdir 0.13.0" in captured.out

def test_main_no_scrub_hyphenless_uuids(tmp_path, capsys):
    """Test main() with --no-scrub-hyphenless-uuids preserves hyphenless UUIDs."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hyphenless: aaaaaaaa1111111111111111aaaaaaaa")
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '--no-scrub-hyphenless-uuids', '-o', str(tmp_path / "prepped_dir.txt")]):
        main()
    content = (tmp_path / "prepped_dir.txt").read_text()
    assert "aaaaaaaa1111111111111111aaaaaaaa" in content
    assert "00000000000000000000000000000000" not in content

def test_main_init_config(capsys, tmp_path):
    """Test main() with --init creates a config file."""
    with patch.object(sys, 'argv', ['prepdir', '--init']):
        with patch('prepdir.core.Path.mkdir'):
            with patch('prepdir.core.Path.exists', return_value=False):  # Mock config doesn't exist
                with patch('prepdir.core.yaml.safe_dump'):
                    main()
    captured = capsys.readouterr()
    assert "Created '.prepdir/config.yaml' with default configuration." in captured.out

def test_main_init_config_force(capsys, tmp_path):
    """Test main() with --init and --force overwrites existing config."""
    with patch.object(sys, 'argv', ['prepdir', '--init', '--force']):
        with patch('prepdir.core.Path.mkdir'):
            with patch('prepdir.core.Path.exists', return_value=True):  # Mock config exists
                with patch('prepdir.core.yaml.safe_dump'):
                    main()
    captured = capsys.readouterr()
    assert "Created '.prepdir/config.yaml' with default configuration." in captured.out

def test_main_init_config_exists(capsys, tmp_path):
    """Test main() with --init fails if config exists without --force."""
    with patch.object(sys, 'argv', ['prepdir', '--init']):
        with patch('prepdir.core.Path.mkdir'):
            with patch('prepdir.core.Path.exists', return_value=True):  # Mock config exists
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error: '.prepdir/config.yaml' already exists. Use force=True to overwrite." in captured.err

def test_main_invalid_directory(capsys, tmp_path):
    """Test main() with a non-existent directory."""
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path / "nonexistent")]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Directory" in captured.err

def test_main_verbose_mode(tmp_path, capsys):
    """Test main() with --verbose logs skipped files."""
    test_file = tmp_path / "test.pyc"
    test_file.write_text("compiled")
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '-v']):
        main()
    captured = capsys.readouterr()
    assert "Skipping file: test.pyc (excluded in config)" in captured.err

def test_main_include_prepdir_files(tmp_path, capsys):
    """Test main() with --include-prepdir-files includes prepdir-generated files."""
    test_file = tmp_path / "prepped_dir.txt"
    test_file.write_text("File listing generated 2025-06-16 01:36:06.139010 by prepdir (pip install prepdir)\ncontent")
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '--include-prepdir-files', '-o', str(tmp_path / "output.txt")]):
        main()
    content = (tmp_path / "output.txt").read_text()
    assert "prepped_dir.txt" in content

def test_main_custom_replacement_uuid(tmp_path, capsys):
    """Test main() with --replacement-uuid uses custom UUID."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("UUID: 11111111-1111-1111-1111-111111111111")
    with patch.object(sys, 'argv', ['prepdir', str(tmp_path), '--replacement-uuid', '22222222-2222-2222-2222-222222222222']):
        main()
    content = (tmp_path / "prepped_dir.txt").read_text()
    assert "22222222-2222-2222-2222-222222222222" in content
    assert "11111111-1111-1111-1111-111111111111" not in content