import sys
from unittest.mock import patch
import pytest
from pathlib import Path
import yaml
import logging
from io import StringIO
from prepdir.main import init_config, main, is_prepdir_generated, traverse_directory, scrub_uuids, run, validate_output_file

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
    Some text with UUID: 11111111-1111-1111-1111-111111111111
    Another UUID: aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa
    Not a UUID: 123e4567-e89b-12d3-a456-42661417400
    Embedded UUID: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """
    expected = """
    Some text with UUID: 00000000-0000-0000-0000-000000000000
    Another UUID: 00000000-0000-0000-0000-000000000000
    Not a UUID: 123e4567-e89b-12d3-a456-42661417400
    Embedded UUID: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """
    result_str, result_bool = scrub_uuids(content, "00000000-0000-0000-0000-000000000000")
    assert result_str.strip() == expected.strip()
    assert result_bool == True
    
    # Test with custom replacement UUID
    custom_uuid = "11111111-2222-3333-4444-555555555555"
    expected_custom = f"""
    Some text with UUID: {custom_uuid}
    Another UUID: {custom_uuid}
    Not a UUID: 123e4567-e89b-12d3-a456-42661417400
    Embedded UUID: prefix123e4567-e89b-12d3-a456-426614174000suffix
    """
    result_custom_str, result_custom_bool = scrub_uuids(content, custom_uuid)
    assert result_custom_str.strip() == expected_custom.strip()
    assert result_custom_bool == True

def test_traverse_directory_content(tmp_path, capsys):
    """Test UUID content traversal with directory content."""

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    legit_uuid = "123e4567-e89b-12d3-a456-426614174000"
    test_file.write_text(f"""
    ID: {legit_uuid}
    Another: {legit_uuid}
    Embedded: prefix{legit_uuid}suffix
    """)
    output_file = tmp_path / "output.txt"
    
    replacement_uuid="00000000-0000-0000-0000-000000000000"
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
            replacement_uuid=replacement_uuid
        )
    captured = mock_stdout.getvalue()
    print(f"{captured=}")
    assert f"ID: {replacement_uuid}" in captured
    assert f"Another: {replacement_uuid}" in captured
    assert f"Embedded: prefix{legit_uuid}suffix" in captured
    
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
    print(f"{captured=}")
    assert f"ID: {legit_uuid}" in captured
    assert f"Another: {legit_uuid}" in captured
    assert f"Embedded: prefix{legit_uuid}suffix" in captured
    
    # Test custom replacement UUID
    custom_uuid = "11111111-1111-1111-1111-111111111111"
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

def test_run_success(tmp_path):
    """Test run() function with default parameters."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.py"
    test_file.write_text("print('Hello, World!')\n")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [".git"],
            "exclude.files": ["*.pyc"]
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["py"],
            verbose=False
        )
    
    assert "File listing generated" in content
    assert "Base directory is" in content
    assert "Begin File: 'test.py'" in content
    assert "print('Hello, World!')" in content
    assert "End File: 'test.py'" in content

def test_run_with_output_file(tmp_path):
    """Test run() function with output file."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.py"
    test_file.write_text("print('Hello, World!')\n")
    output_file = tmp_path / "output.txt"
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [".git"],
            "exclude.files": ["*.pyc"]
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["py"],
            output_file=str(output_file),
            verbose=False
        )
    
    assert output_file.exists()
    with output_file.open('r', encoding='utf-8') as f:
        file_content = f.read()
    assert "File listing generated" in file_content
    assert "Base directory is" in file_content
    assert "Begin File: 'test.py'" in file_content
    assert "print('Hello, World!')" in file_content
    assert "End File: 'test.py'" in file_content
    assert file_content == content

def test_run_uuid_scrubbing(tmp_path):
    """Test run() function with UUID scrubbing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("ID: 123e4567-e89b-12d3-a456-426614174000\n")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": [],
            "SCRUB_UUIDS": True,
            "REPLACEMENT_UUID": "00000000-0000-0000-0000-000000000000"
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["txt"],
            scrub_uuids=True,
            replacement_uuid="00000000-0000-0000-0000-000000000000",
            verbose=False
        )
    
    assert "ID: 00000000-0000-0000-0000-000000000000" in content
    assert "123e4567-e89b-12d3-a456-426614174000" not in content

