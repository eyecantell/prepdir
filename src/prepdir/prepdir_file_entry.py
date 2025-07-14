from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
import logging
import sys
from .scrub_uuids import scrub_uuids, restore_uuids

logger = logging.getLogger("prepdir.prepdir_file_entry")

BINARY_CONTENT_PLACEHOLDER = "[Binary file or encoding not currently supported by prepdir]"
PREPDIR_DASHES = (
    "=-" * 7 + "="
)  # The dases used on either side of a Begin File: or End File: label - See LENIENT_DELIM_PATTERN for requirements here if considering changing this


class PrepdirFileEntry(BaseModel):
    """Pydantic model for file entries in the prepdir package.

    Represents a single project file's metadata, content, and UUID mappings for processing by prepdir.

    Attributes:
        relative_path (str): Path to the file, relative to the base directory specified.
        absolute_path (Path): Absolute path to the file on the filesystem.
        content (str): Content of the file, possibly with UUIDs scrubbed.
        is_scrubbed (bool): Whether the content has had UUIDs replaced with placeholders.
        is_binary (bool): Whether the file is binary (or has an unsupported encoding).
        error (Optional[str]): Error message if the file could not be read or processed.
    """

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
        quiet: bool = False,
        placeholder_counter: int = 1,
        uuid_mapping: Dict[str, str] = None,
    ) -> Tuple["PrepdirFileEntry", Dict[str, str], int]:
        """Create a PrepdirFileEntry by reading a file, optionally scrubbing UUIDs.

        Args:
            file_path (Path): Path to the file to read.
            base_directory (str): Base directory for computing relative_path.
            scrub_hyphenated_uuids (bool): Whether to scrub hyphenated UUIDs.
            scrub_hyphenless_uuids (bool): Whether to scrub hyphenless UUIDs.
            replacement_uuid (str): UUID to replace scrubbed UUIDs with (if not using unique placeholders).
            use_unique_placeholders (bool): Whether to use unique placeholders instead of a fixed UUID.
            quiet (bool): If True, suppress user-facing output to stdout/stderr.
            placeholder_counter (int): Starting counter for unique placeholders.
            uuid_mapping (Dict[str, str]): Existing mapping of placeholders to original UUIDs.

        Returns:
            Tuple[PrepdirFileEntry, Dict[str, str], int]: The file entry, updated UUID mapping, and updated placeholder counter.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: For other file reading or processing errors.
        """
        import os

        try:
            # Ensure file_path is absolute
            file_path = file_path if file_path.is_absolute() else Path(base_directory) / file_path
            file_path = file_path.resolve()

            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                if not quiet:
                    print(f"Error: File not found: {file_path}", file=sys.stderr)
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
                                verbose=True,  # Enable verbose logging for UUID replacements
                                placeholder_counter=placeholder_counter,
                                uuid_mapping=uuid_mapping,
                            )
                            uuid_mapping.update(updated_uuid_mapping)
                            if not quiet and is_scrubbed:
                                print(f"Scrubbed UUIDs in {relative_path}", file=sys.stdout)
                    except UnicodeDecodeError:
                        logger.debug("got UnicodeDecodeError with utf-8, presuming binary")
                        is_binary = True
                        content = BINARY_CONTENT_PLACEHOLDER
                        if not quiet:
                            print(f"File {relative_path} is binary or encoding not supported", file=sys.stdout)
                    except Exception as e:
                        error = str(e)
                        content = f"[Error reading file: {error}]"
                        logger.error(f"Failed to read {file_path}: {error}")
                        if not quiet:
                            print(f"Error: Failed to read {file_path}: {error}", file=sys.stderr)
            except Exception as e:
                error = str(e)
                content = f"[Error reading file: {error}]"
                logger.error(f"Failed to read {file_path}: {error}")
                if not quiet:
                    print(f"Error: Failed to read {file_path}: {error}", file=sys.stderr)

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
        except Exception as e:
            logger.error(f"Failed to create PrepdirFileEntry for {file_path}: {str(e)}")
            if not quiet:
                print(f"Error: Failed to create PrepdirFileEntry for {file_path}: {str(e)}", file=sys.stderr)
            raise

    def to_output(self, format: str = "text") -> str:
        """Generate formatted output for prepped_dir.txt.

        Args:
            format (str): Output format (currently only "text" is supported).

        Returns:
            str: Formatted string with file content and delimiters.

        Raises:
            ValueError: If an unsupported format is specified.
        """
        if format != "text":
            raise ValueError(f"Unsupported output format: {format}")
        output = [
            f"{PREPDIR_DASHES} Begin File: '{self.relative_path}' {PREPDIR_DASHES}",
            self.content,
            f"{PREPDIR_DASHES} End File: '{self.relative_path}' {PREPDIR_DASHES}",
        ]
        return "\n".join(output)

    def restore_uuids(self, uuid_mapping: Dict[str, str], quiet: bool = False) -> str:
        """Restore original UUIDs in the file content using the provided UUID mapping.

        Args:
            uuid_mapping (Dict[str, str]): Mapping of placeholders to original UUIDs.
            quiet (bool): If True, suppress user-facing output to stdout/stderr.

        Returns:
            str: Content with original UUIDs restored.

        Raises:
            ValueError: If uuid_mapping is invalid when is_scrubbed is True.
        """
        try:
            if self.is_scrubbed and (not uuid_mapping or not isinstance(uuid_mapping, dict)):
                logger.error(f"No valid uuid_mapping provided for {self.relative_path}")
                if not quiet:
                    print(f"Error: No valid uuid_mapping provided for {self.relative_path}", file=sys.stderr)
                raise ValueError("uuid_mapping must be a non-empty dictionary when is_scrubbed is True")

            restored_content = restore_uuids(
                content=self.content,
                uuid_mapping=uuid_mapping,
                is_scrubbed=self.is_scrubbed,
            )
            if not quiet and self.is_scrubbed:
                print(f"Restored UUIDs in {self.relative_path}", file=sys.stdout)
            logger.info(f"Restored UUIDs in {self.relative_path}")  # Changed to INFO to match scrub_uuids.py
            return restored_content
        except Exception as e:
            logger.error(f"Failed to restore UUIDs for {self.relative_path}: {str(e)}")
            if not quiet:
                print(f"Error: Failed to restore UUIDs for {self.relative_path}: {str(e)}", file=sys.stderr)
            raise

    def apply_changes(self, uuid_mapping: Dict[str, str], quiet: bool = False) -> bool:
        """Write restored content back to the file at absolute_path.

        Args:
            uuid_mapping (Dict[str, str]): Mapping of placeholders to original UUIDs.
            quiet (bool): If True, suppress user-facing output to stdout/stderr.

        Returns:
            bool: True if changes were applied successfully, False otherwise.

        Raises:
            Exception: If writing to the file fails.
        """
        try:
            if self.is_binary or self.error:
                logger.warning(
                    f"Skipping apply_changes for {self.relative_path}: {'binary' if self.is_binary else 'error'}"
                )
                if not quiet:
                    print(
                        f"Warning: Skipping apply_changes for {self.relative_path}: {'binary' if self.is_binary else 'error'}",
                        file=sys.stdout,
                    )
                return False
            restored_content = self.restore_uuids(uuid_mapping, quiet=quiet)
            self.absolute_path.write_text(restored_content, encoding="utf-8")
            logger.info(f"Applied changes to {self.relative_path}")  # Changed to INFO to match scrub_uuids.py
            if not quiet:
                print(f"Applied changes to {self.relative_path}", file=sys.stdout)
            return True
        except Exception as e:
            logger.error(f"Failed to apply changes to {self.relative_path}: {str(e)}")
            if not quiet:
                print(f"Error: Failed to apply changes to {self.relative_path}: {str(e)}", file=sys.stderr)
            self.error = str(e)
            return False

    @staticmethod
    def is_prepdir_outputfile_format(
        content: str, highest_base_directory: Optional[str] = None, file_full_path: Optional[str] = None
    ) -> bool:
        """Check if the given content matches the format expected for a prepdir output file.

        Args:
            content (str): The content to check.
            highest_base_directory (Optional[str]): Optional base directory for validation.
            file_full_path (Optional[str]): Optional full path to the file for validation.

        Returns:
            bool: True if the content matches the prepdir output file format, False otherwise.
        """
        try:
            from .prepdir_output_file import PrepdirOutputFile

            PrepdirOutputFile.from_content(content, Path(file_full_path) if file_full_path else None)
            return True
        except ValueError:
            return False
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise
