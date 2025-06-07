import sys
from unittest.mock import patch
import pytest
from pathlib import Path
import yaml
from prepdir.main import init_config, main

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