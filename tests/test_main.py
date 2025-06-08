import sys
from unittest.mock import patch
import pytest
from pathlib import Path
import yaml
from prepdir.main import init_config, main, is_prepdir_generated

def test_init_config_success(tmp_path, capsys):
    """Test initializing a new config.yaml."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "as_dict": lambda self: {
            "EXCLUDE": {
                "DIRECTORIES": [".git"],
                "FILES": ["*.pyc"]
            }
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
            }
        }
    })()):
        init_config(str(config_path), force=True)
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['EXCLUDE']['DIRECTORIES']
    assert '*.pyc' in config['EXCLUDE']['FILES']

def test_main_init_config(tmp_path, monkeypatch, capsys):
    """Test main with --init option."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    monkeypatch.setattr(sys, 'argv', ['prepdir', '--init', '--config', str(config_path)])
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "as_dict": lambda self: {
            "EXCLUDE": {
                "DIRECTORIES": [".git"],
                "FILES": ["*.pyc"]
            }
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