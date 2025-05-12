# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight CLI utility that prepares your code project for sharing with AI assistants by automatically formatting file contents with clear separation between files.

```
prepdir -e py md -o ai_review.txt
```

## 📋 Contents

- [Why Use prepdir?](#-why-use-prepdir)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [Configuration](#-configuration)
- [Common Use Cases](#-common-use-cases)
- [For Developers](#-for-developers)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)

## 🤔 Why Use prepdir?

When sharing code with AI assistants for review or analysis, context is crucial. **prepdir** solves common problems:

- **Complete Context**: Creates a single file containing all relevant project files
- **Clear Structure**: Adds distinct separators between files with relative paths
- **Smart Filtering**: Automatically excludes irrelevant files like `.git` and `node_modules`
- **Time Saving**: Eliminates manual copying/formatting of individual files
- **AI-Optimized**: Formatted specifically for AI assistants to understand project structure

## 📦 Installation

### Using pip (recommended)

```bash
pip install prepdir
```

### From GitHub

```bash
pip install git+https://github.com/eyecantell/prepdir.git
```

### For Development

```bash
git clone https://github.com/eyecantell/prepdir.git
cd prepdir
pip install -e .
```

## 🚀 Quick Start

```bash
# Install
pip install prepdir

# Navigate to your project
cd /path/to/your/project

# Create prepped_dir.txt with all project files
prepdir

# Share prepped_dir.txt with an AI assistant
```

## 💡 Usage Examples

### Basic Usage

```bash
# Process current directory, output to prepped_dir.txt
prepdir

# Only include Python files
prepdir -e py

# Only include Python and Markdown files
prepdir -e py md

# Custom output filename
prepdir -o my_project.txt

# Process a specific directory
prepdir /path/to/directory
```

### Advanced Options

```bash
# Include all files (ignore exclusion rules)
prepdir --all

# Use a custom config file
prepdir --config custom_config.yaml

# Initialize a local .prepdir/config.yaml
prepdir --init

# Verbose mode to see what's being skipped
prepdir -v
```

## ⚙️ Configuration

### Configuration Precedence

1. **Custom config**: Specified via `--config` option (highest precedence)
2. **Project config**: `.prepdir/config.yaml` in your local directory 
3. **Global config**: `~/.prepdir/config.yaml`
4. **Default config**: Built into the package (lowest precedence)

### Default Exclusions

By default, prepdir skips:
- Version control: `.git`
- Build artifacts: `dist`, `build`
- Cache directories: `__pycache__`, `.pytest_cache`
- Virtual environments: `.venv`, `venv`
- IDE files: `.idea`
- Dependencies: `node_modules`
- Temporary files: `*.pyc`, `*.log`

### Creating/Customizing Configuration

#### Initialize a project config:

```bash
# Create .prepdir/config.yaml with default settings
prepdir --init

# Overwrite existing config
prepdir --init --force
```

#### Example config.yaml:

```yaml
exclude:
  directories:
    - .git
    - __pycache__
    - .venv
    - node_modules
    - dist
    - "*.egg-info"
  files:
    - .gitignore
    - .DS_Store
    - "*.pyc"
    - "*.log"
```

## 🔍 Common Use Cases

### 1. Code Review by AI Assistants

```bash
# Generate a file with just Python source files
prepdir -e py -o code_review.txt

# Upload file and Ask AI: "Please review this Python project for best practices"
```

### 2. Project Analysis

```bash
# Include all project files
prepdir --all -o full_project.txt

# Upload file and Ask AI: "Help me understand the architecture of this project"
```

### 3. Bug Hunting

```bash
# Focus on a specific area of code
prepdir ./src/problematic_module -e py -o debug.txt

# Upload file and Ask AI: "Help me find the bug causing this error message..."
```

### 4. Documentation Generation

```bash
# Collect Python files and docs
prepdir -e py md rst -o docs_context.txt

# Upload file and Ask AI: "Generate detailed documentation for this project"
```

## 👨‍💻 For Developers

### Development Setup

```bash
# Clone the repository
git clone https://github.com/eyecantell/prepdir.git
cd prepdir

# Install with PDM in development mode
pdm install

# Run the development version
pdm run prepdir

# Run tests
pdm run pytest
```

### Building and Publishing

```bash
# Build the package
pdm build

# Install locally from build
pip install dist/*.whl

# Publish to PyPI (with credentials)
pdm publish
```

## ❓ Troubleshooting

### Common Issues

- **No files found**: Check your directory path and file extensions
- **Missing expected files**: Verify they're not being excluded in config
- **Error loading config.yaml**: Ensure YAML syntax is valid
- **Package not found after install**: Verify your Python environment/PATH

### Verbose Mode

Run with `-v` to see what files are being skipped and why:

```bash
prepdir -v
```

## 📝 FAQ

**Q: How large a project can prepdir handle?**  
A: prepdir works well with projects up to moderate size (thousands of files). For very large projects, consider using file extensions filters (`-e`) to focus on relevant files.

**Q: Can I use prepdir with non-code files?**  
A: Yes! While designed for code, prepdir works with any text file. Use `-e` to include specific file types.

**Q: How do I upgrade from a previous version?**  
A: If you previously used `config.yaml` in your project directory (versions <0.6.0), move it to `.prepdir/config.yaml` or specify it with `--config config.yaml`.

**Q: Can I use glob patterns in configuration?**  
A: Yes, the configuration accepts standard .gitignore-style glob patterns like `*.pyc` or `**/*.log`.

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.