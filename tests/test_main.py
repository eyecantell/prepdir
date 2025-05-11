import pytest
import os
import sys
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from importlib.metadata import version
from unittest.mock import patch
from prepdir.main import traverse_directory, load_config, main

@pytest.fixture
def temp_project(tmp_path):
    """Set up a sample project structure for testing."""
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()
    
    # Create files
    (project_dir / "file1.py").write_text("print('Hello')")
    (project_dir / "file2.txt").write_text("Sample text")
    (project_dir / "ignored.pyc").write_text("binary")
    
    # Create logs directory with a log file
    logs_dir = project_dir / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.log").write_text("Log entry")
    
    # Create .git directory
    git_dir = project_dir / "git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config")
    
    return project_dir

@pytest.fixture
def custom_config(tmp_path):
    """Create a custom config.yaml for testing."""
    config_path = tmp_path / "custom_config.yaml"
    config_path.write_text("""
exclude:
  directories:
    - git
    - "*.egg-info"
  files:
    - "*.pyc"
    - "**/*.log"
""")
    return config_path

@pytest.fixture
def home_config(tmp_path):
    """Create a config.yaml in a mocked home directory for testing."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_dir = home_dir / ".prepdir"
    config_dir.mkdir()
    config_path = config_dir / "config.yaml"
    config_path.write_text("""
exclude:
  directories:
    - git
    - node_modules
  files:
    - "*.pyc"
    - "*.bak"
""")
    return home_dir, config_path

def test_traverse_directory_basic(temp_project, tmp_path):
    """Test basic directory traversal and output format."""
    output_file = temp_project / "output.txt"
    output_file.touch()
    with output_file.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                str(temp_project),
                extensions=None,
                excluded_dirs=['git'],
                excluded_files=['*.pyc', '**/*.log'],
                include_all=False,
                verbose=False,
                output_file=str(output_file)
            )
    
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "print('Hello')" in content
    assert "End File: 'file1.py'" in content
    assert "Begin File: 'file2.txt'" in content
    assert "Sample text" in content
    assert "End File: 'file2.txt'" in content
    assert "ignored.pyc" not in content
    assert "app.log" not in content
    assert "git/config" not in content
    assert "output.txt" not in content

def test_traverse_directory_verbose(temp_project, tmp_path):
    """Test verbose logging for skipped files and directories."""
    output_file = temp_project / "output.txt"
    output_file.touch()
    stderr_capture = StringIO()
    with output_file.open('w', encoding='utf-8') as f, redirect_stdout(f), redirect_stderr(stderr_capture):
        traverse_directory(
            str(temp_project),
            extensions=None,
            excluded_dirs=['git', '*.egg-info'],
            excluded_files=['*.pyc', '**/*.log'],
            include_all=False,
            verbose=True,
            output_file=str(output_file)
        )
    
    stderr_output = stderr_capture.getvalue()
    # Normalize paths for cross-platform compatibility
    temp_project_str = str(temp_project).replace('\\', '/')
    output_file_str = str(output_file).replace('\\', '/')
    assert f"Skipping directory: {temp_project_str}/git (excluded in config)" in stderr_output
    assert f"Skipping file: {temp_project_str}/ignored.pyc (excluded in config)" in stderr_output
    assert f"Skipping file: {temp_project_str}/logs/app.log (excluded in config)" in stderr_output
    assert f"Skipping file: {output_file_str} (output file)" in stderr_output

def test_traverse_directory_with_extensions(temp_project, tmp_path):
    """Test filtering by file extensions."""
    output_file = temp_project / "output.txt"
    output_file.touch()
    with output_file.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                str(temp_project),
                extensions=['py'],
                excluded_dirs=['git'],
                excluded_files=['*.pyc', '**/*.log'],
                include_all=False,
                verbose=False,
                output_file=str(output_file)
            )
    
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "print('Hello')" in content
    assert "file2.txt" not in content
    assert "ignored.pyc" not in content
    assert "app.log" not in content
    assert "git/config" not in content

def test_traverse_directory_include_all(temp_project, tmp_path):
    """Test traversal with --all (ignoring exclusions)."""
    output_file = temp_project / "output.txt"
    output_file.touch()
    with output_file.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                str(temp_project),
                extensions=None,
                excluded_dirs=['git'],
                excluded_files=['*.pyc', '**/*.log'],
                include_all=True,
                verbose=False,
                output_file=str(output_file)
            )
    
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "Begin File: 'file2.txt'" in content
    assert "Begin File: 'ignored.pyc'" in content
    assert "Begin File: 'logs/app.log'" in content
    assert "Begin File: 'git/config'" in content
    assert "output.txt" not in content

def test_load_config_missing_file(tmp_path):
    """Test loading config when file is missing."""
    config_path = tmp_path / "nonexistent.yaml"
    excluded_dirs, excluded_files = load_config(str(config_path))
    assert excluded_dirs == ['.git', '__pycache__', '.pdm-build']
    assert excluded_files == ['.gitignore', 'LICENSE']

def test_load_config_custom_file(custom_config, tmp_path):
    """Test loading a custom config file."""
    excluded_dirs, excluded_files = load_config(str(custom_config))
    assert excluded_dirs == ['git', '*.egg-info']
    assert excluded_files == ['*.pyc', '**/*.log']

def test_load_config_home_directory(home_config, tmp_path):
    """Test loading config from ~/.prepdir/config.yaml."""
    home_dir, config_path = home_config
    with patch('pathlib.Path.home', return_value=home_dir):
        excluded_dirs, excluded_files = load_config(str(tmp_path / "nonexistent.yaml"))
    assert excluded_dirs == ['git', 'node_modules']
    assert excluded_files == ['*.pyc', '*.bak']

def test_main_version(monkeypatch, capsys):
    """Test the --version option."""
    monkeypatch.setattr(sys, 'argv', ['prepdir', '--version'])
    with pytest.raises(SystemExit):
        main()
    captured = capsys.readouterr()
    assert captured.out.strip() == f"prepdir {version('prepdir')}"

def test_main_invalid_directory(tmp_path, monkeypatch, capsys):
    """Test error handling for invalid directory."""
    invalid_dir = tmp_path / "nonexistent"
    monkeypatch.setattr(sys, 'argv', ['prepdir', str(invalid_dir)])
    with pytest.raises(SystemExit):
        main()
    captured = capsys.readouterr()
    assert f"Error: Directory '{invalid_dir}' does not exist." in captured.err

def test_main_empty_directory(tmp_path, tmp_path_factory, monkeypatch):
    """Test traversal of an empty directory."""
    empty_dir = tmp_path_factory.mktemp("empty")
    output_file = tmp_path / "output.txt"
    monkeypatch.setattr(sys, 'argv', ['prepdir', str(empty_dir), '-o', str(output_file)])
    main()
    content = output_file.read_text()
    assert "No files found." in content

def test_main_custom_config(temp_project, custom_config, tmp_path, monkeypatch):
    """Test main with a custom config file."""
    output_file = temp_project / "output.txt"
    monkeypatch.setattr(sys, 'argv', ['prepdir', str(temp_project), '--config', str(custom_config), '-o', str(output_file)])
    main()
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "Begin File: 'file2.txt'" in content
    assert "ignored.pyc" not in content
    assert "app.log" not in content
    assert "git/config" not in content