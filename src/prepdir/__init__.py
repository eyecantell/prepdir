"""
prepdir - Directory traversal utility to prepare project contents for review
"""

from .main import configure_logging

from .config import (
    init_config,
    __version__,
)

from .validate_output_file import validate_output_file
from .scrub_uuids import scrub_uuids, restore_uuids, is_valid_uuid
from .prepdir_file_entry import PrepdirFileEntry
from .prepdir_output_file import PrepdirOutputFile

__all__ = [
    "__version__",
    "configure_logging",
    "display_file_content",
    "init_config",
    "is_excluded_dir",
    "is_excluded_file",
    "is_valid_uuid",
    "PrepdirFileEntry",
    "PrepdirOutputFile",
    "restore_uuids",
    "run",
    "scrub_uuids",
    "traverse_directory",
    "validate_output_file",
]
