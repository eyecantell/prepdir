import pytest
import os
import sys
import yaml
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from importlib.metadata import version
from unittest.mock import patch
from prepdir.main import traverse_directory, load_config, init_config, main

@pytest.fixture
def temp_project(tmp_path):
    """Set up a sample project structure for testing."""
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()
    
    # Create files
    (project_dir / "file1.py").write_text("print('Hello')")
    (project_dir / "file2.txt").write_text("Sample text")
    (project_dir / "ignored.custom_config_file_regex_single_star").write_text("single star content")
    
    # Create logs directory with a log file
    logs_dir = project_dir / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.custom_config_file_regex_double_star").write_text("Log entry")
    
    # Create custom_config_dir directory
    config_dir = project_dir / "custom_config_dir"
    config_dir.mkdir()
    (config_dir / "config").write_text("config content")
    
    return project_dir

@pytest.fixture
def custom_config(tmp_path):
    """Create a custom config.yaml for testing."""
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "custom_config.yaml"
    config_path.write_text("""
exclude:
  directories:
    - custom_config_dir
    - "*.custom_config_dir_regex"
  files:
    - "*.custom_config_file_regex_single_star"
    - "**/*.custom_config_file_regex_double_star"
""")
    return config_path

@pytest.fixture
def local_config(tmp_path):
    """Create a local .prepdir/config.yaml for testing."""
    config_dir = tmp_path / ".prepdir"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text("""
exclude:
  directories:
    - config_dir
    - "*.config_dir_regex"
  files:
    - "*.config_file_regex_single_star"
    - "**/*.config_file_regex_double_star"
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
    - config_dir
    - "*.config_dir_regex"
  files:
    - "*.config_file_regex_single_star"
    - "**/*.config_file_regex_double_star"
""")
    return home_dir, config_path

@pytest.fixture
def mock_package_config():
    """Mock the package config.yaml content."""
    config_content = """
exclude:
  directories:
    - .git
    - __pycache__
  files:
    - "*.pyc"
    - "*.log"
"""
    return config_content

def test_traverse_directory_basic(temp_project, tmp_path):
    """Test basic directory traversal and output format."""
    output_file = temp_project / "output.txt"
    output_file.touch()
    with output_file.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                str(temp_project),
                extensions=None,
                excluded_dirs=['custom_config_dir'],
                excluded_files=['*.custom_config_file_regex_single_star', '**/*.custom_config_file_regex_double_star'],
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
    assert "ignored.custom_config_file_regex_single_star" not in content
    assert "app.custom_config_file_regex_double_star" not in content
    assert "custom_config_dir/config" not in content
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
            excluded_dirs=['custom_config_dir', '*.custom_config_dir_regex'],
            excluded_files=['*.custom_config_file_regex_single_star', '**/*.custom_config_file_regex_double_star'],
            include_all=False,
            verbose=True,
            output_file=str(output_file)
        )
    
    stderr_output = stderr_capture.getvalue()
    # Normalize paths for cross-platform compatibility
    temp_project_str = str(temp_project).replace('\\', '/')
    output_file_str = str(output_file).replace('\\', '/')
    assert f"Skipping directory: {temp_project_str}/custom_config_dir (excluded in config)" in stderr_output
    assert f"Skipping file: {temp_project_str}/ignored.custom_config_file_regex_single_star (excluded in config)" in stderr_output
    assert f"Skipping file: {temp_project_str}/logs/app.custom_config_file_regex_double_star (excluded in config)" in stderr_output
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
                excluded_dirs=['custom_config_dir'],
                excluded_files=['*.custom_config_file_regex_single_star', '**/*.custom_config_file_regex_double_star'],
                include_all=False,
                verbose=False,
                output_file=str(output_file)
            )
    
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "print('Hello')" in content
    assert "file2.txt" not in content
    assert "ignored.custom_config_file_regex_single_star" not in content
    assert "app.custom_config_file_regex_double_star" not in content
    assert "custom_config_dir/config" not in content

def test_traverse_directory_include_all(temp_project, tmp_path):
    """Test traversal with --all (ignoring exclusions)."""
    output_file = temp_project / "output.txt"
    output_file.touch()
    with output_file.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                str(temp_project),
                extensions=None,
                excluded_dirs=['custom_config_dir'],
                excluded_files=['*.custom_config_file_regex_single_star', '**/*.custom_config_file_regex_double_star'],
                include_all=True,
                verbose=False,
                output_file=str(output_file)
            )
    
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "Begin File: 'file2.txt'" in content
    assert "Begin File: 'ignored.custom_config_file_regex_single_star'" in content
    assert "Begin File: 'logs/app.custom_config_file_regex_double_star'" in content
    assert "Begin File: 'custom_config_dir/config'" in content
    assert "output.txt" not in content

