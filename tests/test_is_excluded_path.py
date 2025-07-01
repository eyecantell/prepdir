import os
import pytest
from prepdir.is_excluded_path import is_excluded_dir, is_excluded_file

@pytest.fixture
def excluded_dir_patterns():
    """Fixture providing the excluded directory patterns from config.yaml."""
    return [
        '.git',
        '__pycache__',
        '.pdm-build',
        '.venv',
        'venv',
        '.idea',
        'node_modules',
        'dist',
        'build',
        '.pytest_cache',
        '.mypy_cache',
        '.cache',
        '.eggs',
        '.tox',
        '*.egg-info',
        '.ruff_cache',
        'logs'
    ]

@pytest.fixture
def excluded_file_patterns():
    """Fixture providing the excluded file patterns from config.yaml."""
    return [
        '.gitignore',
        '.prepdir/config.yaml',
        '~/.prepdir/config.yaml',
        'LICENSE',
        '.DS_Store',
        'Thumbs.db',
        '.env',
        '.env.production',
        '.coverage',
        'coverage.xml',
        '.pdm-python',
        'pdm.lock',
        '*.pyc',
        '*.pyo',
        '*.log',
        '*.bak',
        '*.swp',
        '**/*.log'
    ]

@pytest.fixture
def base_directory():
    """Fixture providing the base directory for relative path calculations."""
    return '/base/path'

#
# Begin is_excluded_dir testing
#

def test_exact_match_directory(excluded_dir_patterns, base_directory):
    """Test exact match for directory name."""
    assert is_excluded_dir('logs', '/base/path', base_directory, excluded_dir_patterns), "Directory 'logs' should be excluded"
    assert is_excluded_dir('.git', '/base/path', base_directory, excluded_dir_patterns), "Directory '.git' should be excluded"

def test_glob_pattern_match(excluded_dir_patterns, base_directory):
    """Test glob pattern matching for directories like '*.egg-info'."""
    assert is_excluded_dir('my.egg-info', '/base/path', base_directory, excluded_dir_patterns), "Directory 'my.egg-info' should match '*.egg-info'"
    assert is_excluded_dir('project.egg-info', '/base/path', base_directory, excluded_dir_patterns), "Directory 'project.egg-info' should match '*.egg-info'"

def test_parent_directory_exclusion(excluded_dir_patterns, base_directory):
    """Test exclusion when a parent directory matches a pattern."""
    assert is_excluded_dir('c', '/base/path/my/logs/a/b', base_directory, excluded_dir_patterns), "Directory 'my/logs/a/b/c' should be excluded due to 'logs'"
    assert is_excluded_dir('hooks', '/base/path/.git', base_directory, excluded_dir_patterns), "Directory '.git/hooks' should be excluded due to '.git'"

def test_no_substring_match(excluded_dir_patterns, base_directory):
    """Test that patterns like 'logs' don't match substrings like 'mylogsarefun'."""
    assert not is_excluded_dir('mylogsarefun', '/base/path/my', base_directory, excluded_dir_patterns), "Directory 'mylogsarefun' should not match 'logs'"
    assert not is_excluded_dir('a', '/base/path/my/mylogsarefun', base_directory, excluded_dir_patterns), "Directory 'my/mylogsarefun/a' should not be excluded"

def test_empty_relative_path(excluded_dir_patterns, base_directory):
    """Test handling of empty or current directory paths."""
    assert not is_excluded_dir('.', '/base/path', base_directory, excluded_dir_patterns), "Current directory '.' should not be excluded"

def test_single_component_path(excluded_dir_patterns, base_directory):
    """Test single-component paths."""
    assert is_excluded_dir('build', '/base/path', base_directory, excluded_dir_patterns), "Directory 'build' should be excluded"
    assert not is_excluded_dir('src', '/base/path', base_directory, excluded_dir_patterns), "Directory 'src' should not be excluded"

def test_special_characters_in_pattern(excluded_dir_patterns, base_directory):
    """Test patterns with special characters like '.' in '.git'."""
    assert is_excluded_dir('.git', '/base/path', base_directory, excluded_dir_patterns), "Directory '.git' should be excluded"
    assert not is_excluded_dir('dotgitlike', '/base/path', base_directory, excluded_dir_patterns), "Directory 'dotgitlike' should not match '.git'"

