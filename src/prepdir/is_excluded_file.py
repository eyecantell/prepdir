import os
import re
from typing import List


def glob_to_regex(pattern: str) -> str:
    """Convert a glob pattern to a regex pattern for exact or path-based matching.

    Args:
        pattern: Glob pattern to convert (e.g., '*.pyc', 'my*.txt', 'src/**/test_*', '~/.prepdir/config.yaml').

    Returns:
        str: Equivalent regex pattern.
    """
    # Normalize pattern by removing trailing slashes and normalizing path
    pattern = os.path.normpath(pattern.rstrip("/"))
    # Handle patterns containing **/ (e.g., src/**/test_* or a/**/b.txt)
    if "/**/" in pattern:
        # Split pattern at **/ and handle each part
        parts = pattern.split("/**/")
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


def is_excluded_dir(dirname: str, root: str, base_directory: str, excluded_dir_patterns: List[str]) -> bool:
    """Check if directory or any of its parent directories should be excluded from traversal using glob patterns.

    Args:
        dirname: Directory name to check.
        root: Root path of the directory.
        base_directory: Base directory for relative path calculation.
        excluded_dir_patterns: List of directory patterns to exclude (supports glob patterns).

    Returns:
        bool: True if the directory or any parent directory should be excluded.
    """
    # Get the relative path of the directory
    relative_path = os.path.relpath(os.path.join(root, dirname), base_directory)

    # Check the directory itself
    for pattern in excluded_dir_patterns:
        pattern = pattern.rstrip("/")
        regex = glob_to_regex(pattern)
        # Match dirname exactly or as a path component in relative_path
        if dirname == pattern or re.search(regex, relative_path):
            return True

    # Check each parent directory
    path_parts = relative_path.split(os.sep)
    for i in range(1, len(path_parts) + 1):
        parent_path = os.sep.join(path_parts[:i])
        parent_dir = path_parts[i - 1] if i > 0 else ""
        for pattern in excluded_dir_patterns:
            pattern = pattern.rstrip("/")
            regex = glob_to_regex(pattern)
            # Match parent_dir exactly or as a path component in parent_path
            if parent_dir == pattern or re.search(regex, parent_path):
                return True

    return False


def is_excluded_file(
    filename: str, root: str, base_directory: str, excluded_dir_patterns: List[str], excluded_file_patterns: List[str]
) -> bool:
    """Check if a file or its parent directories should be excluded from traversal using glob patterns.

    Args:
        filename: File name to check.
        root: Root path of the file.
        base_directory: Base directory for relative path calculation.
        excluded_dir_patterns: List of directory patterns to exclude (supports glob patterns).
        excluded_file_patterns: List of file patterns to exclude (supports glob patterns).

    Returns:
        bool: True if the file or any of its parent directories should be excluded.
    """
    # Check if the file is in an excluded directory
    dir_name = os.path.basename(root)
    if is_excluded_dir(dir_name, os.path.dirname(root), base_directory, excluded_dir_patterns):
        return True

    # Get the full and relative paths of the file
    full_path = os.path.abspath(os.path.join(root, filename))
    relative_path = os.path.relpath(full_path, base_directory)
    home_dir = os.path.expanduser("~")

    # Check file patterns
    for pattern in excluded_file_patterns:
        # Normalize patterns containing ~
        pattern = os.path.normpath(pattern.rstrip("/").replace("~", home_dir))
        regex = glob_to_regex(pattern)
        # For exact patterns, check filename or full_path equality
        if not any(c in pattern for c in "*?[]") and not "/**/" in pattern:
            if filename == pattern or full_path == pattern:
                return True
        # For glob patterns, check filename with regex
        elif "/**/" not in pattern:
            if re.match(regex, filename):
                return True
        # For recursive patterns or home directory patterns, check relative_path and full_path
        else:
            if re.match(regex, relative_path) or re.match(regex, full_path):
                return True

    return False