def test_load_config_missing_file(tmp_path, capsys, mock_package_config):
    """Test loading config when custom file is missing, should fall back to local or package config."""
    config_path = tmp_path / ".prepdir" / "nonexistent.yaml"
    # Mock home directory to ensure no ~/.prepdir/config.yaml
    with patch('pathlib.Path.home', return_value=tmp_path):
        with patch('prepdir.main.get_package_config', return_value=mock_package_config):
            excluded_dirs, excluded_files = load_config(str(config_path))
    captured = capsys.readouterr()
    assert f"Warning: Config file '{config_path}' not found, falling back to other configs." in captured.err
    assert '.git' in excluded_dirs
    assert '__pycache__' in excluded_dirs
    assert '*.pyc' in excluded_files
    assert '*.log' in excluded_files

def test_load_config_missing_file_fallback(tmp_path, capsys):
    """Test loading config when custom and package config fail, should use defaults."""
    config_path = tmp_path / ".prepdir" / "nonexistent.yaml"
    with patch('pathlib.Path.home', return_value=tmp_path):
        with patch('prepdir.main.get_package_config', side_effect=Exception("Resource error")):
            excluded_dirs, excluded_files = load_config(str(config_path))
    captured = capsys.readouterr()
    assert f"Warning: Config file '{config_path}' not found, falling back to other configs." in captured.err
    assert "Warning: Failed to load package config.yaml: Resource error" in captured.err
    assert '.git' in excluded_dirs
    assert '__pycache__' in excluded_dirs
    assert '.pdm-build' in excluded_dirs
    assert '.gitignore' in excluded_files
    assert 'LICENSE' in excluded_files

def test_load_config_custom_file(custom_config, tmp_path):
    """Test loading a custom config file."""
    excluded_dirs, excluded_files = load_config(str(custom_config))
    assert excluded_dirs == ['custom_config_dir', '*.custom_config_dir_regex']
    assert excluded_files == ['*.custom_config_file_regex_single_star', '**/*.custom_config_file_regex_double_star']

def test_load_config_home_directory(home_config, tmp_path, capsys):
    """Test loading config from ~/.prepdir/config.yaml when custom and local configs are missing."""
    home_dir, config_path = home_config
    nonexistent_config = tmp_path / ".prepdir" / "nonexistent.yaml"
    with patch('pathlib.Path.home', return_value=home_dir):
        excluded_dirs, excluded_files = load_config(str(nonexistent_config))
    captured = capsys.readouterr()
    assert f"Warning: Config file '{nonexistent_config}' not found, falling back to other configs." in captured.err
    assert excluded_dirs == ['config_dir', '*.config_dir_regex']
    assert excluded_files == ['*.config_file_regex_single_star', '**/*.config_file_regex_double_star']

def test_load_config_precedence(custom_config, local_config, home_config, tmp_path, mock_package_config):
    """Test configuration precedence: custom > local > global > default."""
    home_dir, home_config_path = home_config
    with patch('pathlib.Path.home', return_value=home_dir):
        with patch('prepdir.main.get_package_config', return_value=mock_package_config):
            # Test 1: Custom config takes precedence
            excluded_dirs, excluded_files = load_config(str(custom_config))
            assert excluded_dirs == ['custom_config_dir', '*.custom_config_dir_regex']
            assert excluded_files == ['*.custom_config_file_regex_single_star', '**/*.custom_config_file_regex_double_star']

            # Test 2: Missing custom config falls back to local config
            nonexistent_config = tmp_path / ".prepdir" / "nonexistent.yaml"
            excluded_dirs, excluded_files = load_config(str(nonexistent_config))
            assert excluded_dirs == ['config_dir', '*.config_dir_regex']
            assert excluded_files == ['*.config_file_regex_single_star', '**/*.config_file_regex_double_star']

            # Test 3: No custom or local config falls back to global config
            # Remove local config file to ensure it doesn't exist
            if local_config.exists():
                local_config.unlink()
            # Change working directory to tmp_path to align Path.cwd() with local_config
            original_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                def mock_exists(self, *args, **kwargs):
                    local_path = str(local_config)
                    self_path = str(self.resolve() if self.is_absolute() else Path.cwd() / self)
                    print(f"Checking exists: self={self_path}, local={local_path}, result={self_path != local_path}", file=sys.stderr)
                    return self_path != local_path
                with patch.object(Path, 'exists', mock_exists):
                    excluded_dirs, excluded_files = load_config(str(nonexistent_config))
                    assert excluded_dirs == ['config_dir', '*.config_dir_regex']
                    assert excluded_files == ['*.config_file_regex_single_star', '**/*.config_file_regex_double_star']
            finally:
                os.chdir(original_cwd)

            # Test 4: No custom, local, or global config falls back to package config
            with patch('pathlib.Path.exists', return_value=False):  # Mock all configs as missing
                with patch('pathlib.Path.home', return_value=tmp_path):  # No home config
                    excluded_dirs, excluded_files = load_config(str(nonexistent_config))
                    assert '.git' in excluded_dirs
                    assert '__pycache__' in excluded_dirs
                    assert '*.pyc' in excluded_files
                    assert '*.log' in excluded_files

