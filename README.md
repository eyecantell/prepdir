# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/runs/16384663620)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://pepy.tech/badge/prepdir)](https://pepy.tech/project/prepdir)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight directory traversal utility designed to prepare project contents for AI code review and analysis. Quickly gather all your project files into a single, well-formatted document that's perfect for sharing with AI assistants.

## 🚀 Quick Start

Get up and running in 30 seconds:

```bash
# Install
pip install prepdir

# Navigate to your project
cd /path/to/your/project

# Generate a file with all your code
prepdir

# Share prepped_dir.txt with your AI assistant
```

That's it! You now have a `prepped_dir.txt` file containing all your project files with clear delimiters, ready for AI review.

### Python Integration
```python
from prepdir import run

# Generate content for Python files
output = run(directory="/path/to/project", extensions=["py"])
print(output.content)  # Use the content directly
```

## 🎯 Why Use prepdir?

**Save hours of manual work** when sharing code with AI assistants:
- ✅ **Instant Context**: Combines all relevant files into one structured document
- ✅ **Smart Filtering**: Automatically excludes cache files, build artifacts, and other noise
- ✅ **Privacy Protection**: Scrubs UUIDs and sensitive identifiers by default
- ✅ **AI-Optimized**: Uses clear separators and formatting that AI models love
- ✅ **Flexible**: CLI tool + Python library for any workflow

## 📦 Installation

```bash
pip install prepdir
```

**Alternative methods:**
```bash
# From GitHub
pip install git+https://github.com/eyecantell/prepdir.git

# Development install
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pip install -e .
```

## 💡 Usage Examples

### Command Line Interface

```bash
# Basic usage - all files
prepdir

# Only Python files
prepdir -e py

# Multiple file types
prepdir -e py js html css

# Custom output file
prepdir -o my_review.txt

# Specific directory
prepdir /path/to/project

# Include everything (ignore exclusions)
prepdir --all

# Disable UUID scrubbing
prepdir --no-scrub-uuids

# Initialize default configuration
prepdir --init
```

### Programmatic Use

Use `prepdir` as a library to process directories programmatically:

```python
from prepdir import run, PrepdirOutputFile, PrepdirProcessor

# Run and get a PrepdirOutputFile object
output: PrepdirOutputFile = run(directory="my_project", extensions=["py", "md"], use_unique_placeholders=True)

# Access processed files
for abs_path, file_entry in output.files.items():
    print(f"File: {file_entry.relative_path}, Content: {file_entry.content}")

# Save to file
output.save("prepped_dir.txt")

# For legacy use, get raw output
content, uuid_mapping, files_list, metadata = run(directory="my_project")
```

### Sample Output

```plaintext
File listing generated 2025-07-17T19:50:21.946603 by prepdir version 0.17.1
Base directory is '/path/to/project'
Note: Valid (hyphenated) UUIDs in file contents will be scrubbed and replaced with '00000000-0000-0000-0000-000000000000'.
Note: Valid hyphen-less UUIDs in file contents will be scrubbed and replaced with '00000000000000000000000000000000'.
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=
# My Project
This is a sample project.
=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=
```

## 🔍 Common Use Cases

### 1. **Code Review with AI**
```bash
prepdir -e py -o code_review.txt
# Ask AI: "Review my Python code for bugs and improvements"
```

### 2. **Debugging Help**
```bash
prepdir -e py log -o debug_context.txt
# Ask AI: "Help me debug errors in these logs and Python files"
```

### 3. **Documentation Generation**
```bash
prepdir -e py md rst -o docs_context.txt
# Ask AI: "Generate detailed documentation for this project"
```

### 4. **Architecture Analysis**
```bash
prepdir -e py js ts -o architecture.txt
# Ask AI: "Analyze the architecture and suggest improvements"
```

## ⚙️ Configuration

### Configuration Files
prepdir looks for configuration in this order:
1. Custom config (via `--config`)
2. Local: `.prepdir/config.yaml`
3. Global: `~/.prepdir/config.yaml`
4. Built-in defaults

### Create Configuration
```bash
# Initialize local config at .prepdir/config.yaml
prepdir --init

# Or create manually
mkdir .prepdir
cat > .prepdir/config.yaml << EOF
# Configuration file for prepdir
EXCLUDE:
  DIRECTORIES:
    - __pycache__
    - .applydir
    - .cache
    - .eggs
    - .git
    - .idea
    - .mypy_cache
    - .pdm-build
    - .prepdir
    - .pytest_cache
    - .ruff_cache
    - .tox
    - .venv
    - .vibedir
    - '*.egg-info'
    - build
    - dist
    - node_modules
    - venv
  FILES:
    - .gitignore
    - .prepdir/config.yaml
    - ~/.prepdir/config.yaml
    - LICENSE
    - .DS_Store
    - Thumbs.db
    - .env
    - .env.production
    - .coverage
    - coverage.xml
    - .pdm-python
    - pdm.lock
    - "*.pyc"
    - "*.pyo"
    - "*.log"
    - "*.bak"
    - "*.swp"
    - "**/*.log"
SCRUB_HYPHENATED_UUIDS: true
SCRUB_HYPHENLESS_UUIDS: true
REPLACEMENT_UUID: "00000000-0000-0000-0000-000000000000"
DEFAULT_EXTENSIONS: []
DEFAULT_OUTPUT_FILE: "prepped_dir.txt"
USE_UNIQUE_PLACEHOLDERS: false
INCLUDE_PREPDIR_FILES: false
VERBOSE: false
EOF
```

