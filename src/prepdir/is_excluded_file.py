import logging
import os
import re
from typing import List, Optional
from prepdir.glob_translate import glob_translate

logger = logging.getLogger(__name__)


def is_excluded_dir(
    dirname: str,
    root: str,
    base_directory: str,
    excluded_dir_patterns: List[str] = None,
    excluded_dir_regexes: List[re.Pattern] = None,
) -> bool:
    """
    Check if a directory or any of its parent directories is excluded based on config patterns or precompiled regexes.

    Args:
        dirname: Name of the directory to check (not used directly, kept for compatibility).
        root: Path to the directory containing the file or subdirectory.
        base_directory: Base directory for relative path calculations.
        excluded_dir_patterns: List of glob patterns for excluded directories.
        excluded_dir_regexes: List of precompiled regex objects for excluded directories.

    Returns:
        bool: True if the directory or any parent is excluded, False otherwise.
    """
    # Compile excluded_dir_patterns into regexes
    regexes = excluded_dir_regexes if excluded_dir_regexes is not None else []
    if excluded_dir_patterns:
        regexes = regexes + [
            re.compile(glob_translate(pattern.rstrip(os.sep), seps=(os.sep, os.altsep)))
            for pattern in excluded_dir_patterns
        ]

    if not regexes:
        return False

    # Get the relative path of the directory
    relative_path = os.path.relpath(root, base_directory)
    # Split the relative path into components
    path_components = relative_path.split(os.sep) if relative_path != "." else []

    # Check each individual directory component and parent path
    for i in range(len(path_components) + 1):
        # Check individual component (if i > 0)
        if i > 0 and any(regex.search(path_components[i - 1]) for regex in regexes):
            logger.debug(f"Directory component '{path_components[i - 1]}' matched exclusion pattern")
            return True
        # Check parent path
        current_path = os.sep.join(path_components[:i]) or "."
        if any(regex.search(current_path.replace(os.sep, "/")) for regex in regexes):
            logger.debug(f"Parent path '{current_path}' matched exclusion pattern")
            return True

    return False


def is_excluded_file(
    filename: str,
    root: str,
    base_directory: str,
    excluded_dir_patterns: List[str],
    excluded_file_patterns: List[str],
    excluded_dir_regexes: List[re.Pattern] = None,
    excluded_file_regexes: List[re.Pattern] = None,
    excluded_file_glob_regexes: List[re.Pattern] = None,
) -> bool:
    """
    Check if a file is excluded based on config patterns or precompiled regexes.

    Args:
        filename: Name of the file to check.
        root: Directory containing the file.
        base_directory: Base directory for relative path calculations.
        excluded_dir_patterns: List of glob patterns for excluded directories.
        excluded_file_patterns: List of glob patterns for excluded files.
        excluded_dir_regexes: List of precompiled regex objects for excluded directories.
        excluded_file_regexes: List of precompiled regex objects for excluded files.
        excluded_file_glob_regexes: List of precompiled regex objects for excluded files that include a recursive glob (**).

    Returns:
        bool: True if the file is excluded, False otherwise.
    """
    # Compile excluded_dir_patterns into regexes and combine with excluded_dir_regexes
    dir_regexes = excluded_dir_regexes if excluded_dir_regexes is not None else []
    if excluded_dir_patterns:
        dir_regexes = dir_regexes + [
            re.compile(glob_translate(pattern.rstrip(os.sep), seps=(os.sep, os.altsep)))
            for pattern in excluded_dir_patterns
        ]

    if is_excluded_dir(os.path.basename(root), root, base_directory, excluded_dir_regexes=dir_regexes):
        logger.debug(f"File '{filename}' excluded due to parent directory")
        return True

    # Compile excluded_file_patterns into regexes and combine with excluded_file_regexes
    regexes = excluded_file_regexes if excluded_file_regexes is not None else []
    glob_regexes = excluded_file_glob_regexes if excluded_file_glob_regexes is not None else []

    if excluded_file_patterns:
        for pattern in excluded_file_patterns:
            compiled_pattern = re.compile(glob_translate(pattern, seps=(os.sep, os.altsep)))
            regexes.append(compiled_pattern)
            if "**" in pattern:
                glob_regexes.append(compiled_pattern)

    logger.debug(f"(file) regexes are {regexes}")
    logger.debug(f"glob_regexes are {glob_regexes}")

    for regex in regexes:
        logger.info(f"{regex.pattern}")

    # Get the full and relative paths of the file
    full_path = os.path.abspath(os.path.join(root, filename))
    relative_path = os.path.relpath(full_path, base_directory)

    # Log patterns for debugging
    logger.debug(f"Checking file: filename='{filename}', relative_path='{relative_path}', full_path='{full_path}'")
    logger.debug(f"File regexes: {[r.pattern for r in regexes]}")
    logger.debug(f"Glob regexes: {[r.pattern for r in glob_regexes]}")

    # Check file patterns
    for regex in regexes:
        if re.match(regex, filename):
            logger.debug(f"filename {filename} matched regex {regex}")
            return True

    for regex in glob_regexes:
        if re.match(regex, relative_path):
            logger.debug(f"relative_path {relative_path} matched regex {regex}")
            return True

        if re.match(regex, full_path):
            logger.debug(f"relative_path {full_path} matched regex {regex}")
            return True

    logger.debug(f"no regex matched filename:{filename}, relative_path:{relative_path}, or full_path:{full_path}")
    return False
