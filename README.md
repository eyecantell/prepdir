prepdir

A utility to traverse directories and prepare file contents, designed specifically for sharing code projects with AI assistants for review and analysis.
Features

Recursively walks through directories
Displays relative paths and file contents
Skips specified directories and files using .gitignore-style glob patterns (configured via config.yaml)
Automatically excludes the output file (e.g., prepped_dir.txt)
Filters files by extension
Outputs to a file (default: prepped_dir.txt)
Option to include all files and directories, ignoring exclusions
Customizable configuration file path (supports ~/.prepdir/config.yaml or user-specified path)
Verbose mode to log skipped files and directories
Easy-to-use command-line interface
Perfect for sending code to AI assistants for review

Installation
Using PDM (recommended)
# Install PDM if you don't already have it
pip install pdm

# Install in development mode
pdm install

# Install for system-wide use
pdm build
pip install dist/*.whl

Using pip
# Install from PyPI (once published)
pip install prepdir

# Install from GitHub
pip install git+https://github.com/eyecantell/prepdir.git

Usage
# Output all files in current directory to prepped_dir.txt
prepdir

# Output to a custom file
prepdir -o output.txt

# Output all files in specified directory
prepdir /path/to/directory

# Only output Python files
prepdir -e py

# Output Python and Markdown files to custom file
prepdir -o project_files.txt -e py md

# Include all files and directories, ignoring exclusions
prepdir --all

# Use a custom config file
prepdir --config custom_config.yaml

# Enable verbose output
prepdir -v

# Show the version number
prepdir --version

# Combine options
prepdir /path/to/directory --all -e py -o output.txt -v --config custom_config.yaml

Testing
To run the test suite, ensure pytest is installed (included in development dependencies):
# Install development dependencies
pdm install

# Run tests
pdm run pytest

Configuration
Exclusions for directories and files are defined in config.yaml, which can be located in:

The user's home directory at ~/.prepdir/config.yaml (highest precedence).
A custom path specified with --config (e.g., --config custom_config.yaml).
The default config.yaml included with the package (lowest precedence).

The output file (e.g., prepped_dir.txt) is automatically excluded. The configuration uses .gitignore-style glob patterns.
Example config.yaml:
exclude:
  directories:
    - .git
    - __pycache__
    - .pdm-build
    - .venv
    - venv
    - .idea
    - node_modules
    - dist
    - build
    - .pytest_cache
    - .mypy_cache
    - .cache
    - .eggs
    - .tox
    - "*.egg-info"
  files:
    - .gitignore
    - LICENSE
    - .DS_Store
    - Thumbs.db
    - .env
    - .coverage
    - coverage.xml
    - .pdm-python
    - "*.pyc"
    - "*.pyo"
    - "*.log"
    - "*.bak"
    - "*.swp"
    - "**/*.log"

To use a global configuration, create ~/.prepdir/config.yaml:
mkdir -p ~/.prepdir
echo "exclude:\n  directories:\n    - .git\n  files:\n    - *.pyc" > ~/.prepdir/config.yaml

Use Cases

AI Code Review: Easily prepare your entire codebase for AI assistants
Project Analysis: Get a comprehensive view of project structure and content
Knowledge Transfer: Help AI understand your project context quickly
Bug Hunting: Provide full context when asking for debugging help

Development
This project uses PDM for dependency management and packaging.
# Clone the repository
git clone https://github.com/eyecantell/prepdir.git
cd prepdir

# Install development dependencies
pdm install

# Run in development mode
pdm run prepdir

License
MIT
