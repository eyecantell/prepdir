# Changelog

All notable changes to `prepdir` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)

## [Unreleased]

### Added
- Added `glob_translate.py` module to convert glob patterns to regex patterns, supporting recursive `**` patterns, hidden files, and custom separators, adapted from Python 3.14's `glob.translate()`.
- Added `profile_prepdir.py` script for profiling `prepdir` performance using `cProfile`, outputting results for the top 20 functions by cumulative time.
- Added comprehensive tests for `glob_translate()` in `test_glob_translate.py`, covering basic patterns, character classes, `**` patterns, cross-platform separators, edge cases, non-recursive mode, hidden files, and consecutive `**` patterns.
- Added support for precompiled regexes in `is_excluded_dir()` and `is_excluded_file()` to improve performance by compiling glob patterns once during `PrepdirProcessor` initialization.
- Added logging for file inclusion/exclusion counts in `_traverse_directory()` to track the number of files checked and included.
- Added `Path` object support in `is_excluded_file()` and `is_excluded_dir()` with conversion to string and appropriate type checking.

### Changed
- Improved `_traverse_directory()` to skip excluded directories early, preventing unnecessary recursion, and to log file counts, significantly improving performance for large directories.
- Updated `.devcontainer/Dockerfile` to use `python:3.13-slim` as the base image, upgrading from `python:3.9-slim`.
- Changed `.devcontainer/devcontainer.json` to use `pdm install` instead of `pip install -e .` for dependency installation.
- Refactored `is_excluded_file.py` to use `glob_translate()` for glob-to-regex conversion, removing custom `glob_to_regex()` function for improved accuracy and maintainability.
- Modified `PrepdirProcessor` to compile glob patterns into regexes during initialization, storing them as `excluded_dir_regexes`, `excluded_file_regexes`, and `excluded_file_recursive_glob_regexes` for efficient reuse.
- Updated `is_excluded_dir()` and `is_excluded_file()` to accept precompiled regexes and full paths, simplifying path handling and removing `base_directory` parameter.
- Enhanced logging in `test_prepdir_processor.py` and `test_is_excluded_file.py` to use `DEBUG` level for detailed output during testing.

### Fixed
- Fixed handling of consecutive `**` patterns in `glob_translate()` to collapse them correctly, ensuring accurate regex generation.

## [0.16.0] - 2025-07-14
### Changed
- Deprecated support for python 3.8

## [0.15.0] - 2025-07-14

### Added
- Introduced object-oriented architecture with new classes `PrepdirProcessor`, `PrepdirFileEntry`, and `PrepdirOutputFile` to encapsulate file traversal, content processing, and output generation/parsing.
- Added `PrepdirFileEntry` class to represent individual file metadata, content, and UUID mappings, supporting serialization with Pydantic and methods like `to_output()` and `restore_uuids()`.
- Added `PrepdirOutputFile` class to encapsulate the `prepped_dir.txt` file, including content, metadata, and a list of `PrepdirFileEntry` objects, with methods for saving, parsing, and serialization.
- Integrated Pydantic for serialization of `PrepdirFileEntry` and `PrepdirOutputFile`, enabling JSON-compatible output, type safety, and validation for debugging, inter-process communication, and caching.
- Added support for `applydir` integration, allowing `PrepdirOutputFile` to be passed to `applydir` for applying LLM-generated changes to the filesystem.
- Added `vibedir` integration, enabling `prepdir` to generate `prepped_dir.txt` for LLM processing and parse modified outputs for `applydir`.
- Added new design decision documents (`docs/prepdir_design_decisions_20250621.md` and `docs/prepdir_design_decisions_20250628.md`) detailing the object-oriented architecture and integration with `applydir` and `vibedir`.
- Added comprehensive tests for UUID scrubbing in `test_core.py`, covering unique placeholders, fixed UUID replacements, no scrubbing, reused mappings, logging, and edge cases like empty content, malformed UUIDs, and case sensitivity.
- Added `return_raw` option in `run()` to maintain backward compatibility, returning a tuple `(content, uuid_mapping, files_list, metadata)` for existing users.
- Added `.ruff_cache` to default excluded directories in `.prepdir/config.yaml`.
- Added `pydantic>=2.5.0` as a dependency for serialization support.

### Changed
- Refactored `PrepdirProcessor` to use `PrepdirFileEntry` and `PrepdirOutputFile`, streamlining output generation and parsing logic for better maintainability and interoperability.
- Updated `run()` to return `PrepdirOutputFile` by default, with `return_raw=True` for legacy tuple output, ensuring backward compatibility.
- Renamed `PrepdirFile` to `SinglePrepdirFile`, then to `PrepdirFileEntry` for clarity and to reflect its role as an entry in `PrepdirOutputFile`.
- Updated `.prepdir/config.yaml` to remove `LOAD_DOTENV` and `MERGE_LISTS`, and renamed `SCRUB_UUIDS` to `SCRUB_HYPHENATED_UUIDS` for consistency.
- Reordered dependencies in `.devcontainer/Dockerfile` for clarity and added `pydantic` to the list of installed development tools.
- Overhauled `README.md` to simplify content, improve clarity, and reflect new object-oriented features and integrations.
- Updated `__version__` to 0.15.0 in `src/prepdir/__init__.py` and `pyproject.toml`.
- Enhanced `validate_output_file()` to return `PrepdirOutputFile` instead of a dictionary, aligning with the new object-oriented structure.
- Improved UUID scrubbing to support consistent placeholder reuse across multiple calls with a shared `uuid_mapping`.

