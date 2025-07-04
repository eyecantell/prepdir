import os
import pytest
from prepdir.is_excluded_file import is_excluded_dir, is_excluded_file


@pytest.fixture
def excluded_dir_patterns():
    """Fixture providing the excluded directory patterns from config.yaml."""
    return [
        ".git",
        "__pycache__",
        ".pdm-build",
        ".venv",
        "venv",
        ".idea",
        "node_modules",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".cache",
        ".eggs",
        ".tox",
        "*.egg-info",
        ".ruff_cache",
        "logs",
    ]


@pytest.fixture
def excluded_file_patterns():
    """Fixture providing the excluded file patterns from config.yaml."""
    return [
        ".gitignore",
        ".prepdir/config.yaml",
        "~/.prepdir/config.yaml",
        "LICENSE",
        ".DS_Store",
        "Thumbs.db",
        ".env",
        ".env.production",
        ".coverage",
        "coverage.xml",
        ".pdm-python",
        "pdm.lock",
        "*.pyc",
        "*.pyo",
        "*.log",
        "*.bak",
        "*.swp",
        "**/*.log",
        "my*.txt",
        "src/**/test_*",
    ]


@pytest.fixture
def base_directory():
    """Fixture providing the base directory for relative path calculations."""
    return "/base/path"


@pytest.fixture
def exact_file_patterns():
    """Fixture for exact-match file patterns."""
    return [".gitignore", "pdm.lock", "LICENSE"]


@pytest.fixture
def glob_file_patterns():
    """Fixture for glob-based file patterns."""
    return ["*.pyc", "*.log", "my*.txt"]


@pytest.fixture
def recursive_glob_patterns():
    """Fixture for recursive glob patterns."""
    return ["**/*.log", "src/**/test_*"]


#
# Begin is_excluded_dir testing
#


def test_exact_match_directory(base_directory):
    """Test exact match for directory name."""
    patterns = ["logs", ".git"]
    assert is_excluded_dir("logs", "/base/path", base_directory, patterns), "Directory 'logs' should be excluded"
    assert is_excluded_dir(".git", "/base/path", base_directory, patterns), "Directory '.git' should be excluded"


def test_glob_pattern_match(base_directory):
    """Test glob pattern matching for directories like '*.egg-info'."""
    patterns = ["*.egg-info"]
    assert is_excluded_dir("my.egg-info", "/base/path", base_directory, patterns), (
        "Directory 'my.egg-info' should match '*.egg-info'"
    )
    assert is_excluded_dir("project.egg-info", "/base/path", base_directory, patterns), (
        "Directory 'project.egg-info' should match '*.egg-info'"
    )


def test_parent_directory_exclusion(base_directory):
    """Test exclusion when a parent directory matches a pattern."""
    patterns = ["logs", ".git"]
    assert is_excluded_dir("c", "/base/path/my/logs/a/b", base_directory, patterns), (
        "Directory 'my/logs/a/b/c' should be excluded due to 'logs'"
    )
    assert is_excluded_dir("hooks", "/base/path/.git", base_directory, patterns), (
        "Directory '.git/hooks' should be excluded due to '.git'"
    )


def test_no_substring_match(base_directory):
    """Test that patterns like 'logs' don't match substrings like 'mylogsarefun'."""
    patterns = ["logs"]
    assert not is_excluded_dir("mylogsarefun", "/base/path/my", base_directory, patterns), (
        "Directory 'mylogsarefun' should not match 'logs'"
    )
    assert not is_excluded_dir("a", "/base/path/my/mylogsarefun", base_directory, patterns), (
        "Directory 'my/mylogsarefun/a' should not be excluded"
    )


def test_empty_relative_path(base_directory):
    """Test handling of empty or current directory paths."""
    assert not is_excluded_dir(".", "/base/path", base_directory, []), "Current directory '.' should not be excluded"


def test_single_component_path(base_directory):
    """Test single-component paths."""
    patterns = ["build"]
    assert is_excluded_dir("build", "/base/path", base_directory, patterns), "Directory 'build' should be excluded"
    assert not is_excluded_dir("src", "/base/path", base_directory, patterns), "Directory 'src' should not be excluded"


def test_special_characters_in_pattern(base_directory):
    """Test patterns with special characters like '.' in '.git'."""
    patterns = [".git"]
    assert is_excluded_dir(".git", "/base/path", base_directory, patterns), "Directory '.git' should be excluded"
    assert not is_excluded_dir("dotgitlike", "/base/path", base_directory, patterns), (
        "Directory 'dotgitlike' should not match '.git'"
    )


def test_nested_glob_pattern(base_directory):
    """Test nested directories with glob patterns."""
    patterns = ["*.egg-info"]
    assert is_excluded_dir("subdir", "/base/path/my.egg-info", base_directory, patterns), (
        "Directory 'my.egg-info/subdir' should be excluded due to '*.egg-info'"
    )


