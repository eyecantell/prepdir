# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://pepy.tech/badge/prepdir)](https://pepy.tech/project/prepdir)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`prepdir` is a light weight directory traversal utility designed to prepare project contents for review, particularly for sharing with AI assistants for code analysis and improvement suggestions. 

**Get Started**: [Quick Start](#-quick-start)

## Features

- Traverse directories and output file contents with clear delimiters.
- Filter files by extensions (e.g., `py`, `txt`).
- Exclude directories and files using glob patterns in `config.yaml`.
- Scrub UUIDs in file contents, replacing them with a specified UUID or unique placeholders (e.g., `PREPDIR_UUID_PLACEHOLDER_1`).
- Validate `prepdir`-generated or LLM-edited output files with lenient delimiter parsing.
- Programmatic usage via `from prepdir import run` for integration into scripts.
- Configurable via local (`.prepdir/config.yaml`), global (`~/.prepdir/config.yaml`), or custom configuration files.
- Supports `TEST_ENV=true` for isolated testing environments.

## Contents
```
prepdir -e py md -o ai_review.txt
```

- [What's New](#-whats-new)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Configuration](#-configuration)
- [Logging](#-logging)
- [Why Use prepdir?](#-why-use-prepdir)
- [Common Use Cases](#-common-use-cases)
- [Advanced Options](#-advanced-options)
- [Development](#-development)
- [FAQ](#-faq)

## 📰 What's New

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

See [CHANGELOG.md](docs/CHANGELOG.md) for the complete version history.

## 🚀 Quick Start

Get up and running with `prepdir` in minutes:

### CLI Usage
```bash
# Install prepdir
pip install prepdir

# Navigate to your project
cd /path/to/your/project

# Generate prepped_dir.txt with all project files (UUIDs scrubbed per config)
prepdir

# Share prepped_dir.txt with an AI assistant
```

### Programmatic Usage
```python
from prepdir import run

# Generate content for Python files
content, _ = run(directory="/path/to/project", extensions=["py"])
print(content)  # Use the content directly
```

```python
from prepdir import run

# Enable unique UUID placeholders (new in 0.14.0, requires programmatic use for mapping access):
content, uuid_mapping = run(directory="/path/to/project", use_unique_placeholders=True)
print("UUID Mapping:", uuid_mapping)
```

## 📦 Installation

### **Using pip (Recommended)**
```bash
pip install prepdir
```

### **From GitHub**
```bash
pip install git+https://github.com/eyecantell/prepdir.git
```

### **From Source**
```bash
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pip install -e .
```

## 💡 Usage Examples

### **CLI Usage**
```bash
# Output all files to prepped_dir.txt (UUIDs scrubbed per config)
prepdir

# Include only Python files
prepdir -e py

# Save output to a custom file
prepdir -o my_project.txt

# Include prepdir-generated files
prepdir --include-prepdir-files -o project_with_outputs.txt

# Disable UUID scrubbing (overrides config)
prepdir --no-scrub-uuids -o unscrubbed.txt

# Disable hyphen-less UUID scrubbing (overrides config)
prepdir --no-scrub-hyphenless-uuids -o no_hyphenless_scrub.txt

# Use a custom replacement UUID (overrides config)
prepdir --replacement-uuid 123e4567-e89b-12d3-a456-426614174000 -o custom_uuid.txt

# Process a specific directory
prepdir /path/to/directory
```

### **Programmatic Usage**
Use `prepdir` as a library in another Python project:
```python
from prepdir import run, validate_output_file

# Basic usage: process Python and Markdown files
content = run(
    directory="/path/to/project",
    extensions=["py", "md"],
    verbose=True
)
print(content)

# Save to a file with custom UUID scrubbing
content = run(
    directory="/path/to/project",
    extensions=["py"],
    output_file="project_review.txt",
    scrub_uuids=False,
    scrub_hyphenless_uuids=False
)

# Include all files, ignoring exclusions
content = run(
    directory="/path/to/project",
    include_all=True,
    include_prepdir_files=True,
    replacement_uuid="123e4567-e89b-12d3-a456-426614174000"
)

# Validate output file
result = validate_output_file("project_review.txt")
if result["is_valid"]:
    print("Valid prepdir output")
else:
    print(f"Errors: {result['errors']}")
```

### **Sample Output**
```plaintext
File listing generated 2025-06-14 23:24:00.123456 by prepdir version 0.13.0 (pip install prepdir)
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=

=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=
This is a sample project.
# Sample Header
- Item 1
- Item 2
=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=
```

### **Configuration Precedence**
1. **Custom config**: Specified with `--config` or `config_path` (highest precedence)
2. **Local config**: `.prepdir/config.yaml` in your project directory
3. **Global config**: `~/.prepdir/config.yaml` in your home directory
4. **Bundled config**: Built-in at `src/prepdir/config.yaml` (lowest precedence)

When `TEST_ENV=true`, default config files (local and global) are skipped for testing purposes.

### **Default Exclusions**
- Version control: `.git`
- Cache files: `__pycache__`, `.pytest_cache`, `.mypy_cache`
- Build artifacts: `dist`, `build`, `*.egg-info`
- IDE files: `.idea`
- Dependencies: `node_modules`
- Temporary files: `*.pyc`, `*.log`
- `prepdir`-generated files: Files like `prepped_dir.txt` (unless `--include-prepdir-files` or `include_prepdir_files=True` is used)
- Config files: `.prepdir/config.yaml`, `~/.prepdir/config.yaml`

### **UUID Scrubbing**
By default, `prepdir` scrubs UUIDs in file contents, replacing them with `00000000-0000-0000-0000-000000000000` (per config). UUIDs are matched as standalone tokens (surrounded by word boundaries, e.g., whitespace or punctuation) to avoid replacing embedded strings. Hyphen-less UUIDs are also scrubbed by default (per `SCRUB_HYPHENLESS_UUIDS`). Configure via:
- CLI: `--no-scrub-uuids` or `--replacement-uuid <uuid>` (overrides config)
- CLI: `--no-scrub-hyphenless-uuids` to disable hyphen-less UUID scrubbing
- Programmatic: `scrub_uuids=None` (uses config) or `scrub_uuids=False`, `replacement_uuid=None` (uses config) or `replacement_uuid="custom-uuid"`, `scrub_hyphenless_uuids=None` or `scrub_hyphenless_uuids=False`
- `config.yaml`: `SCRUB_UUIDS` (boolean, default: `true`), `REPLACEMENT_UUID` (string, default: `"00000000-0000-0000-0000-000000000000"`), `SCRUB_HYPHENLESS_UUIDS` (boolean, default: `true`)

### **Creating a Config**
```bash
# Initialize a local config
prepdir --init

# Or create manually
mkdir .prepdir
echo "EXCLUDE:
  DIRECTORIES:
    - .git
  FILES:
    - *.pyc
SCRUB_UUIDS: true
SCRUB_HYPHENLESS_UUIDS: true
REPLACEMENT_UUID: \"00000000-0000-0000-0000-000000000000\"" > .prepdir/config.yaml
```

## 📜 Logging
`prepdir` uses Python’s standard logging with a default level of `INFO` and format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Control verbosity with the `LOGLEVEL` environment variable:
```bash
LOGLEVEL=DEBUG prepdir
```

Valid `LOGLEVEL` values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Use verbose mode for additional details:
```bash
prepdir -v
# or
from prepdir import run
run(verbose=True)
```

## 🧐 Why Use prepdir?
`prepdir` simplifies sharing code with AI assistants:
- **Save Time**: Automates collecting and formatting project files.
- **Provide Context**: Combines all relevant files into one structured file.
- **Filter Automatically**: Excludes irrelevant files like caches, binaries, and `prepdir`-generated files.
- **Protect Privacy**: Scrubs UUIDs (including hyphen-less) by default to anonymize sensitive identifiers.
- **Enhance Clarity**: Uses clear separators and relative paths for AI compatibility.
- **Programmatic Access**: Use as a library to integrate with other tools or scripts.
- **Streamline Workflow**: Optimizes code review, analysis, and documentation tasks.

## 🔍 Common Use Cases
1. **Code Review with AI**
```bash
prepdir -e py -o code_review.txt
# Ask AI: "Review my Python code for bugs and improvements"
```

2. **Debugging Help**
```bash
prepdir -e py log -o debug_context.txt
# Ask AI: "Help me debug errors in these logs and Python files"
```

3. **Refactoring Suggestions**
```bash
prepdir -e py -o refactor.txt
# Ask AI: "Suggest refactoring improvements for this Python code"
```

4. **Documentation Generation**
```bash
prepdir -e py md rst -o docs_context.txt
# Ask AI: "Generate detailed documentation for this project"
```

5. **Programmatic Integration**
```python
from prepdir import run
content = run(directory="src", extensions=["py"], output_file="code.txt")
# Process content or send to AI assistant
```

## 🔧 Advanced Options
```bash
# Include all files, ignoring exclusions
prepdir --all

# Include prepdir-generated files
prepdir --include-prepdir-files

# Disable UUID scrubbing (overrides config)
prepdir --no-scrub-uuids

# Disable hyphen-less UUID scrubbing (overrides config)
prepdir --no-scrub-hyphenless-uuids

# Use a custom replacement UUID (overrides config)
prepdir --replacement-uuid 123e4567-e89b-12d3-a456-426614174000

# Use a custom config file
prepdir --config custom_config.yaml

# Check version
prepdir --version
```

### **Programmatic Use**
Import `prepdir` in your Python project:
```python
from prepdir import run, validate_output_file
content = run(directory="/path/to/project", extensions=["py"], verbose=True)
result = validate_output_file("output.txt")
```

### **Configuration Management**
The `load_config` function in `prepdir.config` uses Dynaconf for shared configuration across tools like `vibedir` and `applydir`, with the precedence described above.

### **Development Setup**
```bash
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pdm install
pdm run prepdir  # Run development version
pdm run pytest   # Run tests
pdm publish      # Publish to PyPI (requires credentials)
```

### **Common Issues**
- **No files found**: Verify directory path and file extensions (`-e` or `extensions`).
- **Files missing**: Check exclusions in config with `-v` or `verbose=True`. Note that `prepdir`-generated files are excluded by default unless `--include-prepdir-files` or `include_prepdir_files=True` is used.
- **UUIDs not scrubbed**: Ensure `--no-scrub-uuids` or `scrub_uuids=False` is not used and `SCRUB_UUIDS` is not set to `false` in the config. Verify the UUID is a standalone token.
- **Hyphen-less UUIDs not scrubbed**: Ensure `--no-scrub-hyphenless-uuids` or `scrub_hyphenless_uuids=False` is not used and `SCRUB_HYPHENLESS_UUIDS` is not set to `false`.
- **Invalid replacement UUID**: Check that `--replacement-uuid` or `REPLACEMENT_UUID` is a valid UUID. Invalid UUIDs default to the nil UUID.
- **Config errors**: Ensure valid YAML syntax in `config.yaml`.
- **Command not found**: Confirm Python environment and PATH.

### **Verbose Mode**
```bash
prepdir -v
# or
from prepdir import run
run(verbose=True)
```

## 📝 FAQ
**Q: What project sizes can prepdir handle?**  
A: Effective for moderate projects (thousands of files). Use `-e` or `extensions` to filter large projects.

**Q: Can prepdir handle non-code files?**  
A: Yes, it supports any text file. Specify types with `-e` or `extensions` (e.g., `prepdir -e txt md`).

**Q: Why are my prepdir output files missing from the new output?**  
A: Starting with version 0.11.0, `prepdir` excludes its own generated files (e.g., `prepped_dir.txt`) by default. Use `--include-prepdir-files` or `include_prepdir_files=True` to include them.

**Q: When should I use `--include-prepdir-files`?**  
A: Use it if you need to include previously generated output files in a new output, such as when reviewing past `prepdir` runs or combining multiple outputs.

**Q: Why are UUIDs replaced in my output?**  
A: Starting with version 0.12.0, `prepdir` scrubs UUIDs by default. Use `--no-scrub-uuids` or `scrub_uuids=False` to disable, or configure `SCRUB_UUIDS: false` in `config.yaml`.

**Q: Why are hyphen-less UUIDs replaced?**  
A: Starting with version 0.13.0, `prepdir` scrubs hyphen-less UUIDs by default. Use `--no-scrub-hyphenless-uuids` or `scrub_hyphenless_uuids=False` to disable, or configure `SCRUB_HYPHENLESS_UUIDS: false`.

**Q: Can I customize the replacement UUID?**  
A: Yes, use `--replacement-uuid <uuid>` or `replacement_uuid="<uuid>"` in code, or set `REPLACEMENT_UUID` in `config.yaml`.

**Q: Why am I getting an error about lowercase configuration keys?**  
A: In versions 0.10.0 to 0.12.0, `prepdir` required uppercase keys. This was removed in 0.13.0, so keys can now be in any case.

**Q: How do I upgrade from older versions?**  
A: For versions <0.6.0, move `config.yaml` to `.prepdir/config.yaml` or use `--config config.yaml`. For versions <0.13.0, note that uppercase key requirements are no longer enforced.

**Q: Are glob patterns supported?**  
A: Yes, use .gitignore-style patterns like `*.pyc` or `**/*.log` in configs.