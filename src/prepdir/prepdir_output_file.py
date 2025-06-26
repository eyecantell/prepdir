from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Dict, Optional, List
from prepdir.prepdir_file_entry import PrepdirFileEntry
from prepdir.config import __version__
import logging
import re

logger = logging.getLogger(__name__)

# Compiled regex patterns for performance
LENIENT_DELIM_PATTERN = r"[=-]{3,}"
HEADER_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+Begin File: '(.*?)'\s+{LENIENT_DELIM_PATTERN}$")
FOOTER_PATTERN = re.compile(rf"^{LENIENT_DELIM_PATTERN}\s+End File: '(.*?)'\s+{LENIENT_DELIM_PATTERN}$")
GENERATED_HEADER_PATTERN = re.compile(
    r"^File listing generated (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)?(?: by (.*))$", re.MULTILINE
)
BASE_DIR_PATTERN = re.compile(r"^Base directory is '(.*?)'$", re.MULTILINE)

class PrepdirOutputFile(BaseModel):
    """Represents the prepdir output file (e.g., prepped_dir.txt) with metadata and file entries."""
    
    path: Optional[Path] = None
    content: str
    files: Dict[Path, PrepdirFileEntry] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=lambda: {
        "version": __version__,
        "date": datetime.now().isoformat(),
        "base_directory": ".",
        "creator": "prepdir",
        "scrub_hyphenated_uuids": "true",
        "scrub_hyphenless_uuids": "true",
        "use_unique_placeholders": "false"
    })
    uuid_mapping: Dict[str, str] = Field(default_factory=dict)
    placeholder_counter: int = 0

    @field_validator('path', mode='before')
    @classmethod
    def validate_path(cls, v):
        if v is not None and not isinstance(v, Path):
            return Path(v)
        return v

    @field_validator('content', mode='before')
    @classmethod
    def validate_content(cls, v):
        if not isinstance(v, str):
            raise ValueError("Content must be a string")
        return v

    def save(self):
        """Save the output to disk."""
        if self.path:
            self.path.write_text(self.content, encoding="utf-8")
            logger.debug(f"Saved output to {self.path}")
        else:
            logger.warning("No path specified, content not saved")

    def parse(self, base_directory: str) -> Dict[Path, PrepdirFileEntry]:
        """Parse the content to regenerate PrepdirFileEntry objects and return a dict of abs_path to entries."""
        entries = {}
        lines = self.content.splitlines()
        current_content = []
        current_file = None

        for line in lines:
            header_match = HEADER_PATTERN.match(line)
            footer_match = FOOTER_PATTERN.match(line)

            if header_match and current_file is None:
                current_file = header_match.group(1)
                current_content = []
            elif footer_match:
                if current_file is None:
                    logger.warning(f"Footer found without matching header on line: {line}")
                elif footer_match.group(1) != current_file:
                    logger.warning(f"Mismatched footer '{footer_match.group(1)}' for header '{current_file}', treating as content")
                    current_content.append(line)
                else:
                    if current_content:
                        file_path = Path(current_file)
                        abs_path = Path(base_directory).absolute() / file_path
                        entry = PrepdirFileEntry(
                            relative_path=current_file,
                            absolute_path=abs_path,
                            content="\n".join(current_content) + "\n",
                            is_binary=False,  # Explicitly set to satisfy validation
                            is_scrubbed=False,
                        )
                        entries[abs_path] = entry
                    current_file = None
                    current_content = []
            elif header_match or footer_match:
                logger.warning(f"Extra header/footer '{line}' encountered for current file '{current_file}', treating as content")
                current_content.append(line)
            elif current_file:
                current_content.append(line)

        if current_file:
            raise ValueError(f"Unclosed file '{current_file}' at end of content")

        self.files = entries  # Directly assign the dict
        return entries

    @classmethod
    def from_file(cls, path: str, expected_base_directory: Optional[str] = None) -> 'PrepdirOutputFile':
        """Create a PrepdirOutputFile instance from a file on disk."""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File {path} does not exist")
        content = path_obj.read_text(encoding="utf-8")
        return cls.from_content(content, expected_base_directory, path_obj)

    @classmethod
    def from_content(cls, content: str, expected_base_directory: Optional[str] = None, path_obj: Optional[Path] = None) -> 'PrepdirOutputFile':
        """Create a PrepdirOutputFile instance from content already read from file."""
        lines = content.splitlines()
        
        # Extract output_file_header up to the first HEADER_PATTERN line
        output_file_header = []
        header_found = False
        for line in lines:
            if HEADER_PATTERN.match(line):
                header_found = True
                break
            output_file_header.append(line)
        output_file_header = "\n".join(output_file_header)

        if not header_found:
            raise ValueError("No file headers found!")

        # Search header section with re.MULTILINE if it exists
        gen_header_match = GENERATED_HEADER_PATTERN.search(output_file_header) if output_file_header else None
        base_dir_match = BASE_DIR_PATTERN.search(output_file_header) if output_file_header else None

        # Determine effective base directory
        if base_dir_match:
            # Got a base directory ifrom the file
            file_base_dir = Path(base_dir_match.group(1))
            effective_base_dir = str(file_base_dir)

            if expected_base_directory is not None:
                # Test to see that the base directory agrees with the passed expected base dir
                expected_base_path = Path(expected_base_directory)
                if not (file_base_dir == expected_base_path or file_base_dir.is_relative_to(expected_base_path)):
                    raise ValueError(f"Base directory mismatch: File-defined base directory '{file_base_dir}' is not the same as or relative to expected base directory '{expected_base_path}'")
                
        elif expected_base_directory is not None:
            logger.warning("No base directory found in file, using expected base directory: %s", expected_base_directory)
            effective_base_dir = expected_base_directory
        else:
            raise ValueError("Cannot determine base directory: not in file and no expected base dir passed")

        # Use header metadata if available, otherwise keep defaults
        metadata = {
            
            "date": gen_header_match.group(1) if gen_header_match and gen_header_match.group(1) else "unknown",
            "base_directory": effective_base_dir,
            "creator": gen_header_match.group(2) if gen_header_match and gen_header_match.group(2) else "unknown",
            "scrub_hyphenated_uuids": "true",  # Default values, adjust based on config if needed
            "scrub_hyphenless_uuids": "true",
            "use_unique_placeholders": "false"
        }
        if not gen_header_match:
            logger.warning("No header found in file, using default metadata")

        instance = cls(path=path_obj, content=content, metadata=metadata)
        if effective_base_dir is not None:
            instance.parse(effective_base_dir)
        return instance

    def get_changed_files(self, original: 'PrepdirOutputFile') -> List[PrepdirFileEntry]:
        """Identify files that have changed compared to an original PrepdirOutputFile."""
        changed = []
        orig_files = {entry.absolute_path: entry for entry in original.files.values()}  # Use dict values
        for entry in self.files.values():
            orig_entry = orig_files.get(entry.absolute_path)
            if not orig_entry or entry.content != orig_entry.content:
                changed.append(entry)
        return changed