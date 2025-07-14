# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/runs/15799653478)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
content, _ = run(directory="/path/to/project", extensions=["py"])
print(content)  # Use the content directly
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
```

### Programmatic Use

Use `prepdir` as a library to process directories programmatically:

```python
from prepdir import run, PrepdirOutputFile

# Run and get a PrepdirOutputFile object
output: PrepdirOutputFile = run(directory="my_project", extensions=["py", "md"], use_unique_placeholders=True)

# Access processed files
for file_entry in output.files:
    print(f"File: {file_entry.path}, Content: {file_entry.content}")

# Save to file
output.save("prepped_dir.txt")

# For legacy use, get raw output
content, uuid_mapping, files_list, metadata = run(directory="my_project", return_raw=True)
```

### Sample Output

```plaintext
File listing generated 2025-06-14 23:24:00.123456 by prepdir version 0.14.1
Base directory is '/path/to/project'
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
# Initialize local config
prepdir --init

# Or create manually
mkdir .prepdir
cat > .prepdir/config.yaml << EOF
EXCLUDE:
  DIRECTORIES:
    - .git
    - node_modules
    - __pycache__
  FILES:
    - "*.pyc"
    - "*.log"
SCRUB_HYPHENATED_UUIDS: true
SCRUB_HYPHENLESS_UUIDS: true
REPLACEMENT_UUID: "00000000-0000-0000-0000-000000000000"
EOF
```

### Default Exclusions
- **Version control**: `.git`
- **Cache files**: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- **Build artifacts**: `dist`, `build`, `*.egg-info`
- **IDE files**: `.idea`, `.vscode`
- **Dependencies**: `node_modules`
- **Temporary files**: `*.pyc`, `*.log`
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
- CLI: `--no-scrub-uuids` or `--replacement-uuid <uuid>`
- Python: `scrub_hyphenated_uuids=False` or `replacement_uuid="custom-uuid"`
- Config: Set `SCRUB_HYPHENATED_UUIDS: false` or `REPLACEMENT_UUID: "custom-uuid"`

### Unique Placeholders (New in 0.14.0)
Generate unique placeholders for each UUID to maintain relationships:

```python
content, uuid_mapping = run(
    directory="/path/to/project", 
    use_unique_placeholders=True
)
print("UUID Mapping:", uuid_mapping)
# Output: {'PREPDIR_UUID_PLACEHOLDER_1': 'original-uuid-1', ...}
```

## 🔧 Advanced Features

### Command Line Options
```bash
prepdir --help

# Key options:
-e, --extensions     File extensions to include
-o, --output         Output file name
--all               Include all files (ignore exclusions)
--include-prepdir-files    Include prepdir-generated files
--no-scrub-uuids    Disable UUID scrubbing
--replacement-uuid  Custom replacement UUID
--config            Custom config file
-v, --verbose       Verbose output
```

### Python API Reference
```python
from prepdir import run, validate_output_file

# Full API
content, uuid_mapping = run(
    directory="/path/to/project",           # Target directory
    extensions=["py", "js"],                # File extensions
    output_file="output.txt",               # Save to file
    scrub_hyphenated_uuids=True,            # Scrub (hyphenated) UUIDs
    scrub_hyphenless_uuids=True,            # Scrub hyphenless UUIDs
    replacement_uuid="custom-uuid",         # Custom replacement
    use_unique_placeholders=False,          # Unique placeholders
    include_all=False,                      # Ignore exclusions
    include_prepdir_files=False,            # Include prepdir outputs
    verbose=False                           # Verbose logging
)

# Validate output
result = validate_output_file("output.txt")
# Returns: {"is_valid": bool, "errors": [], "warnings": [], "files": {}, "creation": {}}
```

## 📊 Logging & Debugging

Control verbosity with environment variables:
```bash
LOGLEVEL=DEBUG prepdir -v
```

Valid levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 📈 What's New

### Version 0.14.1 (Latest)
- Fixed typos in README and CHANGELOG

### Version 0.14.0
- ✨ **Unique UUID placeholders** - Maintain UUID relationships with unique placeholders
- 🔧 **Enhanced validation** - Improved validation of prepdir-generated files
- 🎯 **Lenient parsing** - More flexible delimiter parsing for edited files

### Version 0.13.0
- 🐍 **Python library support** - Use `from prepdir import run`
- ✅ **File validation** - Validate prepdir output files
- 🧪 **Testing improvements** - Better test isolation

[View complete changelog](docs/CHANGELOG.md)

## 🤔 FAQ

<details>
<summary><strong>Q: What project sizes can prepdir handle?</strong></summary>
A: Effective for small to moderate projects (thousands of files). Use file extension filters for larger projects. The limitation will more likely be what the LLM can handle. 
</details>

<details>
<summary><strong>Q: Why are my prepdir output files missing?</strong></summary>
A: prepdir excludes its own generated files by default. Use <code>--include-prepdir-files</code> to include them.
</details>

<details>
<summary><strong>Q: Why are UUIDs replaced in my output?</strong></summary>
A: Privacy protection! prepdir scrubs UUIDs by default. Use <code>--no-scrub-uuids</code> to disable.
</details>

<details>
<summary><strong>Q: Can I use prepdir with non-code files?</strong></summary>
A: Yes! It works with any text files. Use <code>-e txt md</code> for specific types.
</details>

<details>
<summary><strong>Q: How do I upgrade from older versions?</strong></summary>
A: For versions <0.6.0, move <code>config.yaml</code> to <code>.prepdir/config.yaml</code>. Most upgrades are seamless.
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