# Changelog

All notable changes to `prepdir` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)

## [0.13.0] - 2025-06-14

### Added
- New `run()` function in `prepdir.main` for programmatic use, allowing other Python projects to import and use `prepdir` as a library. Mirrors CLI functionality, accepting parameters for directory, extensions, output file, and more, returning formatted content as a string. Accessible via `from prepdir import run`.
- New `validate_output_file()` function in `prepdir.main` to verify the legitimacy of prepdir-generated output files (e.g., `prepped_dir.txt`). Checks for valid headers, matching `Begin File` and `End File` pairs, and correct delimiters. Accessible via `from prepdir import validate_output_file`.
- Support for environment variable `TEST_ENV` to skip default config files during testing.
- Debug logging for configuration loading steps, including attempted files and final config values (`SCRUB_UUIDS`, `REPLACEMENT_UUID`).
- Tests for `run()` respecting `SCRUB_UUIDS` and `REPLACEMENT_UUID` from `config.yaml`, CLI overrides, and general functionality (successful execution, output file writing, error handling, inclusion of prepdir-generated files).
- Tests for `validate_output_file()` covering valid files, missing footers, unmatched headers/footers, invalid headers, and malformed delimiters.
- Tests for ignoring real config files when `TEST_ENV=true` and custom config path excluding bundled config.

### Changed
- Standardized logging format to `%(asctime)s - %(name)s - %(levelname)s - %(message)s` with default level `INFO`.
- Configuration loading prioritizes local `.prepdir/config.yaml` over home `~/.prepdir/config.yaml`.
- Bundled config is now copied to a temporary file for `Dynaconf` compatibility, with cleanup afterward.
- Disabled `Dynaconf` features: `load_dotenv`, `merge_enabled`, and `environments` for simpler config behavior.
- Removed uppercase key validation (introduced in `0.10.0`) to allow flexible key casing.
- Updated `run()` to allow `scrub_uuids` and `replacement_uuid` to be `None`, falling back to config defaults.
- CLI argument descriptions for `--no-scrub-uuids` and `--replacement-uuid` clarify config fallback behavior.
- Overhauled `tests/test_config.py` for isolated environments using `clean_cwd` fixture and updated assertions.
- Updated `__version__` in `src/prepdir/__init__.py` to `"0.13.0"`.

### Fixed
- Ensured consistent handling of missing bundled config without logging errors when skipped.

## [0.12.0] - 2025-06-13

### Added
- Automatic scrubbing of UUIDs in file contents, replacing them with the nil UUID (`00000000-0000-0000-0000-000000000000`) by default. UUIDs are matched as standalone tokens (using word boundaries) to avoid false positives. Configurable via:
  - Command line: `--no-scrub-uuids` to disable, `--replacement-uuid <uuid>` for custom UUID.
  - `config.yaml`: `SCRUB_UUIDS` (boolean, default: `true`), `REPLACEMENT_UUID` (string, default: `"00000000-0000-0000-0000-000000000000"`).
- Validation for replacement UUIDs, defaulting to nil UUID if invalid.

### Changed
- Shortened file delimiter from 31 characters (`=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=`) to 15 characters (`=-=-=-=-=-=-=-=`) to reduce token usage in AI model inputs.

### Upgrade Notes
- For versions <0.12.0, add `SCRUB_UUIDS` and `REPLACEMENT_UUID` to your `config.yaml` to customize UUID scrubbing. Existing configs without these keys will use the default behavior (scrubbing enabled with nil UUID).
- UUID scrubbing now uses word boundaries, so only standalone UUIDs are replaced. File delimiters are now 15 characters long. Command line options `--no-scrub-uuids` and `--replacement-uuid` override config settings.

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)

## [0.11.0] - 2025-06-07

### Added
- Automatic exclusion of `prepdir`-generated files (e.g., `prepped_dir.txt`) by default, with new `--include-prepdir-files` option to include them.

## [0.10.1] - 2025-06-07

### Added
- Validation in `load_config` to detect lowercase configuration keys (`exclude`, `directories`, `files`) and provide guidance to update to uppercase (`EXCLUDE`, `DIRECTORIES`, `FILES`) for compatibility with version 0.10.0's Dynaconf integration.

### Fixed
- Improved user experience for upgrading users by adding clear error messages for deprecated lowercase configuration keys.

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)

## [0.10.0] - 2025-06-07

### Added
- Integrated [Dynaconf](https://dynaconf.com) for robust configuration management, supporting custom, local, global, and default config files with clear precedence. See the [Configuration section](https://github.com/eyecantell/prepdir#configuration) in the README.

### Changed
- Enhanced test suite for improved coverage and reliability across Python 3.8–3.11.
- Reorganized README with a prioritized Quick Start, added badges for PyPI downloads, and included a "What's New" section linking to this changelog.

### Fixed
- Resolved `test_load_config_bundled` failure in `tests/test_config.py` by correctly mocking the `importlib.resources.files` context manager, ensuring bundled config loading.

### Upgrade Notes
- **Configuration Locations**: If upgrading from versions <0.6.0, move `config.yaml` to `.prepdir/config.yaml` or use `--config config.yaml`. See the [FAQ](https://github.com/eyecantell/prepdir#faq).
- **Dynaconf**: Configurations now use uppercase keys (e.g., `EXCLUDE`, `DIRECTORIES`, `FILES`) to match `src/prepdir/config.yaml`. Update custom configs accordingly.
- **Dependencies**: Requires Python 3.8 or higher; older versions are unsupported.

### Acknowledgments
Thanks to the community for feedback and support. Report issues or suggest improvements on [GitHub Issues](https://github.com/eyecantell/prepdir/issues).

### Links
- [README](https://github.com/eyecantell/prepdir/blob/main/README.md)
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)
- [Dynaconf Documentation](https://dynaconf.com)