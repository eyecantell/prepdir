#!/usr/bin/env python3
"""
Core functionality for prepdir - Utility to traverse directories and prepare file contents for review.
"""

import os
import sys
import re
import uuid
import yaml
from datetime import datetime
from contextlib import redirect_stdout
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
import fnmatch
import logging
from io import StringIO
from prepdir.config import load_config

if sys.version_info < (3, 9):
    from typing_extensions import Tuple
else:
    from typing import Tuple

logger = logging.getLogger(__name__)

try:
    __version__ = version("prepdir")
except PackageNotFoundError:
    __version__ = "0.13.0"  # Fallback to hardcoded version

# UUID regex pattern (8-4-4-4-12 hexadecimal characters, case-insensitive, with word boundaries)
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", re.IGNORECASE
)

UUID_PATTERN_NO_HYPHENS = re.compile(r"\b[0-9a-fA-F]{32}\b", re.IGNORECASE)

# File delimiter and header/footer patterns
DELIMITER = "=-=-=-=-=-=-=-="
LENIENT_DELIM_PATTERN = "[=-]+"
HEADER_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+Begin File: '(.*?)'\s+{LENIENT_DELIM_PATTERN}$")
FOOTER_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+End File: '(.*?)'\s+{LENIENT_DELIM_PATTERN}$")
GENERATED_HEADER_PATTERN = re.compile(
    r"^File listing generated (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)?(?: by (.*)(?: version ([0-9.]+))?(?: \(pip install prepdir\))?)?$"
)
PARTIAL_HEADER_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+Begin File:")
PARTIAL_FOOTER_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+End File:")


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def scrub_uuids(
    content: str,
    replacement_uuid: str,
    scrub_hyphenless: bool = False,
    verbose: bool = False,
    use_unique_placeholders: bool = False,
    placeholder_counter: int = 1,
) -> Tuple[str, bool, dict, int]:
    """
    Scrub UUIDs in content, replacing with either a single UUID or unique placeholders.

    Args:
        content (str): The content to scrub.
        replacement_uuid (str): UUID to use when use_unique_placeholders is False.
        scrub_hyphenless (bool): If True, also scrub hyphen-less UUIDs.
        verbose (bool): If True, log UUIDs being scrubbed.
        use_unique_placeholders (bool): If True, replace UUIDs with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n).
        placeholder_counter (int): Counter for generating unique placeholders.

    Returns:
        Tuple[str, bool, dict, int]: (scrubbed content, whether replacements occurred, mapping of placeholders to original UUIDs, updated placeholder counter).
    """
    original_content = content
    replaced = False
    uuid_mapping = {}
    current_counter = placeholder_counter

    def generate_placeholder():
        nonlocal current_counter
        placeholder = f"PREPDIR_UUID_PLACEHOLDER_{current_counter}"
        current_counter += 1
        return placeholder

    # Scrub hyphenated UUIDs
    if use_unique_placeholders:

        def replace_hyphenated_uuid(match):
            original_uuid = match.group(0)
            placeholder = generate_placeholder()
            uuid_mapping[placeholder] = original_uuid
            if verbose:
                logger.debug(f"Replacing hyphenated UUID '{original_uuid}' with '{placeholder}'")
            return placeholder

        content = UUID_PATTERN.sub(replace_hyphenated_uuid, content)
    else:
        if verbose:
            matches = list(UUID_PATTERN.finditer(content))
            if matches:
                logger.debug(f"Scrubbed {len(matches)} hyphenated UUID(s): {[m.group(0) for m in matches]}")
        content = UUID_PATTERN.sub(replacement_uuid, content)
    if content != original_content:
        replaced = True

    # Scrub hyphen-less UUIDs if enabled
    if scrub_hyphenless:
        if use_unique_placeholders:

            def replace_hyphenless_uuid(match):
                original_uuid = match.group(0)
                placeholder = generate_placeholder()
                uuid_mapping[placeholder] = original_uuid
                if verbose:
                    logger.debug(f"Replacing hyphen-less UUID '{original_uuid}' with '{placeholder}'")
                return placeholder

            content = UUID_PATTERN_NO_HYPHENS.sub(replace_hyphenless_uuid, content)
        else:
            if verbose:
                matches = list(UUID_PATTERN_NO_HYPHENS.finditer(content))
                if matches:
                    logger.debug(f"Scrubbed {len(matches)} hyphen-less UUID(s): {[m.group(0) for m in matches]}")
            content = UUID_PATTERN_NO_HYPHENS.sub(replacement_uuid.replace("-", ""), content)
        if content != original_content:
            replaced = True

    return content, replaced, uuid_mapping, current_counter


