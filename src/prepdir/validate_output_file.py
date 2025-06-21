import re
import os
import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

# Pattern for lenient delimiter (3 or more - or = characters)
LENIENT_DELIM_PATTERN = r"[-=]{3,}"


def _process_header_lines(lines: List[str], first_non_blank_index: int) -> Tuple[Dict, List, int]:
    """
    Process potential header lines (file listing and base directory).

    Args:
        lines: List of file lines.
        first_non_blank_index: Index of first non-blank line.

    Returns:
        Tuple of (creation dict, warnings list, next line index).
    """
    creation = {"date": "unknown", "creator": "unknown", "version": "unknown"}
    warnings = []
    next_index = first_non_blank_index

    if first_non_blank_index >= len(lines):
        warnings.append("File contains only blank lines, but no valid file content.")
        return creation, warnings, next_index

    # Check for file listing header
    first_line = lines[first_non_blank_index].strip()
    initial_header_match = re.match(
        r"^\s*file\s+listing\s+generated\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*"
        r"(?:by\s+([^\s]+)\s*(?:version\s+([\d.]+))?)?(?:\s*\(pip\s+install\s+[^\)]+\))?\s*$",
        first_line,
        re.IGNORECASE,
    )
    if initial_header_match:
        creation["date"] = initial_header_match.group(1) or "unknown"
        creation["creator"] = initial_header_match.group(2) or "unknown"
        creation["version"] = initial_header_match.group(3) or "unknown"
        next_index += 1
    else:
        warnings.append(
            f"Line {first_non_blank_index + 1}: Missing or invalid file listing header. Got: '{first_line}'"
        )

    # Skip blank lines after potential header
    while next_index < len(lines) and not lines[next_index].strip():
        next_index += 1

    # Check for base directory line
    if next_index < len(lines):
        base_dir_line = lines[next_index].strip()
        if re.match(r"^\s*base\s+directory\s+is\s+.*$", base_dir_line, re.IGNORECASE):
            next_index += 1
        else:
            warnings.append(f"Line {next_index + 1}: Missing or invalid base directory line. Got: '{base_dir_line}'")

    return creation, warnings, next_index


def _parse_file_sections(lines: List[str], start_index: int) -> Tuple[Dict, List, List, set]:
    """
    Parse file sections from lines starting at given index.

    Args:
        lines: List of file lines.
        start_index: Index to start parsing from.

    Returns:
        Tuple of (files_content dict, errors list, warnings list, seen_file_paths set).
    """
    files_content = {}
    errors = []
    warnings = []
    seen_file_paths = set()
    open_headers = []
    current_file = None
    current_content = []

    for line_number, line in enumerate(lines[start_index:], start_index + 1):
        stripped_line = line.rstrip("\n")
        if not stripped_line:
            if current_file:
                current_content.append(stripped_line)
            continue

        # Check for header
        header_match = re.match(
            rf"^{LENIENT_DELIM_PATTERN}\s+begin\s+file\s*:\s*['\"](.*?)['\"]\s*{LENIENT_DELIM_PATTERN}$",
            stripped_line,
            re.IGNORECASE,
        )
        if header_match:
            file_path = header_match.group(1).strip()
            if not file_path:
                errors.append(f"Line {line_number}: Empty file path in header.")
                continue
            if file_path in seen_file_paths:
                warnings.append(f"Line {line_number}: Duplicate file path '{file_path}' detected.")
            else:
                seen_file_paths.add(file_path)
            if os.path.isabs(file_path) or ".." in os.path.split(file_path):
                warnings.append(f"Line {line_number}: Suspicious file path '{file_path}' (absolute or contains '..').")
            elif not re.match(r"^[\w\-\./]+$", file_path):
                warnings.append(f"Line {line_number}: File path '{file_path}' contains unusual characters.")
            if current_file:
                files_content[current_file] = "\n".join(current_content)
                current_content = []
            open_headers.append((file_path, line_number))
            current_file = file_path
            logger.debug(f"Header found: {stripped_line}")
            continue

        # Check for footer
        footer_match = re.match(
            rf"^{LENIENT_DELIM_PATTERN}\s+end\s+file\s*:\s*['\"](.*?)['\"]\s*{LENIENT_DELIM_PATTERN}$",
            stripped_line,
            re.IGNORECASE,
        )
        if footer_match:
            file_path = footer_match.group(1).strip()
            if not file_path:
                errors.append(f"Line {line_number}: Empty file path in footer.")
                continue
            if not open_headers:
                errors.append(f"Line {line_number}: Footer for '{file_path}' without matching header.")
            else:
                last_header_path, header_line = open_headers[-1]
                if last_header_path != file_path:
                    errors.append(
                        f"Line {line_number}: Footer for '{file_path}' does not match open header "
                        f"'{last_header_path}' from line {header_line}."
                    )
                else:
                    if current_file:
                        files_content[current_file] = "\n".join(current_content)
                        current_content = []
                        current_file = None
                    open_headers.pop()
            logger.debug(f"Footer found: {stripped_line}")
            continue

        # Check for malformed header or footer
        if re.match(rf"^{LENIENT_DELIM_PATTERN}\s+begin\s+file\s*:", stripped_line, re.IGNORECASE):
            errors.append(f"Line {line_number}: Malformed header: '{stripped_line}'")
            if current_file:
                current_content.append(stripped_line)
            logger.debug(f"Malformed header: {stripped_line}")
            continue

        if re.match(rf"^{LENIENT_DELIM_PATTERN}\s+end\s+file\s*:", stripped_line, re.IGNORECASE):
            errors.append(f"Line {line_number}: Malformed footer: '{stripped_line}'")
            if current_file:
                current_content.append(stripped_line)
            logger.debug(f"Malformed footer: {stripped_line}")
            continue

        # Collect content
        if current_file:
            current_content.append(stripped_line)

    # Finalize open file content
    if current_file:
        files_content[current_file] = "\n".join(current_content)

    # Check for unclosed headers
    for file_path, header_line in open_headers:
        errors.append(f"Line {header_line}: Header for '{file_path}' has no matching footer.")

    return files_content, errors, warnings, seen_file_paths


def validate_output_file(file_path: str) -> Dict:
    """
    Validate a prepdir-generated or LLM-edited output file to ensure it has correct structure.

    Args:
        file_path (str): Path to the output file to validate.

    Returns:
        Dict: Validation result with keys:
            - is_valid (bool): True if the file is valid, False otherwise.
            - errors (List): List of error messages for invalid structure.
            - warnings (List): List of warning messages for minor issues.
            - files (Dict): Dictionary mapping file paths to their contents.
            - creation (Dict): Dictionary containing creator, date, and version from the header.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file cannot be read as text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' does not exist.")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        raise UnicodeDecodeError("File cannot be read as text.", b"", 0, 0, "Invalid encoding")

    if not lines:
        return {
            "is_valid": False,
            "errors": ["File is empty."],
            "warnings": [],
            "files": {},
            "creation": {"date": "unknown", "creator": "unknown", "version": "unknown"},
        }

    # Find first non-blank line
    first_non_blank_index = 0
    while first_non_blank_index < len(lines) and not lines[first_non_blank_index].strip():
        first_non_blank_index += 1

    # Process header lines (file listing and base directory)
    creation, warnings, next_index = _process_header_lines(lines, first_non_blank_index)

    # Parse file sections
    files_content, errors, section_warnings, _ = _parse_file_sections(lines, next_index)
    warnings.extend(section_warnings)

    # Determine validity
    is_valid = len(errors) == 0 and len(files_content) > 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "files": files_content,
        "creation": creation,
    }