def test_run_no_uuid_scrubbing(tmp_path):
    """Test run() function without UUID scrubbing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("ID: 123e4567-e89b-12d3-a456-426614174000\n")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": [],
            "SCRUB_UUIDS": False
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["txt"],
            scrub_uuids=False,
            verbose=False
        )
    
    assert "ID: 123e4567-e89b-12d3-a456-426614174000" in content
    assert "00000000-0000-0000-0000-000000000000" not in content

def test_run_invalid_directory(tmp_path):
    """Test run() function with invalid directory."""
    invalid_dir = tmp_path / "nonexistent"
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {}
    })()):
        with pytest.raises(ValueError) as exc_info:
            run(directory=str(invalid_dir))
        assert f"Directory '{invalid_dir}' does not exist." in str(exc_info.value)

def test_run_invalid_uuid(tmp_path, caplog):
    """Test run() function with invalid replacement UUID."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("ID: 123e4567-e89b-12d3-a456-426614174000\n")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": []
        }.get(key, default)
    })()):
        with caplog.at_level(logging.ERROR):
            content = run(
                directory=str(project_dir),
                extensions=["txt"],
                scrub_uuids=True,
                replacement_uuid="invalid-uuid",
                verbose=True
            )
    
    assert "Invalid replacement UUID: 'invalid-uuid'. Using default nil UUID." in caplog.text
    assert "ID: 00000000-0000-0000-0000-000000000000" in content

def test_run_include_prepdir_files(tmp_path):
    """Test run() function with include_prepdir_files option."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    prepdir_file = project_dir / "prepped_dir.txt"
    prepdir_file.write_text("File listing generated 2025-06-07 15:04:54.188485 by prepdir (pip install prepdir)\n")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": []
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["txt"],
            include_prepdir_files=True,
            verbose=False
        )
    
    assert "Begin File: 'prepped_dir.txt'" in content
    assert "File listing generated" in content
    assert "End File: 'prepped_dir.txt'" in content

def test_validate_output_file_valid(tmp_path):
    """Test validate_output_file with a valid prepdir output file."""
    output_file = tmp_path / "prepped_dir.txt"
    content = """File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=
# My Project
This is a sample project.
=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=
"""
    output_file.write_text(content, encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is True
    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 0

def test_validate_output_file_missing_footer(tmp_path):
    """Test validate_output_file with a missing footer."""
    output_file = tmp_path / "prepped_dir.txt"
    content = """File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
"""
    output_file.write_text(content, encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert "Line 3: Header for 'src/main.py' has no matching footer." in result["errors"]
    assert len(result["warnings"]) == 0

def test_validate_output_file_unmatched_footer(tmp_path):
    """Test validate_output_file with an unmatched footer."""
    output_file = tmp_path / "prepped_dir.txt"
    content = """File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/other.py' =-=-=-=-=-=-=-=
"""
    output_file.write_text(content, encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert "Line 5: Footer for 'src/other.py' does not match open header 'src/main.py' from line 3." in result["errors"]
    assert len(result["warnings"]) == 0

def test_validate_output_file_missing_header(tmp_path):
    """Test validate_output_file with a missing header."""
    output_file = tmp_path / "prepped_dir.txt"
    content = """File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
"""
    output_file.write_text(content, encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert "Line 4: Footer for 'src/main.py' without matching header." in result["errors"]
    assert len(result["warnings"]) == 0

def test_validate_output_file_invalid_header(tmp_path):
    """Test validate_output_file with an invalid prepdir header."""
    output_file = tmp_path / "prepped_dir.txt"
    content = """Invalid header
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
"""
    output_file.write_text(content, encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert "Line 1: Missing or invalid prepdir header. Got: 'Invalid header'" in result["errors"]
    assert len(result["warnings"]) == 0

def test_validate_output_file_malformed_delimiter(tmp_path):
    """Test validate_output_file with a malformed delimiter."""
    output_file = tmp_path / "prepped_dir.txt"
    content = """File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
