import os
import pytest
import logging
from prepdir.is_excluded_file import is_excluded_dir, is_excluded_file
from prepdir.prepdir_logging import configure_logging

logger = logging.getLogger(__name__)
configure_logging(logger, logging.DEBUG)
logging.getLogger("prepdir").setLevel(logging.DEBUG)


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


def test_exact_match_directory():
    """Test exact match for directory name."""
    patterns = ["logs", ".git"]
    assert is_excluded_dir("/base/path/logs", excluded_dir_patterns=patterns), (
        "Directory '/base/path/logs' should be excluded"
    )
    assert is_excluded_dir("/base/path/.git", excluded_dir_patterns=patterns), (
        "Directory '/base/path/.git' should be excluded"
    )


def test_glob_pattern_match():
    """Test glob pattern matching for directories like '*.egg-info'."""
    patterns = ["*.egg-info"]
    assert is_excluded_dir("/base/path/my.egg-info", excluded_dir_patterns=patterns), (
        "Directory '/base/path/my.egg-info' should match '*.egg-info'"
    )
    assert is_excluded_dir("/base/path/project.egg-info", excluded_dir_patterns=patterns), (
        "Directory '/base/path/project.egg-info' should match '*.egg-info'"
    )


def test_parent_directory_exclusion():
    """Test exclusion when a parent directory matches a pattern."""
    patterns = ["logs", ".git"]
    assert is_excluded_dir("/base/path/my/logs/a/b/c", excluded_dir_patterns=patterns), (
        "Directory '/base/path/my/logs/a/b/c' should be excluded due to 'logs'"
    )
    assert is_excluded_dir("/base/path/.git/hooks", excluded_dir_patterns=patterns), (
        "Directory '/base/path/.git/hooks' should be excluded due to '.git'"
    )


def test_no_substring_match():
    """Test that patterns like 'logs' don't match substrings like 'mylogsarefun'."""
    patterns = ["logs"]
    assert not is_excluded_dir("/base/path/my/mylogsarefun", excluded_dir_patterns=patterns), (
        "Directory '/base/path/my/mylogsarefun' should not match 'logs'"
    )
    assert not is_excluded_dir("/base/path/my/mylogsarefun/a", excluded_dir_patterns=patterns), (
        "Directory '/base/path/my/mylogsarefun/a' should not be excluded"
    )


def test_empty_relative_path():
    """Test handling of empty or current directory paths."""
    assert not is_excluded_dir(".", excluded_dir_patterns=[]), "Current directory '.' should not be excluded"


def test_single_component_path():
    """Test single-component paths."""
    patterns = ["build"]
    assert is_excluded_dir("/base/path/build", excluded_dir_patterns=patterns), (
        "Directory '/base/path/build' should be excluded"
    )
    assert not is_excluded_dir("/base/path/src", excluded_dir_patterns=patterns), (
        "Directory '/base/path/src' should not be excluded"
    )


def test_special_characters_in_pattern():
    """Test patterns with special characters like '.' in '.git'."""
    patterns = [".git"]
    assert is_excluded_dir("/base/path/.git", excluded_dir_patterns=patterns), (
        "Directory '/base/path/.git' should be excluded"
    )
    assert not is_excluded_dir("/base/path/dotgitlike", excluded_dir_patterns=patterns), (
        "Directory '/base/path/dotgitlike' should not match '.git'"
    )


def test_nested_glob_pattern():
    """Test nested directories with glob patterns."""
    patterns = ["*.egg-info"]
    assert is_excluded_dir("/base/path/my.egg-info/subdir", excluded_dir_patterns=patterns), (
        "Directory '/base/path/my.egg-info/subdir' should be excluded due to '*.egg-info'"
    )


def test_empty_excluded_patterns():
    """Test behavior with empty excluded patterns list."""
    assert not is_excluded_dir("/base/path/logs", excluded_dir_patterns=[]), (
        "No patterns should result in no exclusions"
    )


def test_trailing_slash_handling():
    """Test patterns with trailing slashes are handled correctly."""
    patterns = ["logs/", ".git/"]
    assert is_excluded_dir("/base/path/logs", excluded_dir_patterns=patterns), (
        "Directory '/base/path/logs' should be excluded despite trailing slash in pattern"
    )
    assert is_excluded_dir("/base/path/.git/a", excluded_dir_patterns=patterns), (
        "Directory '/base/path/.git/a' should be excluded due to '.git/'"
    )


def test_case_sensitivity():
    """Test case sensitivity in directory pattern matching."""
    patterns = ["logs"]
    assert not is_excluded_dir("/base/path/LOGS", excluded_dir_patterns=patterns), (
        "Directory '/base/path/LOGS' should not match 'logs' (case-sensitive)"
    )