def test_empty_excluded_patterns(base_directory):
    """Test behavior with empty excluded patterns list."""
    assert not is_excluded_dir("logs", "/base/path", base_directory, []), "No patterns should result in no exclusions"


def test_trailing_slash_handling(base_directory):
    """Test patterns with trailing slashes are handled correctly."""
    patterns = ["logs/", ".git/"]
    assert is_excluded_dir("logs", "/base/path", base_directory, patterns), (
        "Directory 'logs' should be excluded despite trailing slash in pattern"
    )
    assert is_excluded_dir("a", "/base/path/.git", base_directory, patterns), (
        "Directory '.git/a' should be excluded due to '.git/'"
    )


def test_case_sensitivity(base_directory):
    """Test case sensitivity in directory pattern matching."""
    patterns = ["logs"]
    assert not is_excluded_dir("LOGS", "/base/path", base_directory, patterns), (
        "Directory 'LOGS' should not match 'logs' (case-sensitive)"
    )


def test_path_component_match(base_directory):
    """Test that non-glob patterns match as path components."""
    patterns = ["logs", ".git"]
    assert is_excluded_dir("a", "/base/path/my/logs", base_directory, patterns), (
        "Directory 'my/logs/a' should be excluded due to 'logs' in path"
    )
    assert is_excluded_file("test.txt", "/base/path/my/.git", base_directory, patterns, []), (
        "File 'my/.git/test.txt' should be excluded due to '.git' in path"
    )


#
# Begin is_excluded_file testing
#


def test_exact_match_file(exact_file_patterns, base_directory):
    """Test exact match for file name."""
    assert is_excluded_file(".gitignore", "/base/path", base_directory, [], exact_file_patterns), (
        "File '.gitignore' should be excluded"
    )
    assert is_excluded_file("pdm.lock", "/base/path", base_directory, [], exact_file_patterns), (
        "File 'pdm.lock' should be excluded"
    )


def test_glob_pattern_match_file(glob_file_patterns, base_directory):
    """Test glob pattern matching for files like '*.pyc'."""
    assert is_excluded_file("module.pyc", "/base/path", base_directory, [], glob_file_patterns), (
        "File 'module.pyc' should match '*.pyc'"
    )
    assert is_excluded_file("test.log", "/base/path/my", base_directory, [], glob_file_patterns), (
        "File 'my/test.log' should match '*.log'"
    )
    assert is_excluded_file("myfile.txt", "/base/path", base_directory, [], glob_file_patterns), (
        "File 'myfile.txt' should match 'my*.txt'"
    )


def test_file_in_excluded_directory(base_directory):
    """Test file exclusion when in an excluded directory."""
    dir_patterns = ["logs", "*.egg-info"]
    assert is_excluded_file("test.txt", "/base/path/logs", base_directory, dir_patterns, []), (
        "File 'logs/test.txt' should be excluded due to 'logs' directory"
    )
    assert is_excluded_file("script.py", "/base/path/my.egg-info", base_directory, dir_patterns, []), (
        "File 'my.egg-info/script.py' should be excluded due to '*.egg-info'"
    )


def test_no_substring_match_file(exact_file_patterns, glob_file_patterns, base_directory):
    """Test that file patterns like '*.log' or 'LICENSE' don't match substrings like 'mylogsarefun.txt' or 'LICENSE.txt'."""
    patterns = exact_file_patterns + glob_file_patterns
    print(f"{patterns=}")
    assert is_excluded_file("mylogsarefun.txt", "/base/path/my", base_directory, [], patterns), (
        "File 'my/mylogsarefun.txt' should match my*.txt pattern"
    )
    assert not is_excluded_file("yourlogsarefun.txt", "/base/path/my", base_directory, [], patterns), (
        "File 'my/yourlogsarefun.txt' should not match any pattern"
    )
    assert is_excluded_file("mylogsarefun.log", "/base/path/my", base_directory, [], patterns), (
        "File 'my/mylogsarefun.log' should match '*.log'"
    )
    assert not is_excluded_file("notgitignore.txt", "/base/path", base_directory, [], patterns), (
        "File 'notgitignore.txt' should not match '.gitignore'"
    )
    for filename in ["LICENSE.txt", "MYLICENSE", "LICENSE1"]:
        assert not is_excluded_file(filename, "/base/path", base_directory, [], patterns), (
            f"File '{filename}' should not match 'LICENSE'"
        )


def test_home_directory_pattern(base_directory):
    """Test patterns with '~' like '~/.prepdir/config.yaml'."""
    patterns = ["~/.prepdir/config.yaml"]
    home_dir = os.path.expanduser("~")
    config_path = os.path.join(home_dir, ".prepdir", "config.yaml")
    full_path = os.path.abspath(os.path.join(home_dir, ".prepdir", "config.yaml"))
    relative_path = os.path.relpath(full_path, base_directory)
    print(f"{home_dir=}\n{config_path=}\n{full_path=}\n{relative_path=}")
    assert is_excluded_file("config.yaml", os.path.join(home_dir, ".prepdir"), base_directory, [], patterns), (
        f"File '{config_path}' should be excluded"
    )
    assert not is_excluded_file("other.yaml", os.path.join(home_dir, ".prepdir"), base_directory, [], patterns), (
        f"File '{os.path.join(home_dir, '.prepdir', 'other.yaml')}' should not be excluded"
    )


