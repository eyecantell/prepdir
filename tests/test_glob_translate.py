import os
import re
import logging
from prepdir.prepdir_logging import configure_logging
from prepdir.glob_translate import glob_translate

logger = logging.getLogger(__name__)
configure_logging(logger, logging.DEBUG)
logging.getLogger("prepdir").setLevel(logging.DEBUG)

not_sep = f"[^{re.escape(os.sep)}{re.escape(os.path.altsep) if os.path.altsep else ''}]"
any_sep = f"[{re.escape(os.sep)}{re.escape(os.path.altsep)}]" if os.path.altsep else re.escape(os.sep)
logger.debug(f"{not_sep=}\n{any_sep=}")


def test_glob_translate_basic_patterns():
    """Test basic glob patterns without **."""
    assert glob_translate("*.txt") == rf"^{not_sep}*\.txt\Z"
    assert glob_translate("test_*.py") == rf"^test_{not_sep}*\.py\Z"
    assert glob_translate("file?.log") == rf"^file{not_sep}\.log\Z"


def test_glob_translate_character_classes():
    """Test glob patterns with character classes."""
    assert glob_translate("test_[a-z].txt") == rf"^test_[a-z]\.txt\Z"
    assert glob_translate("test_[!a-z].txt") == rf"^test_[^a-z]\.txt\Z"
    assert glob_translate("file[1].txt") == rf"^file[1]\.txt\Z"
    assert glob_translate(r"file\[1\].txt") == rf"^file\\[1\\]\.txt\Z"


def test_glob_translate_double_star():
    """Test patterns with **, including leading and trailing cases."""
    assert glob_translate("src/**/test_*") == rf"^src{any_sep}(?:.+{any_sep})?test_{not_sep}*\Z"
    assert glob_translate("**/file.txt") == rf"^(?:.+{any_sep})?file\.txt\Z"
    assert glob_translate("src/**") == rf"^src{any_sep}.*\Z"


def test_glob_translate_cross_platform():
    """Test patterns with mixed separators."""
    assert glob_translate("src/test/*.py", seps=("/", "\\")) == r"^src[/\\]test[/\\][^/\\]*\.py\Z"
    assert glob_translate("src\\test\\*.py", seps=("/", "\\")) == r"^src[/\\]test[/\\][^/\\]*\.py\Z"


def test_glob_translate_seps():
    """Test custom separators."""
    not_sep_slash = r"[^/]"
    not_sep_backslash = r"[^\\]"
    assert glob_translate("src/test/*.py", seps=("/")) == rf"^src/test/{not_sep_slash}*\.py\Z"
    assert glob_translate("src\\test\\*.py", seps=("\\")) == rf"^src\\test\\{not_sep_backslash}*\.py\Z"


def test_glob_translate_edge_cases():
    """Test edge cases like empty patterns and invalid classes."""
    assert glob_translate("") == r"^\Z"
    assert glob_translate("**") == r"^.*\Z"
    assert glob_translate("[z-a]") == r"^(?!)\Z"  # Invalid range, escaped
    assert glob_translate("[abc") == r"^\[abc\Z"  # Unclosed bracket, escaped


def test_glob_translate_non_recursive():
    """Test with recursive=False."""
    assert glob_translate("src/**/test_*", recursive=False) == rf"^src{any_sep}{not_sep}*{any_sep}test_{not_sep}*\Z"


def test_glob_translate_matches():
    """Test that translated regexes match expected paths."""
    glob_pattern = "src/**/test_*.py"
    regex = re.compile(glob_translate(glob_pattern, recursive=True))

    for file_pattern in [
        f"src{os.sep}abc{os.sep}test_foo.py",
        f"src{os.sep}test_foo.py",
        f"src{os.sep}sub{os.sep}test_bar.py",
        f"src{os.sep}sub{os.sep}dir{os.sep}test_baz.py",
    ]:
        assert regex.match(file_pattern), f"Expected {file_pattern} to match {glob_pattern}"

    for file_pattern in [
        "test_foo.py",
        f"src{os.sep}abc{os.sep}test.py",
    ]:
        assert not regex.match(file_pattern), f"Did not expect {file_pattern} to match {glob_pattern}"

    regex = re.compile(glob_translate("**/file.txt", recursive=True))
    for file_pattern in [
        "file.txt",
        f"sub{os.sep}file.txt",
        f"src{os.sep}sub{os.sep}dir{os.sep}file.txt",
    ]:
        assert regex.match(file_pattern), f"Expected {file_pattern} to match {glob_pattern}"

    regex = re.compile(glob_translate("test_[a-z].txt"))
    assert regex.match("test_a.txt")
    assert not regex.match("test_1.txt")


def test_glob_translate_not_hidden_files():
    """Test handling of hidden files with include_hidden=False."""

    logger.debug(f"{not_sep=}\n{any_sep=}")
    # Expected regex on linux for "*.txt" when include_hidden is False: ^(?!\.)[^/]*\.txt\Z
    assert glob_translate("*.txt", include_hidden=False) == rf"^(?!\.)[^{any_sep}]*\.txt\Z"
    regex = re.compile(glob_translate("*.txt", include_hidden=False))
    assert regex.match("file.txt")
    assert not regex.match(".file.txt")


def test_glob_translate_consecutive_double_star():
    """Test handling of consecutive ** patterns."""

    logger.debug(f"{not_sep=}\n{any_sep=}")
    glob_pattern = "src/**/**/test_*.py"
    regex = glob_translate(glob_pattern)
    expected_regex = rf"^src{any_sep}(?:.+{any_sep})?test_{not_sep}*\.py\Z"
    # Expected on linux is ^src/(?:.+/)?test_[^/]*\.py\Z
    logger.debug(f"---------regex: {regex}")
    logger.debug(f"expected_regex: {expected_regex}")
    assert regex == expected_regex


def test_tilde_for_home_dir():
    home_dir = os.path.expanduser("~")
    assert glob_translate(f"~{os.sep}test.py") == rf"^{home_dir}{os.sep}test\.py\Z"  # starting tilde is replaced
    assert (
        glob_translate(f"{os.sep}~{os.sep}test.py") == rf"^{re.escape(os.sep)}\~/test\.py\Z"
    )  # other tilde is not replaced