def test_path_component_match():
    """Test that non-glob patterns match as path components."""
    patterns = ["logs", ".git"]
    assert is_excluded_dir("/base/path/my/logs/a", excluded_dir_patterns=patterns), (
        "Directory '/base/path/my/logs/a' should be excluded due to 'logs' in path"
    )


#
# Begin is_excluded_file testing
#


def test_exact_match_file(exact_file_patterns):
    """Test exact match for file name."""
    assert is_excluded_file("/base/path/.gitignore", excluded_file_patterns=exact_file_patterns), (
        "File '/base/path/.gitignore' should be excluded"
    )
    assert is_excluded_file("/base/path/pdm.lock", excluded_file_patterns=exact_file_patterns), (
        "File '/base/path/pdm.lock' should be excluded"
    )


def test_glob_pattern_match_file(glob_file_patterns):
    """Test glob pattern matching for files like '*.pyc'."""
    assert is_excluded_file("/base/path/module.pyc", excluded_file_patterns=glob_file_patterns), (
        "File '/base/path/module.pyc' should match '*.pyc'"
    )
    assert is_excluded_file("/base/path/my/test.log", excluded_file_patterns=glob_file_patterns), (
        "File '/base/path/my/test.log' should match '*.log'"
    )
    assert is_excluded_file("/base/path/myfile.txt", excluded_file_patterns=glob_file_patterns), (
        "File '/base/path/myfile.txt' should match 'my*.txt'"
    )


def test_file_in_excluded_directory():
    """Test file exclusion when in an excluded directory."""
    dir_patterns = ["logs", "*.egg-info"]
    assert is_excluded_file("/base/path/logs/test.txt", excluded_dir_patterns=dir_patterns), (
        "File '/base/path/logs/test.txt' should be excluded due to 'logs' directory"
    )
    assert is_excluded_file("/base/path/my.egg-info/script.py", excluded_dir_patterns=dir_patterns), (
        "File '/base/path/my.egg-info/script.py' should be excluded due to '*.egg-info'"
    )


def test_no_substring_match_file(exact_file_patterns, glob_file_patterns):
    """Test that file patterns like '*.log' or 'LICENSE' don't match substrings like 'mylogsarefun.txt' or 'LICENSE.txt'."""
    patterns = exact_file_patterns + glob_file_patterns
    assert is_excluded_file("/base/path/my/mylogsarefun.txt", excluded_file_patterns=patterns), (
        "File '/base/path/my/mylogsarefun.txt' should match 'my*.txt' pattern"
    )
    assert not is_excluded_file("/base/path/my/yourlogsarefun.txt", excluded_file_patterns=patterns), (
        "File '/base/path/my/yourlogsarefun.txt' should not match any pattern"
    )
    assert is_excluded_file("/base/path/my/mylogsarefun.log", excluded_file_patterns=patterns), (
        "File '/base/path/my/mylogsarefun.log' should match '*.log'"
    )
    assert not is_excluded_file("/base/path/notgitignore.txt", excluded_file_patterns=patterns), (
        "File '/base/path/notgitignore.txt' should not match '.gitignore'"
    )
    for filename in ["/base/path/LICENSE.txt", "/base/path/MYLICENSE", "/base/path/LICENSE1"]:
        assert not is_excluded_file(filename, excluded_file_patterns=patterns), (
            f"File '{filename}' should not match 'LICENSE'"
        )


def test_home_directory_pattern():
    """Test patterns with '~' like '~/.prepdir/config.yaml'."""
    patterns = ["~/.prepdir/config.yaml"]
    home_dir = os.path.expanduser("~")
    config_path = os.path.join(home_dir, ".prepdir", "config.yaml")
    assert is_excluded_file(config_path, excluded_file_patterns=patterns), f"File '{config_path}' should be excluded"
    assert not is_excluded_file(os.path.join(home_dir, ".prepdir", "other.yaml"), excluded_file_patterns=patterns), (
        f"File '{os.path.join(home_dir, '.prepdir', 'other.yaml')}' should not be excluded"
    )


def test_empty_excluded_file_patterns():
    """Test behavior with empty excluded file patterns list."""
    dir_patterns = ["logs"]
    assert not is_excluded_file("/base/path/test.txt", excluded_dir_patterns=[], excluded_file_patterns=[]), (
        "No file patterns should not exclude '/base/path/test.txt' unless in excluded dir"
    )
    assert is_excluded_file(
        "/base/path/logs/test.txt", excluded_dir_patterns=dir_patterns, excluded_file_patterns=[]
    ), "File '/base/path/logs/test.txt' should be excluded due to 'logs' directory"