### Removed
- Deleted `tests/test_validate_output_file.py` as validation logic is now integrated into `PrepdirProcessor` and tested within `test_core.py`.
- Removed `SCRUB_UUIDS` configuration key in favor of `SCRUB_HYPHENATED_UUIDS` for clearer naming.

### Fixed
- Ensured consistent UUID mapping across multiple calls by reusing `uuid_mapping` in `scrub_uuids()`, preventing duplicate placeholders for the same UUID.
- Fixed validation of malformed delimiters and headers/footers to handle edge cases more robustly.
- Corrected handling of case-sensitive UUIDs to treat them as distinct in `scrub_uuids()`.

## [0.14.1] - 2025-06-20

### Fixed
- Corrected REAMDE.md and CHANGELOG.md 

## [0.14.0] - 2025-06-20

### Added
- Support for unique UUID placeholders in UUID scrubbing via `use_unique_placeholders` parameter in `run()`, `traverse_directory()`, `display_file_content()`, and `scrub_uuids()`. When enabled, UUIDs are replaced with unique placeholders (e.g., `PREPDIR_UUID_PLACEHOLDER_1`) instead of a single `replacement_uuid`. Returns a dictionary mapping placeholders to original UUIDs.
- New `validate_output_file.py` module to handle validation of `prepdir`-generated or LLM-edited output files, moved from `core.py` for better modularity.
- Lenient delimiter parsing in `validate_output_file()` using `LENIENT_DELIM_PATTERN` (`[-=]{3,}`), allowing headers/footers with varying lengths and combinations of `-` or `=` characters, plus flexible whitespace and case-insensitive keywords.
- Validation of file paths in `validate_output_file()`, flagging absolute paths, paths with `..`, or those with unusual characters as warnings.
- Tracking of file creation metadata (date, creator, version) in `validate_output_file()`, stored in the `creation` dictionary of the result.
- Tests for unique UUID placeholder functionality in `test_core.py`, covering single/multiple files, no UUIDs, and non-placeholder modes.
- Comprehensive tests for `validate_output_file()` in `test_validate_output_file.py`, covering empty files, valid/invalid structures, lenient delimiters, large files, and edge cases like malformed timestamps or missing headers.

### Changed
- Updated `__version__` to 0.14.0 in `src/prepdir/__init__.py` and `pyproject.toml`.
- Moved `validate_output_file()` from `core.py` to `validate_output_file.py` and updated imports in `__init__.py`.
- Enhanced `validate_output_file()` to return a dictionary with `files` (mapping file paths to contents), `creation` (header metadata), `errors`, `warnings`, and `is_valid`. Previously, it only returned `is_valid`, `errors`, and `warnings`.
- Modified `scrub_uuids()` to return a tuple of `(content, replaced, uuid_mapping, placeholder_counter)` to support unique placeholders.
- Updated `traverse_directory()` to return a `uuid_mapping` dictionary and accept `use_unique_placeholders`.
- Updated `display_file_content()` to return a tuple of `(uuids_scrubbed, uuid_mapping, placeholder_counter)` and accept `use_unique_placeholders`.
- Updated `run()` to return a tuple of `(content, uuid_mapping)` and accept `use_unique_placeholders`.
- Improved regex patterns in `core.py` for headers/footers to support lenient delimiters and case-insensitive matching.
- Standardized string quoting in `config.py` and `main.py` for consistency (e.g., double quotes).
- Sorted files in `traverse_directory()` for deterministic processing.
- Updated `GENERATED_HEADER_PATTERN` in `core.py` to handle more flexible header formats, including missing version or pip install text.
- Minor formatting and whitespace improvements in `config.py`, `core.py`, `main.py`, and test files for consistency.

### Fixed
- Fixed test cases in `test_core.py` to account for new return values from `run()`, `scrub_uuids()`, and `display_file_content()`.
- Ensured proper handling of blank lines and whitespace in `validate_output_file()` to preserve file content accurately.
- Corrected delimiter handling in `validate_output_file()` to avoid false negatives with varied delimiter lengths or extra whitespace.

## [0.13.0] - 2025-06-14

