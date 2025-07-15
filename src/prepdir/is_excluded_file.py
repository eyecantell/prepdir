import logging
import os
import re
from typing import List

logger = logging.getLogger(__name__)

def glob_to_regex(pattern: str) -> str:
    """Convert a glob pattern to a regex pattern for exact or path-based matching.

    Args:
        pattern: Glob pattern to convert (e.g., '*.pyc', 'my*.txt', 'src/**/test_*', '~/.prepdir/config.yaml').

    Returns:
        str: Equivalent regex pattern.
    """
    # Note, glob.translate() became available in python 3.13 - to simplify support for 3.9+ we do this routine
    # Normalize pattern by removing trailing slashes and normalizing path
    pattern = os.path.normpath(pattern.rstrip(os.sep))

    # If ~ is in the pattern, replace it with the user home dir
    pattern = pattern.replace('~', os.path.expanduser("~"))

    # Handle patterns containing **/ (e.g., src/**/test_* or a/**/b.txt)
    slashes_and_double_star = os.sep + '**' + os.sep # e.g. /**/
    if slashes_and_double_star in pattern:
        # Split pattern and handle each part
        parts = pattern.split(slashes_and_double_star)
        # Escape and convert glob characters for each part
        regex_parts = []
        for part in parts:
            part = re.escape(part).replace(r"\*", r".*").replace(r"\?", r".")
            regex_parts.append(part)
        # Join with optional directories (.*)? for **/
        regex = r"(/.*)?".join(regex_parts)
        # Anchor to match full path component or anywhere in path
        return f"^{regex}$"
    # If pattern contains glob characters, convert to regex
    if any(c in pattern for c in "*?[]"):
        # Escape special regex characters, replace glob * and ? with regex equivalents
        pattern = re.escape(pattern).replace(r"\*", r".*").replace(r"\?", r".")
        return f"^{pattern}$"
    # For non-glob patterns, require exact match
    return f"^{re.escape(pattern)}$"


def is_excluded_dir(dirname: str, root: str, base_directory: str, excluded_dir_patterns: List[str] = None, excluded_dir_regexes: List[re.Pattern] = None) -> bool:
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
        regexes = regexes + [re.compile(glob_to_regex(pattern.rstrip(os.sep))) for pattern in excluded_dir_patterns]

    if not regexes:
        return False
    
    # Get the relative path of the directory
    relative_path = os.path.relpath(os.path.join(root, dirname), base_directory)

    # Check the each directory of the path, and each parent dir of the path
    path_components = relative_path.split(os.sep) if relative_path != "." else []
    
    for i in range(len(path_components)):
        # Check each individual directory of the path for a match
        if any(regex.search(path_components[i]) for regex in regexes):
            return True
        
        # Check each parent directory in the path for a match
        current_path = os.sep.join(path_components[:i]) or "."
        if any(regex.search(current_path) for regex in regexes):
            return True

    return False


def is_excluded_file(filename: str, root: str, base_directory: str, excluded_dir_patterns: List[str], excluded_file_patterns: List[str], excluded_dir_regexes: List[re.Pattern] = None, excluded_file_regexes: List[re.Pattern] = None, excluded_file_glob_regexes: List[re.Pattern] = None) -> bool:
    """
    Check if a file is excluded based on config patterns or precompiled directory regexes.

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
        dir_regexes = dir_regexes + [re.compile(glob_to_regex(pattern)) for pattern in excluded_dir_patterns]
    logger.debug(f"dir_regexes are {dir_regexes}")

    if is_excluded_dir(os.path.basename(root), root, base_directory, excluded_dir_regexes=dir_regexes):
        return True

    # Compile excluded_file_patterns into regexes and combine with excluded_file_regexes
    regexes = excluded_file_regexes if excluded_file_regexes is not None else []
    glob_regexes = excluded_file_glob_regexes if excluded_file_glob_regexes is not None else []

    if excluded_file_patterns:
        for pattern in excluded_file_patterns:
            compiled_pattern = re.compile(glob_to_regex(pattern))
            regexes.append(compiled_pattern)
            if '**' in pattern:
                glob_regexes.append(compiled_pattern)

    logger.debug(f"(file) regexes are {regexes}")
    logger.debug(f"glob_regexes are {glob_regexes}")

    for regex in regexes:
        logger.info(f"{regex.pattern}")

    # Get the full and relative paths of the file
    full_path = os.path.abspath(os.path.join(root, filename))
    relative_path = os.path.relpath(full_path, base_directory)

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