def is_prepdir_generated(file_path: str) -> bool:
    """Check if a file was generated by prepdir based on its header."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            return first_line.startswith("File listing generated") and "by prepdir" in first_line
    except (UnicodeDecodeError, IOError):
        return False


def init_config(config_path=".prepdir/config.yaml", force=False, stdout=sys.stdout, stderr=sys.stderr):
    """
    Initialize a local config.yaml with the package's default config.

    Args:
        config_path (str): Path to the configuration file to create.
        force (bool): If True, overwrite existing config file.
        stdout (file-like): Stream for success messages (default: sys.stdout).
        stderr (file-like): Stream for error messages (default: sys.stderr).

    Raises:
        SystemExit: If the config file exists and force=False, or if creation fails.
    """
    config_path = Path(config_path)
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists() and not force:
        print(f"Error: '{config_path}' already exists. Use force=True to overwrite.", file=stderr)
        raise SystemExit(1)

    try:
        config = load_config("prepdir")
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config.as_dict(), f)
        print(f"Created '{config_path}' with default configuration.", file=stdout)
    except Exception as e:
        print(f"Error: Failed to create '{config_path}': {str(e)}", file=stderr)
        raise SystemExit(1)


def is_excluded_dir(dirname, root, directory, excluded_dirs):
    """Check if directory should be excluded from traversal using glob patterns."""
    relative_path = os.path.relpath(os.path.join(root, dirname), directory)
    for pattern in excluded_dirs:
        pattern = pattern.rstrip("/")
        if fnmatch.fnmatch(dirname, pattern) or fnmatch.fnmatch(relative_path, pattern):
            return True
    return False


def is_excluded_file(filename, root, directory, excluded_files, output_file, include_prepdir_files):
    """Check if file should be excluded from traversal using glob patterns, if it's the output file, or if it's prepdir-generated."""
    full_path = os.path.abspath(os.path.join(root, filename))
    if output_file and full_path == os.path.abspath(output_file):
        return True

    if not include_prepdir_files and is_prepdir_generated(full_path):
        return True

    relative_path = os.path.relpath(full_path, directory)
    home_dir = os.path.expanduser("~")
    for pattern in excluded_files:
        # Normalize patterns containing ~
        pattern = pattern.replace("~", home_dir)
        if (
            fnmatch.fnmatch(filename, pattern)
            or fnmatch.fnmatch(relative_path, pattern)
            or fnmatch.fnmatch(full_path, pattern)
        ):
            return True
    return False


def display_file_content(
    file_full_path: str,
    directory: str,
    scrub_uuids_enabled: bool,
    scrub_hyphenless_uuids_enabled: bool,
    replacement_uuid: str,
    use_unique_placeholders: bool = False,
    placeholder_counter: int = 1,
) -> Tuple[bool, dict, int]:
    """
    Display the content of a file with appropriate header, optionally scrubbing UUIDs, return if UUIDs were scrubbed and the UUID mapping.

    Args:
        file_full_path (str): Full path to the file.
        directory (str): Base directory for relative path calculation.
        scrub_uuids_enabled (bool): If True, scrub UUIDs in file contents.
        scrub_hyphenless_uuids_enabled (bool): If True, scrub hyphen-less UUIDs.
        replacement_uuid (str): UUID to replace detected UUIDs with when use_unique_placeholders is False.
        use_unique_placeholders (bool): If True, replace UUIDs with unique placeholders.
        placeholder_counter (int): Counter for generating unique placeholders.

    Returns:
        Tuple[bool, dict, int]: (Whether UUIDs were scrubbed, mapping of placeholders to original UUIDs, updated placeholder counter).
    """
    dashes = "=-" * 7 + "="
    relative_path = os.path.relpath(file_full_path, directory)

    print(f"{dashes} Begin File: '{relative_path}' {dashes}")

    uuids_scrubbed = False
    uuid_mapping = {}
    try:
        with open(file_full_path, "r", encoding="utf-8") as f:
            content = f.read()
            if scrub_uuids_enabled or scrub_hyphenless_uuids_enabled:
                content, uuids_scrubbed, file_uuid_mapping, placeholder_counter = scrub_uuids(
                    content,
                    replacement_uuid,
                    scrub_hyphenless_uuids_enabled,
                    use_unique_placeholders=use_unique_placeholders,
                    placeholder_counter=placeholder_counter,
                )
                uuid_mapping.update(file_uuid_mapping)
            print(content)
    except UnicodeDecodeError:
        print("[Binary file or encoding not supported]")
    except Exception as e:
        print(f"[Error reading file: {str(e)}]")

    print(f"{dashes} End File: '{relative_path}' {dashes}")
    return uuids_scrubbed, uuid_mapping, placeholder_counter


def traverse_directory(
    directory,
    extensions=None,
    excluded_dirs=None,
    excluded_files=None,
    include_all=False,
    verbose=False,
    output_file=None,
    include_prepdir_files=False,
    scrub_uuids_enabled=True,
    scrub_hyphenless_uuids_enabled=True,
    replacement_uuid="00000000-0000-0000-0000-000000000000",
    use_unique_placeholders=False,
):
    """
    Traverse the directory and display file contents.

    Args:
        directory (str): Starting directory path.
        extensions (list): List of file extensions to include (without the dot).
        excluded_dirs (list): Directory glob patterns to exclude.
        excluded_files (list): File glob patterns to exclude.
        include_all (bool): If True, ignore exclusion lists.
        verbose (bool): If True, print additional information about skipped files.
        output_file (str): Path to the output file to exclude from traversal.
        include_prepdir_files (bool): If True, include files previously generated by prepdir.
        scrub_uuids_enabled (bool): If True, scrub UUIDs in file contents.
        scrub_hyphenless_uuids_enabled (bool): If True, scrub hyphen-less UUIDs.
        replacement_uuid (str): UUID to replace detected UUIDs with when use_unique_placeholders is False.
        use_unique_placeholders (bool): If True, replace UUIDs with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n).

    Returns:
        dict: Mapping of placeholders to original UUIDs.
    """
    directory = os.path.abspath(directory)
    files_found = False
    any_uuids_scrubbed = False
    uuid_mapping = {}
    placeholder_counter = 1

    print(f"File listing generated {datetime.now()} by prepdir version {__version__} (pip install prepdir)")
    print(f"Base directory is '{directory}'")
    if scrub_uuids_enabled:
        if use_unique_placeholders:
            print(
                "Note: Valid UUIDs in file contents will be scrubbed and replaced with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n)."
            )
        else:
            print(f"Note: Valid UUIDs in file contents will be scrubbed and replaced with '{replacement_uuid}'.")
    if scrub_hyphenless_uuids_enabled:
        if use_unique_placeholders:
            print(
                "Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n)."
            )
        else:
            print(
                f"Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with '{replacement_uuid.replace('-', '')}'."
            )

    for root, dirs, files in os.walk(directory):
        if not include_all:
            skipped_dirs = [d for d in dirs if is_excluded_dir(d, root, directory, excluded_dirs)]
            if verbose:
                for d in skipped_dirs:
                    print(f"Skipping directory: {os.path.join(root, d)} (excluded in config)", file=sys.stderr)
            dirs[:] = [d for d in dirs if not is_excluded_dir(d, root, directory, excluded_dirs)]

        # Sort files for deterministic processing
        files.sort()

        for file in files:
            full_path = os.path.abspath(os.path.join(root, file))
            if is_excluded_file(file, root, directory, excluded_files, output_file, include_prepdir_files):
                if verbose:
                    reason = (
                        "output file"
                        if output_file and full_path == os.path.abspath(output_file)
                        else "prepdir-generated file"
                        if is_prepdir_generated(full_path) and not include_prepdir_files
                        else "excluded in config"
                    )
                    print(f"Skipping file: {os.path.join(root, file)} ({reason})", file=sys.stderr)
                continue

            if extensions:
                file_ext = os.path.splitext(file)[1].lstrip(".")
                if file_ext not in extensions:
                    if verbose:
                        print(
                            f"Skipping file: {os.path.join(root, file)} (extension not in {extensions})",
                            file=sys.stderr,
                        )
                    continue

            files_found = True
            full_path = os.path.join(root, file)
            uuids_scrubbed, file_uuid_mapping, placeholder_counter = display_file_content(
                full_path,
                directory,
                scrub_uuids_enabled,
                scrub_hyphenless_uuids_enabled,
                replacement_uuid,
                use_unique_placeholders,
                placeholder_counter,
            )
            if uuids_scrubbed:
                any_uuids_scrubbed = True
            uuid_mapping.update(file_uuid_mapping)

    if not files_found:
        if extensions:
            print(f"No files with extension(s) {', '.join(extensions)} found.")
        else:
            print("No files found.")

    return uuid_mapping


def run(
    directory: str = ".",
    extensions: list = None,
    output_file: str = None,
    include_all: bool = False,
    config_path: str = None,
    verbose: bool = False,
    include_prepdir_files: bool = False,
    scrub_uuids: bool = None,
    scrub_hyphenless_uuids: bool = None,
    replacement_uuid: str = None,
    use_unique_placeholders: bool = False,
) -> Tuple[str, dict]:
    """
    Programmatically run prepdir to traverse a directory and prepare file contents.

    Args:
        directory (str): Directory to traverse (default: current directory).
        extensions (list): List of file extensions to include (without dot, e.g., ["py", "txt"]).
        output_file (str): Path to save output (if None, returns content as string).
        include_all (bool): If True, ignore exclusion lists in config.
        config_path (str): Path to custom configuration YAML file.
        verbose (bool): If True, log additional information about skipped files.
        include_prepdir_files (bool): If True, include prepdir-generated files.
        scrub_uuids (bool): If True, scrub UUIDs in file contents; if None, use config value.
        scrub_hyphenless_uuids (bool): If True, scrub hyphen-less UUIDs; if None, use config value.
        replacement_uuid (str): UUID to replace detected UUIDs with when use_unique_placeholders is False; if None, use config value.
        use_unique_placeholders (bool): If True, replace UUIDs with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n).

    Returns:
        Tuple[str, dict]: Formatted content of traversed files and a mapping of placeholders to original UUIDs.

    Raises:
        ValueError: If directory does not exist or is not a directory, or if replacement_uuid is invalid when use_unique_placeholders is False.
    """
    logger.debug(f"Running prepdir on directory: {directory}")
    # Validate directory
    if not os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' does not exist.")
    if not os.path.isdir(directory):
        raise ValueError(f"'{directory}' is not a directory.")

    # Load configuration
    config = load_config("prepdir", config_path)
    excluded_dirs = [] if include_all else config.get("exclude.directories", [])
    excluded_files = [] if include_all else config.get("exclude.files", [])

    # Log the loaded config values for debugging
    logger.debug(f"Loaded REPLACEMENT_UUID from config: {config.get('REPLACEMENT_UUID', 'Not set')}")
    logger.debug(f"Loaded SCRUB_UUIDS from config: {config.get('SCRUB_UUIDS', 'Not set')}")

    # Use config values if arguments are not provided
    scrub_uuids_enabled = config.get("SCRUB_UUIDS", True) if scrub_uuids is None else scrub_uuids
    scrub_hyphenless_uuids_enabled = (
        config.get("SCRUB_HYPHENLESS_UUIDS", False) if scrub_hyphenless_uuids is None else scrub_hyphenless_uuids
    )
    logger.debug(f"Scrub UUIDs enabled: {scrub_uuids_enabled}")
    replacement_uuid_config = config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000")
    replacement_uuid_final = replacement_uuid if replacement_uuid is not None else replacement_uuid_config
    logger.debug(f"Final REPLACEMENT_UUID: {replacement_uuid_final}")

    # Validate replacement UUID only if not using unique placeholders
    if not use_unique_placeholders and not is_valid_uuid(replacement_uuid_final):
        logger.error(f"Invalid replacement UUID: '{replacement_uuid_final}'. Using default nil UUID.")
        replacement_uuid_final = "00000000-0000-0000-0000-000000000000"

    # Capture output
    output = StringIO()
    with redirect_stdout(output):
        uuid_mapping = traverse_directory(
            directory,
            extensions,
            excluded_dirs,
            excluded_files,
            include_all,
            verbose,
            output_file=output_file,
            include_prepdir_files=include_prepdir_files,
            scrub_uuids_enabled=scrub_uuids_enabled,
            scrub_hyphenless_uuids_enabled=scrub_hyphenless_uuids_enabled,
            replacement_uuid=replacement_uuid_final,
            use_unique_placeholders=use_unique_placeholders,
        )

    content = output.getvalue()

    # Write to output file if specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)

    return content, uuid_mapping
