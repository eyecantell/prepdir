# 🗂️ prepdir

[![CI](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml/badge.svg)](https://github.com/eyecantell/prepdir/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/prepdir.svg)](https://badge.fury.io/py/prepdir)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://pepy.tech/badge/prepdir)](https://pepy.tech/project/prepdir)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight CLI utility to prepare your code project for AI assistants, formatting file contents with clear separators for easy sharing. **Get Started**: [Quick Start](#-quick-start)

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

### 0.11.0
- Added automatic exclusion of `prepdir`-generated files (e.g., `prepped_dir.txt`) by default, with new `--include-prepdir-files` option to include them.

### 0.10.1
- Added validation for uppercase configuration keys (`EXCLUDE`, `DIRECTORIES`, `FILES`) with guidance for users upgrading from older versions.

See [CHANGELOG.md](docs/CHANGELOG.md) for the complete version history.

## 🚀 Quick Start

Get up and running with `prepdir` in minutes:

```bash
# Install prepdir
pip install prepdir

# Navigate to your project
cd /path/to/your/project

# Generate prepped_dir.txt with all project files
prepdir

# Share prepped_dir.txt with an AI assistant
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

### **Basic Usage**

```bash
# Output all files to prepped_dir.txt
prepdir

# Include only Python files
prepdir -e py

# Include Python and Markdown files
prepdir -e py md

# Use a custom output file
prepdir -o my_project.txt

# Include prepdir-generated files
prepdir --include-prepdir-files -o project_with_outputs.txt

# Process a specific directory
prepdir /path/to/directory
```

## ⚙️ Configuration

`prepdir` uses [Dynaconf](https://dynaconf.com) for flexible and robust configuration management, allowing seamless handling of settings across projects.

### **Configuration Precedence**

1. **Custom config**: Specified with `--config` (highest precedence)
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
- `prepdir`-generated files: Files like `prepped_dir.txt` (unless `--include-prepdir-files` is used)

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
```

## 🧐 Why Use prepdir?

`prepdir` simplifies sharing code with AI assistants by:

- **Save Time**: Automates collecting and formatting project files.
- **Provide Context**: Combines all relevant files into one structured file.
- **Filter Automatically**: Excludes irrelevant files like caches, binaries, and `prepdir`-generated files.
- **Enhance Clarity**: Uses clear separators and relative paths for AI compatibility.
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

## 🔧 Advanced Options

```bash
# Include all files, ignoring exclusions
prepdir --all

# Include prepdir-generated files
prepdir --include-prepdir-files

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

- **No files found**: Verify directory path and file extensions (`-e`).
- **Files missing**: Check exclusions in config with `-v`. Note that `prepdir`-generated files are excluded by default unless `--include-prepdir-files` is used. Use `-v` to see specific reasons for skipped files (e.g., "prepdir-generated file").
- **Config errors**: Ensure valid YAML syntax in `config.yaml` and uppercase keys (`EXCLUDE`, `DIRECTORIES`, `FILES`).
- **Command not found**: Confirm Python environment and PATH.

### **Verbose Mode**

```bash
prepdir -v
```

## 📝 FAQ

**Q: What project sizes can prepdir handle?**  
A: Effective for moderate projects (thousands of files). Use `-e` to filter large projects.

**Q: Can prepdir handle non-code files?**  
A: Yes, it supports any text file. Specify types with `-e` (e.g., `prepdir -e txt md`).

**Q: Why are my prepdir output files missing from the new output?**  
A: Starting with version 0.11.0, `prepdir` excludes its own generated files (e.g., `prepped_dir.txt`) by default. Use `--include-prepdir-files` to include them.

**Q: When should I use `--include-prepdir-files`?**  
A: Use `--include-prepdir-files` if you need to include previously generated output files (e.g., `prepped_dir.txt`) in a new output, such as when reviewing past `prepdir` runs or combining multiple outputs from disparate directories.

**Q: Why am I getting an error about lowercase configuration keys?**  
A: Starting with version 0.10.0, `prepdir` uses Dynaconf, which requires configuration keys like `EXCLUDE`, `DIRECTORIES`, and `FILES` to be uppercase. Please update any custom `config.yaml` to use uppercase keys. See the [Configuration section](#configuration) for details.

**Q: How do I upgrade from older versions?**  
A: For versions <0.6.0, move `config.yaml` to `.prepdir/config.yaml` or use `--config config.yaml`.

**Q: Are glob patterns supported?**  
A: Yes, use .gitignore-style patterns like `*.pyc` or `**/*.log` in configs.

## 🤝 Contributing

We welcome contributions! Check out our [GitHub Issues](https://github.com/eyecantell/prepdir/issues) or submit a pull request. See [CONTRIBUTING.md](https://github.com/eyecantell/prepdir/blob/main/CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.