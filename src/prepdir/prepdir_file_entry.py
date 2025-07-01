from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
import logging
from .scrub_uuids import scrub_uuids, restore_uuids

logger = logging.getLogger(__name__)


BINARY_CONTENT_PLACEHOLDER = "[Binary file or encoding not currently supported by prepdir]"

class PrepdirFileEntry(BaseModel):
    """Represents a single project file's metadata, content, and UUID mappings for prepdir processing."""

    relative_path: str = Field(..., description="Path relative to base directory")
    absolute_path: Path = Field(..., description="Absolute path to the file")
    content: str = Field(..., description="File content, possibly scrubbed")
    is_scrubbed: bool = Field(default=False, description="Whether UUIDs are scrubbed in the current content")
    is_binary: bool = Field(default=False, description="Whether the file is binary")
    error: Optional[str] = Field(default=None, description="Error message if file read failed")

    @field_validator("absolute_path", mode="before")
    @classmethod
    def validate_path(cls, v):
        """Convert string to Path if necessary and ensure it's absolute."""
        abs_path = Path(v) if isinstance(v, str) else v
        if not abs_path.is_absolute():
            raise ValueError("absolute_path must be an absolute path")
        return abs_path

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, v):
        """Ensure relative_path is not absolute."""
        if Path(v).is_absolute():
            raise ValueError("relative_path must not be an absolute path")
        return v

    @classmethod
    def from_file_path(
        cls,
        file_path: Path,
        base_directory: str,
        scrub_hyphenated_uuids: bool,
        scrub_hyphenless_uuids: bool,
        replacement_uuid: str = "00000000-0000-0000-0000-000000000000",
        use_unique_placeholders: bool = False,
        verbose: bool = False,
        placeholder_counter: int = 1,
        uuid_mapping: Dict[str, str] = None,
    ) -> Tuple["PrepdirFileEntry", Dict[str, str], int]:
        """Create a PrepdirFileEntry by reading a file, optionally scrubbing UUIDs.

        Args:
            file_path: Path to the input file (absolute or relative to base_directory).
            base_directory: Base directory for resolving relative paths.
            scrub_hyphenated_uuids: If True, scrub hyphenated UUIDs (e.g., 123e4567-e89b-12d3-a456-426614174000).
            scrub_hyphenless_uuids: If True, scrub hyphen-less UUIDs (e.g., 123e4567e89b12d3a456426614174000).
            replacement_uuid: UUID to use as replacement when use_unique_placeholders=False.
            use_unique_placeholders: If True, use unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n).
            verbose: If True, log scrubbing details.
            placeholder_counter: Starting counter for unique placeholders.
            uuid_mapping: Shared mapping of placeholders to original UUIDs for reuse.

        Returns:
            Tuple of (PrepdirFileEntry instance, updated uuid_mapping, updated placeholder_counter).

        Raises:
            FileNotFoundError: If file_path does not exist.
            ValueError: If replacement_uuid is invalid or paths are invalid.
        """
        import os

        # Ensure file_path is absolute
        file_path = file_path if file_path.is_absolute() else Path(base_directory) / file_path
        file_path = file_path.resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.debug(f"instantiating from {file_path}")

        relative_path = os.path.relpath(file_path, base_directory)
        content = ""
        is_binary = False
        error = None
        is_scrubbed = False
        uuid_mapping = uuid_mapping if uuid_mapping is not None else {}

        try:
            with open(file_path, "rb") as f:  # Read as binary first
                raw_content = f.read()
                try:
                    content = raw_content.decode("utf-8")
                    logger.debug("decoded with utf-8")
                    if scrub_hyphenated_uuids or scrub_hyphenless_uuids:
                        content, is_scrubbed, updated_uuid_mapping, updated_counter = scrub_uuids(
                            content=content,
                            use_unique_placeholders=use_unique_placeholders,
                            replacement_uuid=replacement_uuid,
                            scrub_hyphenated_uuids=scrub_hyphenated_uuids,
                            scrub_hyphenless_uuids=scrub_hyphenless_uuids,
                            verbose=verbose,
                            placeholder_counter=placeholder_counter,
                            uuid_mapping=uuid_mapping,
                        )
                        uuid_mapping.update(updated_uuid_mapping)
                except UnicodeDecodeError:
                    logger.debug("got UnicodeDecodeError with utf-8, presuming binary")
                    is_binary = True
                    content = BINARY_CONTENT_PLACEHOLDER
        except Exception as e:
            error = str(e)
            content = f"[Error reading file: {error}]"

        return (
            cls(
                relative_path=relative_path,
                absolute_path=file_path,
                content=content,
                is_scrubbed=is_scrubbed,
                is_binary=is_binary,
                error=error,
            ),
            uuid_mapping,
            updated_counter if is_scrubbed else placeholder_counter,
        )

    def to_output(self, format: str = "text") -> str:
        """Generate formatted output for prepped_dir.txt.

        Args:
            format: Output format (only 'text' supported).

        Returns:
            Formatted string for the file entry.

        Raises:
            ValueError: If format is unsupported.
        """
        if format != "text":
            raise ValueError(f"Unsupported output format: {format}")
        dashes = "=-" * 7 + "="  # See LENIENT_DELIM_PATTERN for requirements here if considering changing this
        output = [
            f"{dashes} Begin File: '{self.relative_path}' {dashes}",
            self.content,
            f"{dashes} End File: '{self.relative_path}' {dashes}",
        ]
        return "\n".join(output)

    def restore_uuids(self, uuid_mapping: Dict[str, str]) -> str:
        """Restore original UUIDs in content using uuid_mapping.

        Args:
            uuid_mapping: Dictionary mapping placeholders to original UUIDs.

        Returns:
            Content with placeholders replaced by original UUIDs.

        Raises:
            ValueError: If uuid_mapping is None or empty when is_scrubbed is True.
        """
        if self.is_scrubbed and (not uuid_mapping or not isinstance(uuid_mapping, dict)):
            logger.error(f"No valid uuid_mapping provided for {self.relative_path}")
            raise ValueError("uuid_mapping must be a non-empty dictionary when is_scrubbed is True")
        restored_content = restore_uuids(
            content=self.content,
            uuid_mapping=uuid_mapping,
            is_scrubbed=self.is_scrubbed,
        )
        return restored_content  # Return new content instead of modifying in-place

    def apply_changes(self, uuid_mapping: Dict[str, str]) -> bool:
        """Write restored content to absolute_path.

        Args:
            uuid_mapping: Dictionary mapping placeholders to original UUIDs.

        Returns:
            True if successful, False otherwise.

        Raises:
            Exception: If writing to file fails.
        """
        if self.is_binary or self.error:
            logger.warning(
                f"Skipping apply_changes for {self.relative_path}: {'binary' if self.is_binary else 'error'}"
            )
            return False
        try:
            restored_content = self.restore_uuids(uuid_mapping)
            self.absolute_path.write_text(restored_content, encoding="utf-8")
            logger.info(f"Applied changes to {self.relative_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply changes to {self.relative_path}: {str(e)}")
            self.error = str(e)
            return False

    @staticmethod
    def is_prepdir_outputfile_format(content: str, highest_base_directory: Optional[str] = None) -> bool:
        """Return true if the given content matches the format prescribed for a prepdir output file.

        Args:
            content: The file content to check.
            highest_base_directory: The base directory for resolving relative paths (optional, defaults to None for format-only check).

        Returns:
            bool: True if the content matches the prepdir output format, False otherwise.
        """
        try:
            from .prepdir_output_file import PrepdirOutputFile

            PrepdirOutputFile.from_content(content, highest_base_directory)
            return True
        except ValueError:
            return False
