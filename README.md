# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://pepy.tech/badge/prepdir)](https://pepy.tech/project/prepdir)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight CLI and library utility to prepare your code project for AI assistants, formatting file contents with clear separators for easy sharing. **Get Started**: [Quick Start](#-quick-start)

```
prepdir -e py md -o ai_review.txt
```

## 📋 Contents

- [What's New](#-whats-new)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Configuration](#-configuration)
- [Why Use prepdir?](#-why-use-prepdir)
- [Common Use Cases](#-common-use-cases)
- [Advanced Options](#-advanced-options)
- [For Developers](#-for-developers)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

## 📰 What's New

### 0.13.0
- Added `run()` function for programmatic use, allowing other Python projects to import `prepdir` and process directories directly (e.g., `from prepdir import run`). See [Programmatic Usage](#programmatic-usage) for details.
- Added tests for `run()` function to ensure reliability.

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

# Generate prepped_dir.txt with all project files (UUIDs scrubbed by default)
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

### **For Development**

```bash
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pip install -e .
```

## 💡 Usage Examples

### **CLI Usage**

```bash
# Output all files to prepped_dir.txt (UUIDs scrubbed)
prepdir

# Include only Python files
prepdir -e py

# Include Python and Markdown files
prepdir -e py md

# Use a custom output file
prepdir -o my_project.txt

# Include prepdir-generated files
prepdir --include-prepdir-files -o project_with_outputs.txt

# Disable UUID scrubbing
prepdir --no-scrub-uuids -o unscrubbed.txt

# Use a custom replacement UUID
prepdir --replacement-uuid 00000000-0000-0000-0000-000000000000 -o custom_uuid.txt

# Process a specific directory
prepdir /path/to/directory
```

### **Programmatic Usage**

Use `prepdir` as a library in another Python project:

```python
from prepdir import run

# Basic usage: process Python and Markdown files
content = run(
    directory="/path/to/project",
    extensions=["py", "md"],
    verbose=True
)
print(content)

# Save to a file
content = run(
    directory="/path/to/project",
    extensions=["py"],
    output_file="project_review.txt",
    scrub_uuids=False
)

# Include all files, ignoring exclusions
content = run(
    directory="/path/to/project",
    include_all=True,
    include_prepdir_files=True
)
```

### **Sample Output**

```plaintext
File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=
# My Project
This is a sample project.
=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=
```

## ⚙️ Configuration

`prepdir` uses [Dynaconf](https://dynaconf.com) for flexible and robust configuration management, allowing seamless handling of settings across projects.

### **Configuration Precedence**

1. **Custom config**: Specified with `--config` or `config_path` (highest precedence)
2. **Local config**: `.prepdir/config.yaml` in your project directory
3. **Global config**: `~/.prepdir/config.yaml` in your home directory
4. **Default config**: Built-in at `src/prepdir/config.yaml` (lowest precedence)

### **Default Exclusions**

`prepdir` skips common irrelevant files and directories, such as:

- Version control: `.git`
- Build artifacts: `dist`, `build`
- Cache directories: `__pycache__`, `.pytest_cache`
- Virtual environments: `.venv`, `venv`
- IDE files: `.idea`
- Dependencies: `node_modules`
- Temporary files: `*.pyc`, `*.log`
- `prepdir`-generated files: Files like `prepped_dir.txt` (unless `--include-prepdir-files` or `include_prepdir_files=True` is used)

### **UUID Scrubbing**

By default, `prepdir` scrubs UUIDs in file contents, replacing them with `00000000-0000-0000-0000-000000000000`. UUIDs are matched as standalone tokens (surrounded by word boundaries, e.g., whitespace or punctuation) to avoid replacing embedded strings. Configure via:

- CLI: `--no-scrub-uuids` or `--replacement-uuid <uuid>`
- Programmatic: `scrub_uuids=False` or `replacement_uuid="custom-uuid"`
- `config.yaml`: `SCRUB_UUIDS` (boolean, default: `true`), `REPLACEMENT_UUID` (string, default: `"00000000-0000-0000-0000-000000000000"`)

### **Creating a Config**

Initialize a project-level config with default settings:

```bash
# Create .prepdir/config.yaml
prepdir --init

# Overwrite existing config
prepdir --init --force
```

### **Example config.yaml**

```yaml
EXCLUDE:
  DIRECTORIES:
    - .git
    - __pycache__
    - .venv
    - node_modules
    - dist
    - "*.egg-info"
  FILES:
    - .gitignore
    - .DS_Store
    - "*.pyc"
    - "*.log"
SCRUB_UUIDS: true
REPLACEMENT_UUID: "00000000-0000-0000-0000-000000000000"
```

## 🧐 Why Use prepdir?

`prepdir` simplifies sharing code with AI assistants:

- **Save Time**: Automates collecting and formatting project files.
- **Provide Context**: Combines all relevant files into one structured file.
- **Filter Automatically**: Excludes irrelevant files like caches, binaries, and `prepdir`-generated files.
- **Protect Privacy**: Scrubs UUIDs by default to anonymize sensitive identifiers.
- **Enhance Clarity**: Uses clear separators and relative paths for AI compatibility.
- **Programmatic Access**: Use as a library to integrate with other tools or scripts.
- **Streamline Workflow**: Optimizes code review, analysis, and documentation tasks.

## 🔍 Common Use Cases

### **1. AI Code Review**

```bash
prepdir
# Ask AI: "Review Python project described in file prepped_dir.txt for best practices"
```

### **2. Project Analysis**

```bash
prepdir --all -o full_project.txt
# Ask AI: "Explain this project's architecture"
```

### **3. Bug Hunting**

```bash
prepdir ./src/problematic_module -e py -o debug.txt
# Ask AI: "Find the bug causing this error..."
```

### **4. Documentation Generation**

```bash
prepdir -e py md rst -o docs_context.txt
# Ask AI: "Generate detailed documentation for this project"
```

### **5. Programmatic Integration**

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

# Disable UUID scrubbing
prepdir --no-scrub-uuids

# Use a custom replacement UUID
prepdir --replacement-uuid 00000000-0000-0000-0000-000000000000

# Use a custom config file
prepdir --config custom_config.yaml

# Enable verbose mode to debug exclusions
prepdir -v

# Show version
prepdir --version
```

## 👨‍💻 For Developers

### **Development Setup**

```bash
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pdm install
pdm run prepdir  # Run development version
pdm run pytest   # Run tests
```

### **Programmatic Use**

Import `prepdir` in your Python project:

```python
from prepdir import run
content = run(directory="/path/to/project", extensions=["py"], verbose=True)
```

### **Configuration Management**

The `load_config` function in `prepdir.config` uses Dynaconf for shared configuration across tools like `vibedir` and `applydir`, with the precedence described above.

### **Building and Publishing**

```bash
pdm build              # Build package
pip install dist/*.whl # Install locally
pdm publish            # Publish to PyPI (requires credentials)
```

## ❓ Troubleshooting

### **Common Issues**

- **No files found**: Verify directory path and file extensions (`-e` or `extensions`).
- **Files missing**: Check exclusions in config with `-v` or `verbose=True`. Note that `prepdir`-generated files are excluded by default unless `--include-prepdir-files` or `include_prepdir_files=True` is used.
- **UUIDs not scrubbed**: Ensure `--no-scrub-uuids` or `scrub_uuids=False` is not used and `SCRUB_UUIDS` is not set to `false` in the config. Verify the UUID is a standalone token.
- **Invalid replacement UUID**: Check that `--replacement-uuid` or `replacement_uuid` in the config is a valid UUID. Invalid UUIDs default to the nil UUID.
- **Config errors**: Ensure valid YAML syntax in `config.yaml` and uppercase keys (`EXCLUDE`, `DIRECTORIES`, `FILES`, `SCRUB_UUIDS`, `REPLACEMENT_UUID`).
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

**Q: Can I customize the replacement UUID?**  
A: Yes, use `--replacement-uuid <uuid>` or `replacement_uuid="<uuid>"` in code, or set `REPLACEMENT_UUID` in `config.yaml`.

**Q: Why am I getting an error about lowercase configuration keys?**  
A: Starting with version 0.10.0, `prepdir` requires uppercase keys (`EXCLUDE`, `DIRECTORIES`, `FILES`, `SCRUB_UUIDS`, `REPLACEMENT_UUID`). Update your `config.yaml`.

**Q: How do I upgrade from older versions?**  
A: For versions <0.6.0, move `config.yaml` to `.prepdir/config.yaml` or use `--config config.yaml`. For versions <0.10.0, update configuration keys to uppercase.

**Q: Are glob patterns supported?**  
A: Yes, use .gitignore-style patterns like `*.pyc` or `**/*.log` in configs.

## 🤝 Contributing

We welcome contributions! Check out our [GitHub Issues](https://github.com/eyecantell/prepdir/issues) or submit a pull request. See [CONTRIBUTING.md](https://github.com/eyecantell/prepdir/blob/main/CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.