=-=-=- Begin File: 'src/main.py' =-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
"""
    output_file.write_text(content, encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    print(f"{result=}")
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
    assert "Line 5: Footer for 'src/main.py' without matching header." in result["errors"]

def test_validate_output_file_empty(tmp_path):
    """Test validate_output_file with an empty file."""
    output_file = tmp_path / "prepped_dir.txt"
    output_file.write_text("", encoding='utf-8')
    
    result = validate_output_file(str(output_file))
    assert result["is_valid"] is False
    assert "File is empty." in result["errors"]
    assert len(result["warnings"]) == 0

def test_validate_output_file_nonexistent(tmp_path):
    """Test validate_output_file with a nonexistent file."""
    output_file = tmp_path / "nonexistent.txt"
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_output_file(str(output_file))
    assert f"File '{output_file}' does not exist." in str(exc_info.value)

def test_validate_output_file_invalid_encoding(tmp_path):
    """Test validate_output_file with a binary file."""
    output_file = tmp_path / "binary.bin"
    output_file.write_bytes(b'\x00\x01\x02')
    result = validate_output_file(str(output_file))
    print(f"{result=}")
    assert result["is_valid"] == False
    assert "Missing or invalid prepdir header" in result["errors"][0]

def test_run_config_uuid_scrubbing(tmp_path):
    """Test run() function respects SCRUB_UUIDS from config.yaml."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("ID: 123e4567-e89b-12d3-a456-426614174000\n")
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES: []
SCRUB_UUIDS: true
REPLACEMENT_UUID: "11111111-0000-0000-0000-000000000000"
""")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": [],
            "SCRUB_UUIDS": True,
            "REPLACEMENT_UUID": "11111111-0000-0000-0000-000000000000"
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["txt"],
            config_path=str(config_path),
            verbose=False
        )
    
    assert "ID: 11111111-0000-0000-0000-000000000000" in content
    assert "123e4567-e89b-12d3-a456-426614174000" not in content

def test_run_config_no_uuid_scrubbing(tmp_path):
    """Test run() function respects SCRUB_UUIDS: false from config.yaml."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("ID: 123e4567-e89b-12d3-a456-426614174000\n")
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES: []
SCRUB_UUIDS: false
REPLACEMENT_UUID: "11111111-0000-0000-0000-000000000000"
""")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": [],
            "SCRUB_UUIDS": False,
            "REPLACEMENT_UUID": "11111111-0000-0000-0000-000000000000"
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["txt"],
            config_path=str(config_path),
            verbose=False
        )
    
    assert "ID: 123e4567-e89b-12d3-a456-426614174000" in content
    assert "11111111-0000-0000-0000-000000000000" not in content

def test_run_config_uuid_override(tmp_path):
    """Test run() function overrides config.yaml UUID settings with arguments."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    test_file = project_dir / "test.txt"
    test_file.write_text("ID: 123e4567-e89b-12d3-a456-426614174000\n")
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("""
EXCLUDE:
  DIRECTORIES: []
  FILES: []
SCRUB_UUIDS: true
REPLACEMENT_UUID: "11111111-0000-0000-0000-000000000000"
""")
    
    with patch("prepdir.main.load_config", return_value=type("MockDynaconf", (), {
        "get": lambda self, key, default=None: {
            "exclude.directories": [],
            "exclude.files": [],
            "SCRUB_UUIDS": True,
            "REPLACEMENT_UUID": "11111111-0000-0000-0000-000000000000"
        }.get(key, default)
    })()):
        content = run(
            directory=str(project_dir),
            extensions=["txt"],
            config_path=str(config_path),
            scrub_uuids=False,
            replacement_uuid="22222222-0000-0000-0000-000000000000",
            verbose=False
        )
    
    assert "ID: 123e4567-e89b-12d3-a456-426614174000" in content
    assert "11111111-0000-0000-0000-000000000000" not in content
    assert "22222222-0000-0000-0000-000000000000" not in content