def test_case_sensitivity_file(exact_file_patterns, glob_file_patterns, recursive_glob_patterns):
    """Test case sensitivity in file pattern matching."""
    patterns = exact_file_patterns + glob_file_patterns + recursive_glob_patterns
    for filename in [
        "/base/path/license.txt",
        "/base/path/License.txt",
        "/base/path/license",
        "/base/path/LiCEnSe",
        "/base/path/MYfile.txt",
        "/base/path/MyTEST.txt",
        "/base/path/src/a/b/Test_abc",
    ]:
        assert not is_excluded_file(filename, excluded_file_patterns=patterns), (
            f"File '{filename}' should not match 'LICENSE', 'my*.txt', or 'src/**/test_*' (case-sensitive)"
        )


def test_embedded_glob_patterns_file():
    """Test embedded glob patterns like 'my*.txt' and 'src/**/test_*'."""
    # Test my*.txt
    my_txt_patterns = ["my*.txt"]
    assert is_excluded_file("/base/path/myfile.txt", excluded_file_patterns=my_txt_patterns), (
        "File '/base/path/myfile.txt' should match 'my*.txt'"
    )
    assert is_excluded_file("/base/path/my/myabc.txt", excluded_file_patterns=my_txt_patterns), (
        "File '/base/path/my/myabc.txt' should match 'my*.txt'"
    )
    assert not is_excluded_file("/base/path/file.txt", excluded_file_patterns=my_txt_patterns), (
        "File '/base/path/file.txt' should not match 'my*.txt'"
    )
    # Test src/**/test_*
    src_test_patterns = ["src/**/test_*"]
    assert is_excluded_file("/base/path/src/a/b/test_abc", excluded_file_patterns=src_test_patterns), (
        "File '/base/path/src/a/b/test_abc' should match 'src/**/test_*'"
    )
    assert is_excluded_file("/base/path/src/test_123", excluded_file_patterns=src_test_patterns), (
        "File '/base/path/src/test_123' should match 'src/**/test_*'"
    )
    assert not is_excluded_file("/base/path/other/a/b/test_abc", excluded_file_patterns=src_test_patterns), (
        "File '/base/path/other/a/b/test_abc' should not match 'src/**/test_*'"
    )
    # Test other /**/ patterns
    other_patterns = ["a/**/b.txt"]
    assert is_excluded_file("/base/path/a/b.txt", excluded_file_patterns=other_patterns), (
        "File '/base/path/a/b.txt' should match 'a/**/b.txt'"
    )
    assert is_excluded_file("/base/path/a/x/y/b.txt", excluded_file_patterns=other_patterns), (
        "File '/base/path/a/x/y/b.txt' should match 'a/**/b.txt'"
    )
    assert not is_excluded_file("/base/path/other/b.txt", excluded_file_patterns=other_patterns), (
        "File '/base/path/other/b.txt' should not match 'a/**/b.txt'"
    )


def test_pattern_interactions(excluded_dir_patterns, excluded_file_patterns):
    """Test interactions between multiple patterns."""
    # File in excluded directory and matching file pattern
    assert is_excluded_file(
        "/base/path/logs/test.log",
        excluded_dir_patterns=excluded_dir_patterns,
        excluded_file_patterns=excluded_file_patterns,
    ), "File '/base/path/logs/test.log' should be excluded due to 'logs' directory or '*.log'"
    # File matching multiple file patterns
    assert is_excluded_file(
        "/base/path/src/a/b/test.log",
        excluded_file_patterns=excluded_file_patterns,
    ), "File '/base/path/src/a/b/test.log' should match '*.log' or '**/*.log'"
    # File matching exact and glob patterns
    assert is_excluded_file(
        "/base/path/LICENSE",
        excluded_file_patterns=excluded_file_patterns,
    ), "File '/base/path/LICENSE' should match 'LICENSE'"
    # File in non-excluded directory but matching multiple glob patterns
    assert is_excluded_file(
        "/base/path/src/myfile.txt",
        excluded_file_patterns=excluded_file_patterns,
    ), "File '/base/path/src/myfile.txt' should match 'my*.txt'"
    # Non-matching file in excluded directory
    assert is_excluded_file(
        "/base/path/my.egg-info/script.py",
        excluded_dir_patterns=excluded_dir_patterns,
        excluded_file_patterns=excluded_file_patterns,
    ), "File '/base/path/my.egg-info/script.py' should be excluded due to '*.egg-info'"