### Added
- New `run()` function in `prepdir.main` for programmatic use, enabling `prepdir` to be imported as a library (`from prepdir import run`). Mirrors CLI functionality, accepting parameters for directory, extensions, output file, UUID scrubbing, and more, returning formatted content as a string.
- New `validate_output_file()` function in `prepdir.main` to verify the structure of `prepdir`-generated files (e.g., `prepped_dir.txt`). Checks for valid headers, matching `Begin File` and `End File` delimiters, and correct formatting (`from prepdir import validate_output_file`).
- Support for `TEST_ENV=true` environment variable to skip default config files (local and global) during testing, ensuring isolated test environments.
- Debug logging for configuration loading, detailing attempted config files and final values for `SCRUB_UUIDS` and `REPLACEMENT_UUID`.
- Comprehensive tests for `run()`, covering configuration traversal, UUID scrubbing, output file writing, error handling, and inclusion of `prepdir`-generated files.
- Tests for `validate_output_file()`, validating correct files, missing footers, unmatched headers/footers, invalid headers, and malformed delimiters.
- Tests for configuration loading with `TEST_ENV=true` and custom config paths, ensuring bundled config exclusion when appropriate.
- Support for scrubbing hyphen-less UUIDs via `SCRUB_HYPHENLESS_UUIDS` in `config.yaml` and `--no-scrub-hyphenless-uuids` CLI flag.

### Changed
- Standardized logging format to `%(asctime)s - %(name)s - %(levelname)s - %(message)s` with default level `INFO`, configurable via `LOGLEVEL` environment variable (e.g., `LOGLEVEL=DEBUG`).
- Reordered configuration loading precedence: custom config (`--config` or `config_path`) > local `.prepdir/config.yaml` > global `~/.prepdir/config.yaml` > bundled `src/prepdir/config.yaml`.
- Bundled config is now copied to a temporary file for `Dynaconf` compatibility, with automatic cleanup after loading.
- Disabled `Dynaconf` features (`load_dotenv`, `merge_enabled`, `environments`) for simpler configuration behavior.
- Removed uppercase key validation (introduced in 0.10.0), allowing flexible key casing in `config.yaml`.
- Updated `run()` to allow `scrub_uuids` and `replacement_uuid` parameters to be `None`, falling back to `config.yaml` defaults.
- CLI arguments `--no-scrub-uuids` and `--replacement-uuid` now explicitly override `config.yaml` settings, with config values as defaults if unspecified.
- Overhauled `tests/test_config.py` to use `clean_cwd` fixture for isolated environments and updated assertions for robustness.
- Updated `__version__` to 0.13.0 in `src/prepdir/__init__.py`.
- Added `.prepdir/config.yaml` and `~/.prepdir/config.yaml` to default excluded files in bundled `config.yaml`.

### Fixed
- Ensured consistent handling of missing bundled config without logging errors when skipped (e.g., with `TEST_ENV=true` or custom config).
- Fixed `LOGLEVEL` environment variable not applying debug logging by explicitly configuring logging in `main.py`.

## [0.12.0] - 2025-06-13

### Added
- Added automatic scrubbing of UUIDs in file contents, replacing them with the nil UUID (`00000000-0000-0000-0000-000000000000`) by default. UUIDs are matched as standalone tokens (using word boundaries) to avoid false positives. Use `--no-scrub-uuids` to disable or `--replacement-uuid` to specify a custom UUID. Configure via `SCRUB_UUIDS` and `REPLACEMENT_UUID` in `config.yaml`.
- Shortened file delimiter from 31 to 15 characters to reduce token usage in AI model inputs.

## [0.11.0] - 2025-06-01

### Added
- Added automatic exclusion of `prepdir`-generated files (e.g., `prepped_dir.txt`) by default, with new `--include-prepdir-files` option to include them.

## [0.10.1] - 2025-05-20

### Added
- Added validation for uppercase configuration keys (`EXCLUDE`, `DIRECTORIES`, `FILES`) with guidance for users upgrading from older versions.

## [0.10.0] - 2025-05-15

### Changed
- Switched to `Dynaconf` for configuration management, requiring uppercase configuration keys (`EXCLUDE`, `DIRECTORIES`, `FILES`) in `config.yaml`.
- Configuration precedence: `--config` > `.prepdir/config.yaml` > `~/.prepdir/config.yaml` > bundled `src/prepdir/config.yaml`.

## [0.9.0] - 2025-04-10

### Added
- Support for `.gitignore`-style glob patterns in `config.yaml` for file and directory exclusions.

## [0.8.0] - 2025-03-05

### Changed
- Improved performance for large directories by optimizing file traversal logic.

## [0.7.0] - 2025-02-01

### Added
- Verbose mode (`-v`) to log skipped files and reasons (e.g., excluded by config).

## [0.6.0] - 2025-01-10

### Changed
- Moved default config to `.prepdir/config.yaml` from `config.yaml` for better organization.

## [0.5.0] - 2024-12-15

### Added
- Support for custom output file via `-o` or `--output` option.

## [0.4.0] - 2024-11-20

### Fixed
- Fixed handling of non-text files to avoid encoding errors during traversal.

## [0.3.0] - 2024-10-05

### Added
- Support for specific file extensions via `-e` or `--extensions`.

## [0.2.0] - 2024-09-01

### Changed
- Improved output formatting with clearer file separators and timestamps.

## [0.1.0] - 2024-08-01

### Added
- Initial release of `prepdir` with basic directory traversal and file content output.