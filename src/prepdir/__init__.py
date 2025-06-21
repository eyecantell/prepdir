"""
prepdir - Directory traversal utility to prepare project contents for review
"""

from .main import configure_logging

from .core import (
    run,
    init_config,
    traverse_directory,
    display_file_content,
    is_valid_uuid,
    scrub_uuids,
    is_prepdir_generated,
    is_excluded_dir,
    is_excluded_file,
    __version__,
)

from .validate_output_file import validate_output_file

__all__ = [
    "__version__",
    "configure_logging",
    "display_file_content",
    "init_config",
    "is_excluded_dir",
    "is_excluded_file",
    "is_prepdir_generated",
    "is_valid_uuid",
    "run",
    "scrub_uuids",
    "traverse_directory",
    "validate_output_file",
]
