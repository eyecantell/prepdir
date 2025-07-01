import os
import pytest
from prepdir.is_excluded_path import is_excluded_dir

@pytest.fixture
def excluded_patterns():
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
def base_directory():
    """Fixture providing the base directory for relative path calculations."""
    return '/base/path'

def test_exact_match_directory(excluded_patterns, base_directory):
    """Test exact match for directory name."""
    assert is_excluded_dir('logs', '/base/path', base_directory, excluded_patterns), "Directory 'logs' should be excluded"
    assert is_excluded_dir('.git', '/base/path', base_directory, excluded_patterns), "Directory '.git' should be excluded"

def test_glob_pattern_match(excluded_patterns, base_directory):
    """Test glob pattern matching for directories like '*.egg-info'."""
    assert is_excluded_dir('my.egg-info', '/base/path', base_directory, excluded_patterns), "Directory 'my.egg-info' should match '*.egg-info'"
    assert is_excluded_dir('project.egg-info', '/base/path', base_directory, excluded_patterns), "Directory 'project.egg-info' should match '*.egg-info'"

def test_parent_directory_exclusion(excluded_patterns, base_directory):
    """Test exclusion when a parent directory matches a pattern."""
    assert is_excluded_dir('c', '/base/path/my/logs/a/b', base_directory, excluded_patterns), "Directory 'my/logs/a/b/c' should be excluded due to 'logs'"
    assert is_excluded_dir('hooks', '/base/path/.git', base_directory, excluded_patterns), "Directory '.git/hooks' should be excluded due to '.git'"

def test_no_substring_match(excluded_patterns, base_directory):
    """Test that patterns like 'logs' don't match substrings like 'mylogsarefun'."""
    assert not is_excluded_dir('mylogsarefun', '/base/path/my', base_directory, excluded_patterns), "Directory 'mylogsarefun' should not match 'logs'"
    assert not is_excluded_dir('a', '/base/path/my/mylogsarefun', base_directory, excluded_patterns), "Directory 'my/mylogsarefun/a' should not be excluded"

def test_empty_relative_path(excluded_patterns, base_directory):
    """Test handling of empty or current directory paths."""
    assert not is_excluded_dir('.', '/base/path', base_directory, excluded_patterns), "Current directory '.' should not be excluded"

def test_single_component_path(excluded_patterns, base_directory):
    """Test single-component paths."""
    assert is_excluded_dir('build', '/base/path', base_directory, excluded_patterns), "Directory 'build' should be excluded"
    assert not is_excluded_dir('src', '/base/path', base_directory, excluded_patterns), "Directory 'src' should not be excluded"

def test_special_characters_in_pattern(excluded_patterns, base_directory):
    """Test patterns with special characters like '.' in '.git'."""
    assert is_excluded_dir('.git', '/base/path', base_directory, excluded_patterns), "Directory '.git' should be excluded"
    assert not is_excluded_dir('dotgitlike', '/base/path', base_directory, excluded_patterns), "Directory 'dotgitlike' should not match '.git'"

def test_nested_glob_pattern(excluded_patterns, base_directory):
    """Test nested directories with glob patterns."""
    assert is_excluded_dir('subdir', '/base/path/my.egg-info', base_directory, excluded_patterns), "Directory 'my.egg-info/subdir' should be excluded due to '*.egg-info'"

def test_empty_excluded_patterns(base_directory):
    """Test behavior with empty excluded patterns list."""
    assert not is_excluded_dir('logs', '/base/path', base_directory, []), "No patterns should result in no exclusions"

def test_trailing_slash_handling(base_directory):
    """Test patterns with trailing slashes are handled correctly."""
    patterns = ['logs/', '.git/']
    assert is_excluded_dir('logs', '/base/path', base_directory, patterns), "Directory 'logs' should be excluded despite trailing slash in pattern"
    assert is_excluded_dir('a', '/base/path/.git', base_directory, patterns), "Directory '.git/a' should be excluded due to '.git/'"

def test_case_sensitivity(excluded_patterns, base_directory):
    """Test case sensitivity in pattern matching."""
    assert not is_excluded_dir('LOGS', '/base/path', base_directory, excluded_patterns), "Directory 'LOGS' should not match 'logs' (case-sensitive)"