"""
prepdir - Directory traversal utility to prepare project contents for review
"""

from .config import (
    init_config,
    __version__,
)

from .scrub_uuids import scrub_uuids, restore_uuids, is_valid_uuid
from .prepdir_file_entry import PrepdirFileEntry, BINARY_CONTENT_PLACEHOLDER, PREPDIR_DASHES
from .prepdir_output_file import PrepdirOutputFile
from .prepdir_processor import PrepdirProcessor
from .is_excluded_file import is_excluded_dir
from .prepdir_logging import configure_logging

__all__ = [
    "__version__",
    "BINARY_CONTENT_PLACEHOLDER",
    "PREPDIR_DASHES",
    "configure_logging",
    "init_config",
    "is_excluded_dir",
    "is_valid_uuid",
    "PrepdirFileEntry",
    "PrepdirOutputFile",
    "PrepdirProcessor",
    "restore_uuids",
    "scrub_uuids",
]
