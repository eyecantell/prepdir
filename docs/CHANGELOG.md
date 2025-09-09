# Changelog

All notable changes to `prepdir` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)

## [0.18.0] - 2025-09-08

### Added
- Added `--max-chars` CLI option and `max_chars` parameter to `run()` for splitting large outputs into multiple files (e.g., `prepped_dir_part1of3.txt`).
- Added new tests for directory traversal, specific files, exclusions, and permission errors in `test_prepdir_processor.py`.
- Added pytest configuration in `pyproject.toml` for coverage reporting and test discovery.

### Changed
- Updated `run()` to return a list of `PrepdirOutputFile` objects to support multi-part outputs.
- Updated development container to use `pdm install --dev` for installing dev dependencies.

### Fixed
- Fixed UUID scrubbing configuration not being respected when no CLI flags are provided.
- Resolved reference error in `main.py` for scrub variables.
- Corrected release dates in changelog to start from May 2025, using commit history where available and estimated dates for missing versions.

## [0.17.2] - 2025-07-19

### Added
- The `load_config()` routine is now exposed

### Fixed
- Ensured verbose logging works correctly by configuring the `prepdir` logger in `main.py`. The `-v` flag (for `INFO` level) and `-vv` flag (for `DEBUG` level) now properly display corresponding log messages.

## [0.17.1] - 2025-07-17

### Added
- Added default local path (`./.{namespace}/config.yaml`) for `init_config()` when `config_path` is `None` or empty. This allows initializing a configuration file without specifying a path, improving usability for default setups. Updated docstring and added test case to verify this behavior.

## [0.17.0] - 2025-07-17

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

## [0.15.0] - 2025-07-07

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
- Updated `run()` to return a `PrepdirOutputFile` object by default, providing structured access to content, metadata, UUID mappings, and individual file entries.
- Modified `main.py` to use `PrepdirProcessor` for CLI operations, ensuring consistency between CLI and programmatic usage.
- Enhanced `config.yaml` with new options for `USE_UNIQUE_PLACEHOLDERS` and `INCLUDE_PREPDIR_FILES`.
- Updated default exclusions in `config.yaml` to include additional common directories and files (e.g., `.vibedir`, `.applydir`).
- Improved error handling in file reading to include specific messages for binary files, encoding errors, and permission issues.
- Updated tests to use `PrepdirProcessor` and `PrepdirOutputFile`, ensuring coverage for new object-oriented features.

### Fixed
- Fixed handling of binary files by replacing content with a placeholder message instead of attempting to read as text.
- Ensured consistent UUID scrubbing across all file types, with options to disable specific scrubbing types (hyphenated or hyphenless).
- Corrected parsing logic in `PrepdirOutputFile` to handle varied delimiter formats and edge cases like empty files or mismatched headers/footers.

## [0.14.0] - 2025-06-30

### Added
- Added `validate_output()` method to `PrepdirProcessor` for validating `prepped_dir.txt` files, checking for proper structure, matching delimiters, and content integrity.
- Added `get_changed_files()` method to `PrepdirOutputFile` to compare two output files and identify added, changed, or removed files.
- Added support for unique UUID placeholders (e.g., `PREPDIR_UUID_PLACEHOLDER_1`) via `--use-unique-placeholders` CLI flag and `use_unique_placeholders` parameter in `run()`.
- Added `ignore_exclusions` parameter to `run()` and `--all` CLI flag to include all files, bypassing exclusion lists.
- Added `include_prepdir_files` parameter to `run()` and `--include-prepdir-files` CLI flag to include previously generated `prepdir` files.
- Added quiet mode (`-q` or `--quiet`) to suppress console output during processing.
- Added comprehensive tests for `PrepdirOutputFile` parsing, including edge cases like unmatched delimiters, invalid headers, and binary placeholders.
- Added tests for `get_changed_files()` to verify detection of added, changed, and removed files.

### Changed
- Updated `PrepdirOutputFile` to store files as a dictionary with absolute paths as keys for faster lookups and easier comparisons.
- Enhanced UUID scrubbing to support unique placeholders, maintaining a global mapping across all files for consistency.
- Improved logging to include details on scrubbed UUIDs and file inclusion/exclusion reasons when verbose mode is enabled.
- Updated `config.yaml` to include `USE_UNIQUE_PLACEHOLDERS` and `INCLUDE_PREPDIR_FILES` options.

### Fixed
- Fixed handling of relative paths in `PrepdirFileEntry` to ensure consistency with base directory.
- Corrected error messages for file reading failures to include specific exception details.

## [0.13.1] - 2025-06-23

### Fixed
- Fixed delimiter matching in `validate_output_file()` to be more lenient, allowing variations in dash counts while ensuring symmetry.
- Ensured proper restoration of UUIDs in `PrepdirFileEntry` using the provided mapping.

## [0.13.0] - 2025-06-16

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

## [0.11.0] - 2025-06-06

### Added
- Added automatic exclusion of `prepdir`-generated files (e.g., `prepped_dir.txt`) by default, with new `--include-prepdir-files` option to include them.

## [0.10.1] - 2025-06-01

### Added
- Added validation for uppercase configuration keys (`EXCLUDE`, `DIRECTORIES`, `FILES`) with guidance for users upgrading from older versions.

## [0.10.0] - 2025-05-27

### Changed
- Switched to `Dynaconf` for configuration management, requiring uppercase configuration keys (`EXCLUDE`, `DIRECTORIES`, `FILES`) in `config.yaml`.
- Configuration precedence: `--config` > `.prepdir/config.yaml` > `~/.prepdir/config.yaml` > bundled `src/prepdir/config.yaml`.

## [0.9.0] - 2025-05-20

### Added
- Support for `.gitignore`-style glob patterns in `config.yaml` for file and directory exclusions.

## [0.8.0] - 2025-05-12

### Added
- Added `--init` and `--force` options for initializing configuration files.

## [0.7.0] - 2025-05-12

### Added
- Verbose mode (`-v`) to log skipped files and reasons (e.g., excluded by config).
- Updated README and INSTALL documentation.

## [0.6.0] - 2025-05-11

### Added
- Added classifiers and keywords to project metadata.
- Moved default config to `.prepdir/config.yaml` from `config.yaml` for better organization.

## [0.5.0] - 2025-05-11

### Added
- Support for custom output file via `-o` or `--output` option.

## [0.4.1] - 2025-05-11

### Fixed
- Minor bug fixes and improvements (no specific details in commit message).

## [0.4.0] - 2025-05-11

### Fixed
- Fixed handling of non-text files to avoid encoding errors during traversal.

## [0.3.0] - 2025-05-11

### Added
- Support for specific file extensions via `-e` or `--extensions`.
- Added initial test suite.

## [0.2.0] - 2025-05-11

### Changed
- Improved output formatting with clearer file separators and timestamps.

## [0.1.0] - 2025-05-10

### Added
- Initial release of `prepdir` with basic directory traversal and file content output.