def test_nested_glob_pattern(excluded_dir_patterns, base_directory):
    """Test nested directories with glob patterns."""
    assert is_excluded_dir('subdir', '/base/path/my.egg-info', base_directory, excluded_dir_patterns), "Directory 'my.egg-info/subdir' should be excluded due to '*.egg-info'"

def test_empty_excluded_patterns(base_directory):
    """Test behavior with empty excluded patterns list."""
    assert not is_excluded_dir('logs', '/base/path', base_directory, []), "No patterns should result in no exclusions"

def test_trailing_slash_handling(base_directory):
    """Test patterns with trailing slashes are handled correctly."""
    patterns = ['logs/', '.git/']
    assert is_excluded_dir('logs', '/base/path', base_directory, patterns), "Directory 'logs' should be excluded despite trailing slash in pattern"
    assert is_excluded_dir('a', '/base/path/.git', base_directory, patterns), "Directory '.git/a' should be excluded due to '.git/'"

def test_case_sensitivity(excluded_dir_patterns, base_directory):
    """Test case sensitivity in pattern matching."""
    assert not is_excluded_dir('LOGS', '/base/path', base_directory, excluded_dir_patterns), "Directory 'LOGS' should not match 'logs' (case-sensitive)"

#
# Begin is_excluded_file testing
#

def test_exact_match_file(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test exact match for file name."""
    assert is_excluded_file('.gitignore', '/base/path', base_directory, excluded_dir_patterns, excluded_file_patterns), "File '.gitignore' should be excluded"
    assert is_excluded_file('pdm.lock', '/base/path', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'pdm.lock' should be excluded"

def test_glob_pattern_match_file(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test glob pattern matching for files like '*.pyc'."""
    assert is_excluded_file('module.pyc', '/base/path', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'module.pyc' should match '*.pyc'"
    assert is_excluded_file('test.log', '/base/path/my', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'my/test.log' should match '*.log'"

def test_file_in_excluded_directory(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test file exclusion when in an excluded directory."""
    assert is_excluded_file('test.txt', '/base/path/logs', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'logs/test.txt' should be excluded due to 'logs' directory"
    assert is_excluded_file('script.py', '/base/path/my.egg-info', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'my.egg-info/script.py' should be excluded due to '*.egg-info'"

def test_no_substring_match_file(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test that file patterns like '*.log' don't match substrings like 'mylogsarefun.txt'."""
    assert not is_excluded_file('mylogsarefun.txt', '/base/path/my', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'my/mylogsarefun.txt' should not match '*.log'"
    assert not is_excluded_file('notgitignore.txt', '/base/path', base_directory, excluded_dir_patterns, excluded_file_patterns), "File 'notgitignore.txt' should not match '.gitignore'"

def test_home_directory_pattern(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test patterns with '~' like '~/.prepdir/config.yaml'."""
    home_dir = os.path.expanduser("~")
    config_path = os.path.join(home_dir, '.prepdir', 'config.yaml')
    relative_config_path = os.path.relpath(config_path, base_directory)
    assert is_excluded_file('config.yaml', os.path.join(home_dir, '.prepdir'), base_directory, excluded_dir_patterns, excluded_file_patterns), f"File '{relative_config_path}' should be excluded"

def test_empty_excluded_file_patterns(excluded_dir_patterns, base_directory):
    """Test behavior with empty excluded file patterns list."""
    assert not is_excluded_file('test.txt', '/base/path', base_directory, excluded_dir_patterns, []), "No file patterns should not exclude 'test.txt' unless in excluded dir"
    assert is_excluded_file('test.txt', '/base/path/logs', base_directory, excluded_dir_patterns, []), "File 'logs/test.txt' should be excluded due to 'logs' directory"

def test_case_sensitivity_file(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test case sensitivity in file pattern matching."""
    for filename in ["license.txt", "License.txt", "license", "LiCEnSe"]:
        assert not is_excluded_file(filename, '/base/path', base_directory, excluded_dir_patterns, excluded_file_patterns), f"File {filename} should not match 'LICENSE' (case-sensitive)"

def test_contains_excluded_file_pattern(excluded_dir_patterns, base_directory):
    """Test that files are not excluded that contain a file pattern but do not match a file pattern."""
    for filename in ["MYLICENSE", "LICENSE1", "LICENSE.txt"]:
        assert not is_excluded_file(filename, '/base/path', base_directory, excluded_dir_patterns, ["LICENSE"]), f"File {filename} should not match 'LICENSE'"