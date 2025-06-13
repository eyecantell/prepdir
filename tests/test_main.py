import sys
from unittest.mock import patch
import pytest
from pathlib import Path
import yaml
from io import StringIO
from prepdir.main import init_config, main, is_prepdir_generated, traverse_directory, scrub_uuids

def test_init_config_success(tmp_path, capsys):
    """Test initializing a new config.yaml."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "as_dict": lambda self: {
            "EXCLUDE": {
                "DIRECTORIES": [".git"],
                "FILES": ["*.pyc"]
            },
            "SCRUB_UUIDS": True,
            "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
        }
    })()):
        init_config(str(config_path), force=False)
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    assert config_path.exists()
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['EXCLUDE']['DIRECTORIES']
    assert '*.pyc' in config['EXCLUDE']['FILES']
    assert config['SCRUB_UUIDS'] is True
    assert config['REPLACEMENT_UUID'] == "00000000-0000-0000-0000-000000000000"

def test_init_config_force_overwrite(tmp_path, capsys):
    """Test initializing with --force when config.yaml exists."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("existing content")
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "as_dict": lambda self: {
            "EXCLUDE": {
                "DIRECTORIES": [".git"],
                "FILES": ["*.pyc"]
            },
            "SCRUB_UUIDS": True,
            "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
        }
    })()):
        init_config(str(config_path), force=True)
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['EXCLUDE']['DIRECTORIES']
    assert '*.pyc' in config['EXCLUDE']['FILES']
    assert config['SCRUB_UUIDS'] is True
    assert config['REPLACEMENT_UUID'] == "00000000-0000-0000-0000-000000000000"

def test_main_init_config(tmp_path, monkeypatch, capsys):
    """Test main with --init option."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    monkeypatch.setattr(sys, 'argv', ['prepdir', '--init', '--config', str(config_path)])
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "as_dict": lambda self: {
            "EXCLUDE": {
                "DIRECTORIES": [".git"],
                "FILES": ["*.pyc"]
            },
            "SCRUB_UUIDS": True,
            "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
        }
    })()):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    assert config_path.exists()
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['EXCLUDE']['DIRECTORIES']
    assert '*.pyc' in config['EXCLUDE']['FILES']
    assert config['SCRUB_UUIDS'] is True
    assert config['REPLACEMENT_UUID'] == "00000000-0000-0000-0000-000000000000"

def test_is_prepdir_generated(tmp_path):
    """Test detection of prepdir-generated files."""
    prepdir_file = tmp_path / "prepped_dir.txt"
    prepdir_file.write_text("File listing generated 2025-06-07 15:04:54.188485 by prepdir (pip install prepdir)\n")
    assert is_prepdir_generated(str(prepdir_file)) is True
    
    non_prepdir_file = tmp_path / "normal.txt"
    non_prepdir_file.write_text("Just some text\n")
    assert is_prepdir_generated(str(non_prepdir_file)) is False
    
    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b'\x00\x01\x02')
    assert is_prepdir_generated(str(binary_file)) is False

def test_scrub_uuids():
    """Test UUID scrubbing functionality with word boundaries."""
    content = """
    Some text with UUID: 123e4567-e89b-12d3-a456-426614174000
    Another UUID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    Not a UUID: 123e4567-e89b-12d3-a456-42661417400
    Embedded UUID: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """
    expected = """
    Some text with UUID: 00000000-0000-0000-0000-000000000000
    Another UUID: 00000000-0000-0000-0000-000000000000
    Not a UUID: 123e4567-e89b-12d3-a456-42661417400
    Embedded UUID: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """
    result = scrub_uuids(content, "00000000-0000-0000-0000-000000000000")
    assert result.strip() == expected.strip()
    
    # Test with custom replacement UUID
    custom_uuid = "11111111-2222-3333-4444-555555555555"
    expected_custom = """
    Some text with UUID: 11111111-2222-3333-4444-555555555555
    Another UUID: 11111111-2222-3333-4444-555555555555
    Not a UUID: 123e4567-e89b-12d3-a456-42661417400
    Embedded UUID: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """
    result_custom = scrub_uuids(content, custom_uuid)
    assert result_custom.strip() == expected_custom.strip()

def test_traverse_directory_scrub_uuids(tmp_path, capsys):
    """Test UUID scrubbing in traverse_directory with word boundaries."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("""
    ID: 123e4567-e89b-12d3-a456-426614174000
    Another: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    Embedded: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """)
    output_file = tmp_path / "output.txt"
    
    # Test default scrubbing
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        traverse_directory(
            str(project_dir),
            extensions=["txt"],
            excluded_dirs=[],
            excluded_files=[],
            include_all=False,
            verbose=True,
            output_file=str(output_file),
            include_prepdir_files=False,
            scrub_uuids_enabled=True,
            replacement_uuid="00000000-0000-0000-0000-000000000000"
        )
    captured = mock_stdout.getvalue()
    assert "ID: 00000000-0000-0000-0000-000000000000" in captured
    assert "Another: 00000000-0000-0000-0000-000000000000" in captured
    assert "Embedded: prefix123e4567-e89b-12d3-a456-426614174000suffix" in captured
    
    # Test disabled scrubbing
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        traverse_directory(
            str(project_dir),
            extensions=["txt"],
            excluded_dirs=[],
            excluded_files=[],
            include_all=False,
            verbose=True,
            output_file=str(output_file),
            include_prepdir_files=False,
            scrub_uuids_enabled=False,
            replacement_uuid="00000000-0000-0000-0000-000000000000"
        )
    captured = mock_stdout.getvalue()
    assert "ID: 123e4567-e89b-12d3-a456-426614174000" in captured
    assert "Another: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" in captured
    assert "Embedded: prefix123e4567-e89b-12d3-a456-426614174000suffix" in captured
    assert "00000000-0000-0000-0000-000000000000" not in captured
    
    # Test custom replacement UUID
    custom_uuid = "11111111-2222-3333-4444-555555555555"
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        traverse_directory(
            str(project_dir),
            extensions=["txt"],
            excluded_dirs=[],
            excluded_files=[],
            include_all=False,
            verbose=True,
            output_file=str(output_file),
            include_prepdir_files=False,
            scrub_uuids_enabled=True,
            replacement_uuid=custom_uuid
        )
    captured = mock_stdout.getvalue()
    assert f"ID: {custom_uuid}" in captured
    assert f"Another: {custom_uuid}" in captured
    assert "Embedded: prefix123e4567-e89b-12d3-a456-426614174000suffix" in captured