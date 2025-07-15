from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Dict, Optional, List
from prepdir.prepdir_file_entry import PrepdirFileEntry, BINARY_CONTENT_PLACEHOLDER
from prepdir.config import __version__
import logging
import re

logger = logging.getLogger(__name__)

# Compiled regex patterns for performance
LENIENT_DELIM_PATTERN = r"[=-]{3,}"
BEGIN_FILE_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+Begin File: '(.*?)'\s+{LENIENT_DELIM_PATTERN}$")
END_FILE_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+End File: '(.*?)'\s+{LENIENT_DELIM_PATTERN}$")
GENERATED_HEADER_PATTERN = re.compile(
    r"^File listing generated (\d{4}-\d{2}-\d{2}[\sT]+[\d\:\.\s]+\d)?(?:\s+by\s+(.*))?$", re.MULTILINE
)
BASE_DIR_PATTERN = re.compile(r"^Base directory is '(.*?)'$", re.MULTILINE)
METADATA_KEYS = ["date", "base_directory", "creator", "version"]


class PrepdirOutputFile(BaseModel):
    """Represents the prepdir output file (e.g., prepped_dir.txt) with metadata and file entries."""

    path: Optional[Path] = None
    content: str
    files: Dict[Path, PrepdirFileEntry] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(
        default_factory=lambda: {
            "version": __version__,
            "date": datetime.now().isoformat(),
            "base_directory": ".",
            "creator": "prepdir",
        }
    )
    use_unique_placeholders: bool
    uuid_mapping: Dict[str, str] = Field(default_factory=dict)
    placeholder_counter: int = 0

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        if not all(k in v for k in METADATA_KEYS):
            missing = set(METADATA_KEYS) - set(v.keys())
            raise ValueError(f"Metadata missing required keys: {missing}")
        if any(v[k] is None for k in METADATA_KEYS):
            raise ValueError(f"Metadata contains None values for required keys: {v}")
        return v

    @field_validator("path", mode="before")
    @classmethod
    def validate_path(cls, v):
        if v is not None and not isinstance(v, Path):
            return Path(v)
        return v

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        if not isinstance(v, str):
            raise ValueError("Content must be a string")
        return v

    def save(self, path_override: str = None):
        """Save the output to disk."""
        path_for_save = Path(path_override) if path_override else self.path

        if path_for_save:
            if self.content:
                try:
                    path_for_save.write_text(self.content, encoding="utf-8")
                    logger.info(f"Saved output to {path_for_save}")
                except FileNotFoundError as e:
                    logger.error(f"Could not save output to {path_for_save}: {str(e)}")
                    raise ValueError(f"Could not save output to {path_for_save}: {str(e)}") from e
                except PermissionError as e:
                    logger.exception(f"Could not save output to {path_for_save}: PermissionError: {str(e)}")
                    raise
                except Exception as e:
                    logger.exception(f"Could not save output to {path_for_save}: Unexpected exception: {str(e)}")
                    raise

            else:
                logger.warning("No content specified, content not saved")
        else:
            logger.warning("No path specified, content not saved")

    def parse(self, base_directory: str) -> Dict[Path, PrepdirFileEntry]:
        """Parse the content to regenerate PrepdirFileEntry objects and return a dict of abs_path to entries."""
        entries = {}
        lines = self.content.splitlines()
        logger.debug(f"{len(lines)} lines to parse")
        current_content = []
        current_file = None

        file_and_line_being_parsed = "Unknown"
        if self.path:
            file_and_line_being_parsed = str(self.path)
            file_and_line_being_parsed += f":{str(len(current_content))}" if current_content else ""

        for line in lines:
            begin_file_match = BEGIN_FILE_PATTERN.match(line)
            end_file_match = END_FILE_PATTERN.match(line)

            if begin_file_match and current_file is None:
                current_file = begin_file_match.group(1)
                current_content = []

            elif end_file_match:
                if current_file is None:
                    logger.warning(f" {file_and_line_being_parsed}: Footer found without matching header: {line}")
                elif end_file_match.group(1) != current_file:
                    logger.warning(
                        f" {file_and_line_being_parsed} - Mismatched footer '{end_file_match.group(1)}' for header '{current_file}', treating as content"
                    )
                    current_content.append(line)
                else:
                    if current_content:
                        file_path = Path(current_file)
                        abs_path = Path(base_directory).absolute() / file_path
                        entry = PrepdirFileEntry(
                            relative_path=current_file,
                            absolute_path=abs_path,
                            content="\n".join(current_content) + "\n",
                            is_binary=BINARY_CONTENT_PLACEHOLDER in current_content,
                            is_scrubbed=False,
                        )
                        entries[abs_path] = entry
                        logger.debug(f"Added {abs_path} to entries")
                    current_file = None
                    current_content = []
            elif begin_file_match or end_file_match:
                logger.warning(
                    f" {file_and_line_being_parsed} - Extra header/footer '{line}' encountered for current file '{current_file}', treating as content"
                )
                current_content.append(line)
            elif current_file:
                current_content.append(line)

        if current_file:
            raise ValueError(f"Unclosed file '{current_file}' at end of content")

        self.files = entries  # Directly assign the dict
        return entries

    @classmethod
    def from_file(
        cls,
        path: str,
        uuid_mapping: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        use_unique_placeholders: Optional[bool] = False,
    ) -> "PrepdirOutputFile":
        """Create a PrepdirOutputFile instance from a file on disk."""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File {path} does not exist")
        content = path_obj.read_text(encoding="utf-8")
        return cls.from_content(content, path_obj, uuid_mapping, metadata, use_unique_placeholders)

    @classmethod
    def from_content(
        cls,
        content: str,
        path_obj: Optional[Path] = None,
        uuid_mapping: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        use_unique_placeholders: Optional[bool] = False,
    ) -> "PrepdirOutputFile":
        """Create a PrepdirOutputFile instance from content (already read from file or otherwise previously created)."""
        lines = content.splitlines()
        logger.debug(f"Got {len(lines)} lines of content")

        # Extract output_file_header up to the first BEGIN_FILE_PATTERN line
        output_file_header = []
        begin_file_pattern_found = False
        for line in lines:
            if BEGIN_FILE_PATTERN.match(line):
                begin_file_pattern_found = True
                logger.debug(f"Found begin file pattern in line: {line}")
                break
            output_file_header.append(line)
        output_file_header = "\n".join(output_file_header)

        if not begin_file_pattern_found:
            logger.debug(f"No begin file patterns found! content:\n{content}")
            raise ValueError(f"No begin file patterns found!")

        # If metadata values were passed, use them. Otherwise try to pull them from the content.
        new_metadata = {}
        for k in METADATA_KEYS:
            if metadata and k in metadata:
                new_metadata[k] = metadata[k]
            else:
                new_metadata[k] = ""

        # Search header section with re.MULTILINE if it exists
        gen_header_match = GENERATED_HEADER_PATTERN.search(output_file_header) if output_file_header else None

        if gen_header_match:
            # Found a general header, verify it matches the metadata if it was passed, and if no metadata was passed then set it
            header_value = {}
            header_value["date"] = gen_header_match.group(1) or None
            header_value["creator"] = gen_header_match.group(2) or None

            for header_key in header_value.keys():
                if header_value[header_key]:
                    if not new_metadata[header_key]:
                        new_metadata[header_key] = header_value[header_key]
                        logger.debug(f"Set metadata {header_key}={header_value[header_key]} from header")
                    elif new_metadata[header_key] != header_value[header_key]:
                        logger.warning(
                            f"Passed metadata for {header_key} ({new_metadata[header_key]}) and header date ({header_value[header_key]}) do not match. Using header value."
                        )
                        # Header value wins
                        new_metadata[header_key] = header_value[header_key]

        # Determine the base directory if we can
        base_dir_match = BASE_DIR_PATTERN.search(output_file_header) if output_file_header else None

        # Determine the base directory
        if base_dir_match:
            # Got a base directory from the file header
            header_base_dir = str(base_dir_match.group(1))
            if header_base_dir:
                if not new_metadata["base_directory"]:
                    new_metadata["base_directory"] = header_base_dir
                    logger.debug(f"Set metadata 'base_directory={header_base_dir} from header")
                elif new_metadata["base_directory"] != header_base_dir:
                    logger.warning(
                        f"Passed metadata for base_directory ({new_metadata['base_directory']}) and header base dir ({header_base_dir}) do not match. Will use header base dir."
                    )
                    # Header value wins
                    new_metadata["base_directory"] = header_base_dir

        if not new_metadata["base_directory"]:
            raise ValueError("Could not determine base directory from header and not passed in metadata")

        logger.debug(f"{path_obj=}")
        instance = cls(
            path=path_obj,
            content=content,
            metadata=new_metadata,
            uuid_mapping=uuid_mapping or {},
            use_unique_placeholders=use_unique_placeholders,
        )
        logger.debug(f"{instance=}")
        instance.parse(new_metadata["base_directory"])
        return instance

    def get_changed_files(self, original: "PrepdirOutputFile") -> Dict[str, List[PrepdirFileEntry]]:
        """Identify files that have changed compared to an original PrepdirOutputFile.
        Returns a dictionary with:
        - 'added': List of PrepdirFileEntry objects present in current but not in original.
        - 'changed': List of PrepdirFileEntry objects present in both with modified content.
        - 'removed': List of PrepdirFileEntry objects present in original but not in current.
        """
        added = []
        changed = []
        removed = []

        # Check for added or changed files
        for entry in self.files.values():
            orig_entry = original.files.get(entry.absolute_path)
            if not orig_entry:
                added.append(entry)
            elif entry.content != orig_entry.content:
                changed.append(entry)

        # Check for removed files
        for abs_path in original.files.keys():
            current_entry = self.files.get(abs_path)
            if not current_entry:
                removed.append(original.files[abs_path])

        return {"added": added, "changed": changed, "removed": removed}
