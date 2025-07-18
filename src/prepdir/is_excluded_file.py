import logging
import os
import re
from typing import List
from pathlib import Path
from prepdir.glob_translate import glob_translate

logger = logging.getLogger(__name__)


def _path_as_str(path) -> str:
    """Make sure the given path is a string. If a Posix Path is given, convert it. If not str or Path type raise ValueError"""
    if isinstance(path, str):
        return path

    if isinstance(path, Path):
        logger.warning(f"Got Path object - converted to string {path}")
        return str(path)

    if not isinstance(path, str):
        raise ValueError(f"path should be str but got {type(path)}")


def is_excluded_dir(
    path: str,
    excluded_dir_patterns: List[str] = None,
    excluded_dir_regexes: List[re.Pattern] = None,
) -> bool:
    """
    Check if a directory or any of its parent directories is excluded based on config patterns or precompiled regexes.

    Args:
        path: Path for the directory to check
        excluded_dir_patterns: List of glob patterns for excluded directories.
        excluded_dir_regexes: List of precompiled regex objects for excluded directories.

    Returns:
        bool: True if the directory or any parent is excluded, False otherwise.
    """

    path = _path_as_str(path)

    if not path or path == ".":
        logger.debug(f"No path or '.' given ({path}) - returning False")
        return False

    # Compile excluded_dir_patterns
    regexes = excluded_dir_regexes if excluded_dir_regexes is not None else []
    if excluded_dir_patterns:
        regexes = regexes + [
            re.compile(glob_translate(pattern, recursive=True, include_hidden=True))
            for pattern in excluded_dir_patterns
        ]

    if not regexes:
        logger.debug(f"No regexes - returning False")
        return False

    # Split the relative path into components
    path_components = path.split(os.sep)
    logger.debug(f"{path_components=}")

    # Check each individual directory component
    for dirname in path_components:
        for regex in regexes:
            if regex.search(dirname):
                logger.info(f"Directory component '{dirname}' in {path} matched exclusion pattern '{regex.pattern}'")
                return True

    # Check each parent path and the path itself
    for i in range(len(path_components)):
        path_to_check = os.sep.join(path_components[: i + 1])
        logger.debug(f"checking {path_to_check}")
        for regex in regexes:
            if regex.search(path_to_check):
                logger.info(f"Path '{path_to_check}' in {path} matched exclusion pattern '{regex.pattern}'")
                return True

    return False


def is_excluded_file(
    path: str,
    excluded_dir_patterns: List[str] = None,
    excluded_file_patterns: List[str] = None,
    excluded_dir_regexes: List[re.Pattern] = None,
    excluded_file_regexes: List[re.Pattern] = None,
    excluded_file_recursive_glob_regexes: List[re.Pattern] = None,
) -> bool:
    """
    Check if a file is excluded based on config patterns or precompiled regexes.

    Args:
        path: Path of the file to check.
        excluded_dir_patterns: List of glob patterns for excluded directories.
        excluded_file_patterns: List of glob patterns for excluded files.
        excluded_dir_regexes: List of precompiled regex objects for excluded directories.
        excluded_file_regexes: List of precompiled regex objects for excluded files.
        excluded_file_recursive_glob_regexes: List of precompiled regex objects for excluded files that include a recursive glob (**).

    Returns:
        bool: True if the file is excluded, False otherwise.
    """

    path = _path_as_str(path)

    # Compile excluded_dir_patterns into regexes and combine with excluded_dir_regexes
    dir_regexes = excluded_dir_regexes if excluded_dir_regexes is not None else []
    if excluded_dir_patterns:
        dir_regexes = dir_regexes + [
            re.compile(glob_translate(pattern, recursive=True, include_hidden=True))
            for pattern in excluded_dir_patterns
        ]

    if dir_regexes and is_excluded_dir(str(Path(path).parent), excluded_dir_regexes=dir_regexes):
        logger.info(f"File '{path}' excluded due to parent directory {Path(path).parent}")
        return True

    # Compile excluded_file_patterns into regexes and combine with excluded_file_regexes or excluded_file_recursive_glob_regexes
    regexes = excluded_file_regexes if excluded_file_regexes is not None else []
    recursive_glob_regexes = (
        excluded_file_recursive_glob_regexes if excluded_file_recursive_glob_regexes is not None else []
    )

    if excluded_file_patterns:
        for pattern in excluded_file_patterns:
            compiled_pattern = re.compile(glob_translate(pattern, recursive=True, include_hidden=True))
            if "**" in pattern:
                recursive_glob_regexes.append(compiled_pattern)
            else:
                regexes.append(compiled_pattern)

    logger.debug(f"(file) regexes are {regexes}")
    logger.debug(f"recursive_glob_regexes are {recursive_glob_regexes}")

    # Log patterns for debugging
    logger.debug(f"Checking file: path='{path}'")
    logger.debug(f"File regexes: {[r.pattern for r in regexes]}")
    logger.debug(f"Glob regexes: {[r.pattern for r in recursive_glob_regexes]}")

    # Check file patterns
    filename = os.path.basename(path)
    for regex in regexes:
        if regex.search(filename):
            logger.info(f"Filename {filename} matched exclusion regex {regex.pattern}")
            return True

        if regex.search(path):
            logger.info(f"Path {path} matched exclusion regex {regex.pattern}")
            return True

    # Split the relative path into components
    path_components = path.split(os.sep)

    # Check the filename with each parent path
    for i in range(len(path_components)):
        path_to_check = os.sep.join(path_components[i:])
        logger.debug(f"checking {path_to_check}")
        for regex in recursive_glob_regexes:
            if regex.search(path_to_check):
                logger.info(f"Path '{path_to_check}' in {path} matched exclusion pattern '{regex.pattern}'")
                return True

    logger.debug(f"no regex matched path:{path}")
    return False
