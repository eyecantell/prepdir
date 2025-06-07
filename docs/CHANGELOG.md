# Changelog

All notable changes to `prepdir` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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