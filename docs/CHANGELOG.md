Changelog
All notable changes to prepdir are documented in this file.
The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.
[0.12.0] - 2025-06-12
Added

Automatic scrubbing of UUIDs in file contents, replacing them with the nil UUID (00000000-0000-0000-0000-000000000000) by default. UUIDs are matched as standalone tokens (using word boundaries) to avoid false positives. Configurable via:
Command line: --no-scrub-uuids to disable, --replacement-uuid <uuid> for custom UUID.
config.yaml: SCRUB_UUIDS (boolean, default: true), REPLACEMENT_UUID (string, default: "00000000-0000-0000-0000-000000000000").


Validation for replacement UUIDs, defaulting to nil UUID if invalid.

Upgrade Notes

For versions <0.12.0, add SCRUB_UUIDS and REPLACEMENT_UUID to your config.yaml to customize UUID scrubbing. Existing configs without these keys will use the default behavior (scrubbing enabled with nil UUID).
UUID scrubbing now uses word boundaries, so only standalone UUIDs are replaced. Command line options --no-scrub-uuids and --replacement-uuid override config settings.

Links

README
GitHub Repository
PyPI
Dynaconf Documentation

[0.11.0] - 2025-06-07
Added

Automatic exclusion of prepdir-generated files (e.g., prepped_dir.txt) by default, with new --include-prepdir-files option to include them.

[0.10.1] - 2025-06-07
Added

Validation in load_config to detect lowercase configuration keys (exclude, directories, files) and provide guidance to update to uppercase (EXCLUDE, DIRECTORIES, FILES) for compatibility with version 0.10.0's Dynaconf integration.

Fixed

Improved user experience for upgrading users by adding clear error messages for deprecated lowercase configuration keys.

Links

README
GitHub Repository
PyPI
Dynaconf Documentation

[0.10.0] - 2025-06-07
Added

Integrated Dynaconf for robust configuration management, supporting custom, local, global, and default config files with clear precedence. See the Configuration section in the README.

Changed

Enhanced test suite for improved coverage and reliability across Python 3.8–3.11.
Reorganized README with a prioritized Quick Start, added badges for PyPI downloads, and included a "What's New" section linking to this changelog.

Fixed

Resolved test_load_config_bundled failure in tests/test_config.py by correctly mocking the importlib.resources.files context manager, ensuring bundled config loading.

Upgrade Notes

Configuration Locations: If upgrading from versions <0.6.0, move config.yaml to .prepdir/config.yaml or use --config config.yaml. See the FAQ.
Dynaconf: Configurations now use uppercase keys (e.g., EXCLUDE, DIRECTORIES, FILES) to match src/prepdir/config.yaml. Update custom configs accordingly.
Dependencies: Requires Python 3.8 or higher; older versions are unsupported.

Acknowledgments
Thanks to the community for feedback and support. Report issues or suggest improvements on GitHub Issues.
Links

README
GitHub Repository
PyPI
Dynaconf Documentation

