prepdir
A utility to traverse directories and prepare file contents, designed specifically for sharing code projects with AI assistants for review and analysis.
Features

Recursively walks through directories
Displays relative paths and file contents
Skips specified directories and files (configured via config.yaml)
Filters files by extension
Outputs to a file (default: prepped_dir.txt)
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

# Specific directory and extensions
prepdir /path/to/directory -e py md

Configuration
Exclusions for directories and files are defined in config.yaml:
exclude:
  directories:
    - .git
    - __pycache__
    - .pdm-build
  files:
    - .gitignore
    - LICENSE

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
