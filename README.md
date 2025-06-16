# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://pepy.tech/badge/prepdir)](https://pepy.tech/project/prepdir)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight CLI and library utility to prepare your code project for AI assistants, formatting file contents with clear separators for easy sharing. **Get Started**: [Quick Start](#-quick-start)

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

### 0.13.0
- Added `run()` and `validate_output_file()` functions for programmatic use, enabling `prepdir` as a library (`from prepdir import run, validate_output_file`).
- Improved configuration loading: local `.prepdir/config.yaml` now takes precedence over `~/.prepdir/config.yaml`, with `TEST_ENV=true` skipping defaults for testing.
- Removed uppercase key requirement for `config.yaml` (introduced in 0.10.0).
- Standardized logging with `LOGLEVEL` environment variable (e.g., `LOGLEVEL=DEBUG prepdir`).
- CLI arguments `--no-scrub-uuids` and `--replacement-uuid` now override `config.yaml` settings, with config as default otherwise.
- Added support for scrubbing hyphen-less UUIDs via `SCRUB_HYPHENLESS_UUIDS` in `config.yaml` and `--no-scrub-hyphenless-uuids` CLI flag.
- Enhanced tests for configuration and programmatic functionality.

### 0.12.0
- Added automatic scrubbing of UUIDs in file contents, replacing them with the nil UUID (`00000000-0000-0000-0000-000000000000`) by default. UUIDs are matched as standalone tokens (using word boundaries) to avoid false positives. Use `--no-scrub-uuids` to disable or `--replacement-uuid` to specify a custom UUID. Configure via `SCRUB_UUIDS` and `REPLACEMENT_UUID` in `config.yaml`.
- Shortened file delimiter from 31 to 15 characters to reduce token usage in AI model inputs.

### 0.11.0
- Added automatic exclusion of `prepdir`-generated files (e.g., `prepped_dir.txt`) by default, with new `--include-prepdir-files` option to include them.

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
content = run(directory="/path/to/project", extensions=["py"])
print(content)  # Use the content directly
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