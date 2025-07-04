from pathlib import Path
from typing import List, Optional, Iterator, Dict
import os
import logging
import sys
import fnmatch
import re
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout
from dynaconf import Dynaconf
from prepdir.config import load_config, __version__, init_config
from prepdir.prepdir_file_entry import PrepdirFileEntry
from prepdir.prepdir_output_file import PrepdirOutputFile
from prepdir.scrub_uuids import HYPHENATED_UUID_PATTERN
from prepdir.is_excluded_file import is_excluded_dir, is_excluded_file

logger = logging.getLogger(__name__)

class PrepdirProcessor:
    """Manages generation and parsing of prepdir output files.

    Constructor parameters take precedence over configuration settings loaded from config files.
    """

    def __init__(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        specific_files: Optional[List[str]] = None,
        output_file: Optional[str] = None,
        config_path: Optional[str] = None,
        scrub_hyphenated_uuids: Optional[bool] = None,
        scrub_hyphenless_uuids: Optional[bool] = None,
        replacement_uuid: Optional[str] = None,
        use_unique_placeholders: bool = False,
        ignore_exclusions: bool = False,
        include_prepdir_files: bool = False,
        verbose: bool = False,
    ):
        """Initialize PrepdirProcessor with configuration and parameters.

        Args:
            directory: Starting directory path.
            extensions: List of file extensions to include (without dot).
            specific_files: List of specific file paths to process.
            output_file: Path to save the output file; defaults to config's DEFAULT_OUTPUT_FILE ("prepped_dir.txt").
            config_path: Path to custom config file.
            scrub_hyphenated_uuids: If True, scrub hyphenated UUIDs; if None, use config.
            scrub_hyphenless_uuids: If True, scrub hyphen-less UUIDs; if None, use config.
            replacement_uuid: UUID to replace detected UUIDs; if None, use config.
            use_unique_placeholders: If True, use unique placeholders; defaults to config or False.
            ignore_exclusions: If True, ignore exclusion lists; defaults to config or False.
            include_prepdir_files: If True, include prepdir-generated files; defaults to config or False.
            verbose: If True, enable verbose logging; defaults to config or False.
        """
        self.directory = os.path.abspath(directory)
        if not os.path.exists(self.directory):
            raise ValueError(f"Directory '{self.directory}' does not exist")
        if not os.path.isdir(self.directory):
            raise ValueError(f"'{self.directory}' is not a directory")

        self.config = self._load_config(config_path)
        self.extensions = extensions or self.config.get("DEFAULT_EXTENSIONS", [])
        self.specific_files = specific_files or []
        self.output_file = output_file or self.config.get("DEFAULT_OUTPUT_FILE", "prepped_dir.txt")
        self.ignore_exclusions = ignore_exclusions or self.config.get("IGNORE_EXCLUSIONS", False)
        self.include_prepdir_files = include_prepdir_files or self.config.get("INCLUDE_PREPDIR_FILES", False)
        self.verbose = verbose or self.config.get("VERBOSE", False)

        self.scrub_hyphenated_uuids = (
            scrub_hyphenated_uuids
            if scrub_hyphenated_uuids is not None
            else self.config.get("SCRUB_HYPHENATED_UUIDS", True)
        )
        self.scrub_hyphenless_uuids = (
            scrub_hyphenless_uuids
            if scrub_hyphenless_uuids is not None
            else self.config.get("SCRUB_HYPHENLESS_UUIDS", True)
        )
        if replacement_uuid is not None and not re.fullmatch(HYPHENATED_UUID_PATTERN, replacement_uuid):
            logger.error(f"Invalid replacement UUID: '{replacement_uuid}'. Using config default.")
            replacement_uuid = None
        self.replacement_uuid = (
            replacement_uuid
            if replacement_uuid is not None
            else self.config.get("REPLACEMENT_UUID", "00000000-0000-0000-0000-000000000000")
        )
        self.use_unique_placeholders = use_unique_placeholders or self.config.get("USE_UNIQUE_PLACEHOLDERS", False)

        self.logger = logging.getLogger(__name__)
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)

    def _load_config(self, config_path: Optional[str]) -> Dynaconf:
        """Load configuration with precedence handling."""
        return load_config("prepdir", config_path)
    
    def is_excluded_output_file(self, filename: str, root: str) -> bool:
        '''Check if this file is of prepdir out file format and should be excluded'''
        
        full_path = os.path.abspath(os.path.join(root, filename))

        # Always ignore the output file being used for this run
        if self.output_file and full_path == os.path.abspath(self.output_file):
            logger.debug(f"File {full_path} is excluded since it is the output file for this run")
            return True

        if self.include_prepdir_files:
            #logger.debug(f"include_prepdir_files is True {self.include_prepdir_files} - output files will not be excluded")
            return False
    
        try: 
            #logger.debug(f"Checking {full_path} to see if it is an output file")
            with open(full_path, "r", encoding="utf-8") as f:
                if PrepdirFileEntry.is_prepdir_outputfile_format(f.read()):
                    logger.debug(f"Found {full_path} is an output file")
                    return True
        except (IOError, UnicodeDecodeError):
            logger.debug(f"Could not read {full_path} - assuming it is NOT an output file")
            return False  # Ignore errors and assume not prepdir-generated if unreadable
        
        #logger.debug(f"Found {full_path} is NOT an output file")
        return False

    def is_excluded_dir(self, dirname: str, root: str) -> bool:
        """Check if directory or any of its parent directories should be excluded from traversal using glob patterns.

        Args:
            dirname: Directory name to check.
            root: Root path of the directory.

        Returns:
            bool: True if the directory or any parent directory should be excluded.
        """
        if self.ignore_exclusions:
            return False

        excluded_dir_patterns = self.config.get("EXCLUDE", {}).get("DIRECTORIES", [])

        return is_excluded_dir(dirname, root, self.directory, excluded_dir_patterns)
        

    def is_excluded_file(self, filename: str, root: str) -> bool:
        """Check if file should be excluded from traversal using glob patterns, if it's the output file, or if it's prepdir-generated.

        Args:
            filename: File name to check.
            root: Root path of the file.

        Returns:
            bool: True if the file should be excluded.
        """

        if self.ignore_exclusions:
            return False

        excluded_dir_patterns = self.config.get("EXCLUDE", {}).get("DIRECTORIES", [])
        excluded_file_patterns = self.config.get("EXCLUDE", {}).get("FILES", [])

        return is_excluded_file(filename, root, self.directory, excluded_dir_patterns, excluded_file_patterns)


    def generate_output(self) -> PrepdirOutputFile:
        """Generate a prepdir output file as a PrepdirOutputFile object."""
        output = StringIO()
        uuid_mapping: Dict[str, str] = {}
        placeholder_counter = 1
        timestamp_to_use = datetime.now().isoformat()
        metadata = {
            "version": __version__,
            "date": timestamp_to_use,
            "base_directory": self.directory,
            "creator": f"prepdir version {__version__} (pip install prepdir)",
        }

        with redirect_stdout(output):
            files_found = False

            print(f"File listing generated {timestamp_to_use} by prepdir version {__version__} (pip install prepdir)")
            print(f"Base directory is '{self.directory}'")
            if self.scrub_hyphenated_uuids:
                if self.use_unique_placeholders:
                    print(
                        "Note: Valid (hyphenated) UUIDs in file contents will be scrubbed and replaced with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n)."
                    )
                else:
                    print(
                        f"Note: Valid (hyphenated) UUIDs in file contents will be scrubbed and replaced with '{self.replacement_uuid}'."
                    )
            if self.scrub_hyphenless_uuids:
                if self.use_unique_placeholders:
                    print(
                        "Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with unique placeholders (e.g., PREPDIR_UUID_PLACEHOLDER_n)."
                    )
                else:
                    print(
                        f"Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with '{self.replacement_uuid.replace('-', '')}'."
                    )

            file_iterator = (
                self._traverse_specific_files()
                if self.specific_files
                else self._traverse_directory()
            )

            for file_path in file_iterator:
                files_found = True
                logger.debug(f"adding file {file_path}")
                file_entry, updated_uuid_mapping, placeholder_counter = PrepdirFileEntry.from_file_path(
                    file_path=file_path,
                    base_directory=self.directory,
                    scrub_hyphenated_uuids=self.scrub_hyphenated_uuids,
                    scrub_hyphenless_uuids=self.scrub_hyphenless_uuids,
                    replacement_uuid=self.replacement_uuid,
                    use_unique_placeholders=self.use_unique_placeholders,
                    verbose=self.verbose,
                    placeholder_counter=placeholder_counter,
                    uuid_mapping=uuid_mapping,
                )
                print(file_entry.to_output())
                uuid_mapping.update(updated_uuid_mapping)

            if not files_found:
                if self.specific_files:
                    print("No valid or accessible files found from the provided list.")
                elif self.extensions:
                    print(f"No files with extension(s) {', '.join(self.extensions)} found.")
                else:
                    print("No files found.")
                
                raise ValueError("No files found!")

        content = output.getvalue()

        return PrepdirOutputFile.from_content(
            content=content,
            path_obj=Path(self.output_file) if self.output_file else None,
            uuid_mapping=uuid_mapping,
            metadata=metadata,
            use_unique_placeholders=self.use_unique_placeholders,
        )

    def _traverse_specific_files(self) -> Iterator[Path]:
        """Yield specific files, respecting exclusions and validating existence."""
        for file_path in self.specific_files:
            path = Path(file_path)
            if not path.is_absolute():
                path = Path(self.directory) / path
            path = path.resolve()

            if not path.exists():
                self.logger.warning(f"File '{file_path}' does not exist")
                continue
            if not path.is_file():
                self.logger.warning(f"'{file_path}' is not a file")
                continue
            if not self.ignore_exclusions:
                if self.is_excluded_dir(path.parent.name, str(path.parent)):
                    self.logger.info(f"Skipping file '{file_path}' (parent directory excluded)")
                    continue
                if self.is_excluded_file(path.name, str(path.parent)):
                    self.logger.info(f"Skipping file '{file_path}' (excluded in config)")
                    continue
            
            if self.is_excluded_output_file(path.name, str(path.parent)):
                self.logger.info(f"Skipping file: {file_path} (excluded prepdir output file)")
                continue
            yield path

    def _traverse_directory(self) -> Iterator[Path]:
        """Traverse directory, yielding files that match extensions and are not excluded.

        Yields:
            Path: Paths to files that pass the extension and exclusion filters.
        """
        logger.debug(f"traversing {self.directory}")
        for root, dirnames, filenames in sorted(os.walk(self.directory)):

            dirnames[:] = [d for d in dirnames if not self.is_excluded_dir(d, root)]

            for filename in sorted(filenames):
                if self.extensions and not any(filename.endswith(f".{ext}") for ext in self.extensions):
                    self.logger.info(f"Skipping file: {filename} (extension not in {self.extensions})")
                    continue
                if self.is_excluded_output_file(filename, root):
                    self.logger.info(f"Skipping file: {filename} (excluded output file)")
                    continue
                if self.is_excluded_file(filename, root):
                    self.logger.info(f"Skipping file: {filename} (excluded in config)")
                    continue
                yield Path(root) / filename

    def save_output(self, output: PrepdirOutputFile, path: Optional[str] = None) -> None:
        """Save the PrepdirOutputFile content to the specified path."""
        output.save(path)

    def validate_output(
        self,
        content: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        highest_base_directory: Optional[str] = None,
        validate_files_exist: bool = False,
    ) -> PrepdirOutputFile:
        """Validate and parse a prepdir-formatted output (from content or file) into a PrepdirOutputFile.

        Args:
            content: The prepdir-formatted content to parse (e.g., LLM output). Mutually exclusive with file_path.
            file_path: Path to a prepdir-formatted file to parse. Mutually exclusive with content.
            metadata: Optional metadata to override defaults (e.g., base_directory, creator).
            highest_base_directory: Directory above which file paths must not resolve. Defaults to self.directory.
            validate_files_exist: If True, check if parsed files exist in the filesystem.

        Returns:
            PrepdirOutputFile: Parsed output with PrepdirFileEntry objects and metadata.

        Raises:
            ValueError: If input is invalid, paths escape highest_base_directory, or parsing fails.
        """
        if content is not None and file_path is not None:
            raise ValueError("Cannot provide both content and file_path")
        if content is None and file_path is None:
            raise ValueError("Must provide either content or file_path")

        default_metadata = {
            "base_directory": self.directory,
            "version": __version__,
            "date": datetime.now().isoformat(),
            "creator": f"prepdir version {__version__}",
        }
        if metadata:
            default_metadata.update(metadata)

        highest_base = Path(highest_base_directory or self.directory).resolve()

        try:
            if file_path:
                output = PrepdirOutputFile.from_file(
                    path=Path(file_path),
                    metadata=default_metadata,
                    use_unique_placeholders=self.use_unique_placeholders,
                )
            else:
                output = PrepdirOutputFile.from_content(
                    content=content,
                    path_obj=None,
                    metadata=default_metadata,
                    use_unique_placeholders=self.use_unique_placeholders,
                )

            # Verify base_directory is valid and within highest_base_directory
            base_dir = Path(output.metadata["base_directory"]).resolve()
            try:
                base_dir.relative_to(highest_base)
            except ValueError:
                raise ValueError(f"Base directory '{base_dir}' is outside highest base directory '{highest_base}'")

            # Verify all file paths are within highest_base_directory
            for entry in output.files.values():
                abs_path = entry.absolute_path.resolve()
                try:
                    abs_path.relative_to(highest_base)
                except ValueError:
                    raise ValueError(f"File path '{abs_path}' is outside highest base directory '{highest_base}'")
                if validate_files_exist and not abs_path.exists():
                    logger.warning(f"File {abs_path} does not exist in filesystem")

            return output
        except ValueError as e:
            raise ValueError(f"Invalid prepdir output: {str(e)}") from e

    @staticmethod
    def init_config(config_path: str = ".prepdir/config.yaml", force: bool = False) -> None:
        """Initialize a local configuration file."""
        init_config("prepdir", config_path, force, stdout=sys.stdout, stderr=sys.stderr)