"""
prepdir - Directory traversal utility to prepare project contents for review
"""

from .main import configure_logging

from .config import (
    init_config,
    __version__,
)

from .scrub_uuids import scrub_uuids, restore_uuids, is_valid_uuid
from .prepdir_file_entry import PrepdirFileEntry
from .prepdir_output_file import PrepdirOutputFile
from .prepdir_processor import PrepdirProcessor

__all__ = [
    "__version__",
    "configure_logging",
    "init_config",
    "is_valid_uuid",
    "PrepdirFileEntry",
    "PrepdirOutputFile",
    "PrepdirProcessor",
    "restore_uuids",
    "scrub_uuids",
]