def test_empty_excluded_file_patterns(base_directory):
    """Test behavior with empty excluded file patterns list."""
    dir_patterns = ["logs"]
    assert not is_excluded_file("test.txt", "/base/path", base_directory, [], []), (
        "No file patterns should not exclude 'test.txt' unless in excluded dir"
    )
    assert is_excluded_file("test.txt", "/base/path/logs", base_directory, dir_patterns, []), (
        "File 'logs/test.txt' should be excluded due to 'logs' directory"
    )


def test_case_sensitivity_file(exact_file_patterns, glob_file_patterns, recursive_glob_patterns, base_directory):
    """Test case sensitivity in file pattern matching."""
    patterns = exact_file_patterns + glob_file_patterns + recursive_glob_patterns
    for filename in [
        "license.txt",
        "License.txt",
        "license",
        "LiCEnSe",
        "MYfile.txt",
        "MyTEST.txt",
        "SRC/a/b/test_abc",
        "src/a/b/Test_abc",
    ]:
        assert not is_excluded_file(filename, "/base/path", base_directory, [], patterns), (
            f"File '{filename}' should not match 'LICENSE', 'my*.txt', or 'src/**/test_*' (case-sensitive)"
        )


def test_embedded_glob_patterns_file(base_directory):
    """Test embedded glob patterns like 'my*.txt' and 'src/**/test_*'."""
    # Test my*.txt
    my_txt_patterns = ["my*.txt"]
    assert is_excluded_file("myfile.txt", "/base/path", base_directory, [], my_txt_patterns), (
        "File 'myfile.txt' should match 'my*.txt'"
    )
    assert is_excluded_file("myabc.txt", "/base/path/my", base_directory, [], my_txt_patterns), (
        "File 'my/myabc.txt' should match 'my*.txt'"
    )
    assert not is_excluded_file("file.txt", "/base/path", base_directory, [], my_txt_patterns), (
        "File 'file.txt' should not match 'my*.txt'"
    )
    # Test src/**/test_*
    src_test_patterns = ["src/**/test_*"]
    assert is_excluded_file("test_abc", "/base/path/src/a/b", base_directory, [], src_test_patterns), (
        "File 'src/a/b/test_abc' should match 'src/**/test_*'"
    )
    assert is_excluded_file("test_123", "/base/path/src", base_directory, [], src_test_patterns), (
        "File 'src/test_123' should match 'src/**/test_*'"
    )
    assert not is_excluded_file("test_abc", "/base/path/other/a/b", base_directory, [], src_test_patterns), (
        "File 'other/a/b/test_abc' should not match 'src/**/test_*'"
    )
    # Test other /**/ patterns
    other_patterns = ["a/**/b.txt"]
    assert is_excluded_file("b.txt", "/base/path/a", base_directory, [], other_patterns), (
        "File 'a/b.txt' should match 'a/**/b.txt'"
    )
    assert is_excluded_file("b.txt", "/base/path/a/x/y", base_directory, [], other_patterns), (
        "File 'a/x/y/b.txt' should match 'a/**/b.txt'"
    )
    assert not is_excluded_file("b.txt", "/base/path/other", base_directory, [], other_patterns), (
        "File 'other/b.txt' should not match 'a/**/b.txt'"
    )


def test_pattern_interactions(excluded_dir_patterns, excluded_file_patterns, base_directory):
    """Test interactions between multiple patterns."""
    # File in excluded directory and matching file pattern
    assert is_excluded_file(
        "test.log", "/base/path/logs", base_directory, excluded_dir_patterns, excluded_file_patterns
    ), "File 'logs/test.log' should be excluded due to 'logs' directory or '*.log'"
    # File matching multiple file patterns
    assert is_excluded_file("test.log", "/base/path/src/a/b", base_directory, [], excluded_file_patterns), (
        "File 'src/a/b/test.log' should match '*.log' or '**/*.log'"
    )
    # File matching exact and glob patterns
    assert is_excluded_file("LICENSE", "/base/path", base_directory, [], excluded_file_patterns), (
        "File 'LICENSE' should match 'LICENSE'"
    )
    # File in non-excluded directory but matching multiple glob patterns
    assert is_excluded_file("myfile.txt", "/base/path/src", base_directory, [], excluded_file_patterns), (
        "File 'src/myfile.txt' should match 'my*.txt'"
    )
    # Non-matching file in excluded directory
    assert is_excluded_file(
        "script.py", "/base/path/my.egg-info", base_directory, excluded_dir_patterns, excluded_file_patterns
    ), "File 'my.egg-info/script.py' should be excluded due to '*.egg-info'"