### Default Exclusions
- **Version control**: `.git`
- **Cache files**: `__pycache__`, `.cache`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`
- **Build artifacts**: `build`, `dist`, `*.egg-info`, `.pdm-build`
- **IDE files**: `.idea`
- **Virtual environments**: `.venv`, `venv`
- **Dependencies**: `node_modules`
- **Configuration**: `.applydir`, `.prepdir`, `.vibedir`, `.tox`
- **Temporary files**: `*.pyc`, `*.pyo`, `*.log`, `*.bak`, `*.swp`, `**/*.log`
- **System files**: `.DS_Store`, `Thumbs.db`
- **Project files**: `.gitignore`, `.env`, `.env.production`, `.coverage`, `coverage.xml`, `.pdm-python`, `pdm.lock`, `LICENSE`, `.prepdir/config.yaml`, `~/.prepdir/config.yaml`
- **prepdir outputs**: `prepped_dir.txt` (unless `--include-prepdir-files`)

## 🔒 Privacy & Security

### UUID Scrubbing
By default, prepdir protects your privacy by replacing UUIDs with placeholder values:

```python
# Original
user_id = "123e4567-e89b-12d3-a456-426614174000"

# After scrubbing  
user_id = "00000000-0000-0000-0000-000000000000"
```

**Control UUID scrubbing:**
- CLI: `--no-scrub-uuids`, `--no-scrub-hyphenated-uuids`, `--no-scrub-hyphenless-uuids`, or `--replacement-uuid <uuid>`
- Python: `scrub_hyphenated_uuids=False`, `scrub_hyphenless_uuids=False`, or `replacement_uuid="custom-uuid"`
- Config: Set `SCRUB_HYPHENATED_UUIDS: false`, `SCRUB_HYPHENLESS_UUIDS: false`, or `REPLACEMENT_UUID: "custom-uuid"`

### Unique Placeholders
Generate unique placeholders for each UUID to maintain relationships:

```python
from prepdir import run

output = run(directory="/path/to/project", use_unique_placeholders=True)
print("UUID Mapping:", output.uuid_mapping)
# Output: {'PREPDIR_UUID_PLACEHOLDER_1': 'original-uuid-1', ...}
```

## 🔧 Advanced Features

### Command Line Options
```bash
prepdir --help

# Key options:
-e, --extensions            File extensions to include
-o, --output               Output file name
--init                    Initialize local config at .prepdir/config.yaml
--config                  Custom config file
--force                   Overwrite existing config file with --init
--all                     Include all files (ignore exclusions)
--include-prepdir-files   Include prepdir-generated files (e.g., prepped_dir.txt)
--no-scrub-uuids          Disable all UUID scrubbing
--no-scrub-hyphenated-uuids  Disable hyphenated UUID scrubbing
--no-scrub-hyphenless-uuids  Disable hyphen-less UUID scrubbing
--replacement-uuid        Custom replacement UUID
--use-unique-placeholders Replace UUIDs with unique placeholders
-v, --verbose             Verbose output
-q, --quiet               Suppress user-facing output
```

### Python API Reference
```python
from prepdir import run, PrepdirProcessor

# Full API
output = run(
    directory="/path/to/project",           # Target directory
    extensions=["py", "js"],                # File extensions
    specific_files=["file1.py"],            # Specific files
    output_file="output.txt",               # Save to file
    config_path="custom.yaml",              # Custom config
    scrub_hyphenated_uuids=True,            # Scrub hyphenated UUIDs
    scrub_hyphenless_uuids=True,            # Scrub hyphenless UUIDs
    replacement_uuid="custom-uuid",         # Custom replacement
    use_unique_placeholders=False,          # Unique placeholders
    ignore_exclusions=False,                # Ignore exclusions
    include_prepdir_files=False,            # Include prepdir outputs
    quiet=False                            # Suppress output
)

# Validate output
processor = PrepdirProcessor(directory="/path/to/project")
output = processor.validate_output(file_path="output.txt")
# Returns: PrepdirOutputFile object
```

## 📊 Logging & Debugging

Control verbosity with environment variables:
```bash
LOGLEVEL=DEBUG prepdir -v
```

Valid levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 📈 What's New

### Version 0.17.2 (Latest)
- Fixed issue that caused running verbose to be no change. 

### Version 0.17.1 (Latest)
- Fixed issue that caused error when running `prepdir --init`

### Version 0.17.0
- Improved performance and recursive glob handling

[View complete changelog](docs/CHANGELOG.md)

## 🤔 FAQ

<details>
<summary><strong>Q: What project sizes can prepdir handle?</strong></summary>
A: Effective for small to moderate projects (thousands of files). Use file extension filters for larger projects. The limitation will more likely be what the LLM can handle. 
</details>

<details>
<summary><strong>Q: Why are my prepdir output files missing?</strong></summary>
A: prepdir excludes its own generated files (e.g., `prepped_dir.txt`) by default. Use `--include-prepdir-files` to include them.
</details>

<details>
<summary><strong>Q: Why are UUIDs replaced in my output?</strong></summary>
A: Privacy protection! prepdir scrubs UUIDs by default. Use `--no-scrub-uuids` to disable.
</details>

<details>
<summary><strong>Q: Can I use prepdir with non-code files?</strong></summary>
A: Yes! It works with any text files. Use `-e txt md` for specific types.
</details>

<details>
<summary><strong>Q: How do I upgrade from older versions?</strong></summary>
A: Configuration files are now loaded from `.prepdir/config.yaml` (local) or `~/.prepdir/config.yaml` (global) by default. Most upgrades are seamless.
</details>

## 🛠️ Development

```bash
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pdm install          # Install dependencies
pdm run prepdir      # Run development version
pdm run pytest       # Run tests
pdm publish          # Publish to PyPI
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Love prepdir?** Give it a ⭐ on [GitHub](https://github.com/eyecantell/prepdir)!