from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Dict, Optional
from prepdir.prepdir_file_entry import PrepdirFileEntry
import logging
import re

logger = logging.getLogger(__name__)

class PrepdirOutputFile(BaseModel):
    """Represents the prepdir output file (e.g., prepped_dir.txt) with metadata and file entries."""
    
    path: Optional[Path] = None
    content: str
    files: List[PrepdirFileEntry] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=lambda: {
        "version": "0.14.1",
        "date": datetime.now().isoformat(),
        "base_directory": ".",
        "creator": "prepdir",
        "scrub_hyphenated_uuids": "true",
        "scrub_hyphenless_uuids": "true",
        "use_unique_placeholders": "false",
        "validation_errors": [],
        "binary_files": []
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
        """Save the output file to disk."""
        if self.path:
            self.path.write_text(self.content, encoding="utf-8")
            logger.debug(f"Saved output to {self.path}")
        else:
            logger.warning("No path specified, content not saved")

    def parse(self, base_directory: str) -> List[PrepdirFileEntry]:
        """Parse the content to regenerate PrepdirFileEntry objects."""
        entries = []
        lines = self.content.splitlines()
        current_content = []
        current_file = None

        for line in lines:
            header_match = re.match(rf"^[-=]{3,}\s+Begin File: '(.*?)'\s+[-=]{3,}", line)
            footer_match = re.match(rf"^[-=]{3,}\s+End File: '(.*?)'\s+[-=]{3,}", line)

            if header_match:
                if current_file:
                    logger.warning(f"Unclosed file {current_file} encountered during parsing")
                current_file = header_match.group(1)
                current_content = []
            elif footer_match:
                if footer_match.group(1) != current_file:
                    logger.error(f"Mismatched footer {footer_match.group(1)} for header {current_file}")
                    continue
                if current_content:
                    entry = PrepdirFileEntry(
                        relative_path=current_file,
                        absolute_path=Path(base_directory) / current_file,
                        content="\n".join(current_content) + "\n",
                        uuid_mapping=self.uuid_mapping,
                        placeholder_counter=self.placeholder_counter
                    )
                    entries.append(entry)
                current_file = None
                current_content = []
            elif current_file:
                current_content.append(line)

        if current_file:
            logger.warning(f"Unclosed file {current_file} at end of content")
            entry = PrepdirFileEntry(
                relative_path=current_file,
                absolute_path=Path(base_directory) / current_file,
                content="\n".join(current_content) + "\n",
                uuid_mapping=self.uuid_mapping,
                placeholder_counter=self.placeholder_counter
            )
            entries.append(entry)

        self.files = entries
        return entries

    @classmethod
    def from_file(cls, path: str, base_directory: str) -> 'PrepdirOutputFile':
        """Create a PrepdirOutputFile instance from a file on disk."""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File {path} does not exist")
        
        content = path_obj.read_text(encoding="utf-8")
        header_match = re.search(r"^File listing generated (.*?)(?: by (.*?)(?: version (.*?))?(?: \(pip install prepdir\))?)", content, re.MULTILINE)
        metadata = {
            "version": header_match.group(3) if header_match and header_match.group(3) else "unknown",
            "date": header_match.group(1) if header_match and header_match.group(1) else "unknown",
            "base_directory": re.search(r"Base directory is '(.*?)'", content, re.MULTILINE).group(1) if re.search(r"Base directory is '(.*?)'", content, re.MULTILINE) else ".",
            "creator": header_match.group(2) if header_match and header_match.group(2) else "unknown",
            "scrub_hyphenated_uuids": "true",  # Default values, adjust based on config if needed
            "scrub_hyphenless_uuids": "true",
            "use_unique_placeholders": "false",
            "validation_errors": [],
            "binary_files": []
        }
        
        instance = cls(path=path_obj, content=content, metadata=metadata)
        instance.parse(base_directory)
        return instance

    def get_changed_files(self, original: 'PrepdirOutputFile') -> List[PrepdirFileEntry]:
        """Identify files that have changed compared to an original PrepdirOutputFile."""
        changed = []
        orig_files = {entry.relative_path: entry for entry in original.files}
        for entry in self.files:
            orig_entry = orig_files.get(entry.relative_path)
            if not orig_entry or entry.content != orig_entry.content:
                changed.append(entry)
        return changed