def test_init_config_success(tmp_path, capsys, mock_package_config):
    """Test initializing a new config.yaml."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    with patch('prepdir.main.get_package_config', return_value=mock_package_config):
        init_config(str(config_path), force=False)
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    assert config_path.exists()
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['exclude']['directories']
    assert '*.pyc' in config['exclude']['files']

def test_init_config_already_exists(tmp_path, capsys):
    """Test initializing when config.yaml already exists."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("existing content")
    with pytest.raises(SystemExit):
        init_config(str(config_path), force=False)
    captured = capsys.readouterr()
    assert f"Error: '{config_path}' already exists. Use --force to overwrite." in captured.err
    with config_path.open('r', encoding='utf-8') as f:
        assert f.read() == "existing content"

def test_init_config_force_overwrite(tmp_path, capsys, mock_package_config):
    """Test initializing with --force when config.yaml exists."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("existing content")
    with patch('prepdir.main.get_package_config', return_value=mock_package_config):
        init_config(str(config_path), force=True)
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['exclude']['directories']
    assert '*.pyc' in config['exclude']['files']

def test_init_config_package_config_failure(tmp_path, capsys):
    """Test initializing when package config.yaml cannot be read."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    with patch('prepdir.main.get_package_config', side_effect=Exception("Resource error")):
        with pytest.raises(SystemExit):
            init_config(str(config_path), force=False)
    captured = capsys.readouterr()
    assert f"Error: Failed to create '{config_path}': Resource error" in captured.err
    assert not config_path.exists()

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

def test_main_custom_config(temp_project, custom_config, tmp_path, monkeypatch):
    """Test main with a custom config file."""
    output_file = temp_project / "output.txt"
    monkeypatch.setattr(sys, 'argv', ['prepdir', str(temp_project), '--config', str(custom_config), '-o', str(output_file)])
    main()
    content = output_file.read_text()
    assert "Begin File: 'file1.py'" in content
    assert "Begin File: 'file2.txt'" in content
    assert "ignored.custom_config_file_regex_single_star" not in content
    assert "app.custom_config_file_regex_double_star" not in content
    assert "custom_config_dir/config" not in content

def test_main_init_config(tmp_path, monkeypatch, capsys):
    """Test main with --init option."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    monkeypatch.setattr(sys, 'argv', ['prepdir', '--init', '--config', str(config_path)])
    with pytest.raises(SystemExit) as exc_info:
        main()
    captured = capsys.readouterr()
    assert f"Created '{config_path}' with default configuration." in captured.out
    assert exc_info.value.code == 0
    assert config_path.exists()
    with config_path.open('r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    assert '.git' in config['exclude']['directories']
    assert '*.pyc' in config['exclude']['files']

def test_main_init_config_already_exists(tmp_path, monkeypatch, capsys):
    """Test main with --init when config already exists."""
    config_path = tmp_path / ".prepdir" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("existing content")
    monkeypatch.setattr(sys, 'argv', ['prepdir', '--init', '--config', str(config_path)])
    with pytest.raises(SystemExit) as exc_info:
        main()
    captured = capsys.readouterr()
    assert f"Error: '{config_path}' already exists. Use --force to overwrite." in captured.err
    assert exc_info.value.code != 0
    with config_path.open('r', encoding='utf-8') as f:
        assert f.read() == "existing content"