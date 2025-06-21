# Changelog

All notable changes to `prepdir` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)

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

## [0.11.0]
- Added automatic exclusion of `prepdir`-generated files (e.g., `prepped_dir.txt`) by default, with new `--include-prepdir-files` option to include them.

See [CHANGELOG.md](docs/CHANGELOG.md) for the complete version history.