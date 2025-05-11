Installation Guide for prepdir
Project Structure
After setting up, your project directory should look like this:
prepdir/
├── pyproject.toml
├── README.md
├── INSTALL.md
├── config.yaml
└── src/
    └── prepdir/
        ├── __init__.py
        └── main.py

This structure follows PDM's best practices with the package inside the src directory.
Installation Methods
Method 1: Install with PDM (Recommended)
PDM is a modern Python package manager that this project uses.
# Install PDM if you don't have it
pip install pdm

# Navigate to the directory containing pyproject.toml
cd /path/to/prepdir

# Install in development mode (editable)
pdm install

# Run the tool directly
pdm run prepdir

Method 2: Build and Install
To create a distributable package and install it:
# Build the package
pdm build

# Install the wheel
pip install dist/*.whl

Method 3: Install from GitHub
pip install git+https://github.com/eyecantell/prepdir.git

Method 4: Install from PyPI (once published)
pip install prepdir

Publishing to PyPI
If you want to share your tool with others, you can publish it to PyPI:

Make sure PDM is installed:
pip install pdm


Build the package:
pdm build


Upload to PyPI (requires PyPI credentials):
pdm publish



Usage after Installation
After installation, you can use the tool from anywhere:
# Output all files in current directory to prepped_dir.txt
prepdir

# Output to a custom file
prepdir -o output.txt

# Filter files by extension
prepdir -e py md

# Specify a different directory
prepdir /path/to/directory -e py

# Include all files and directories, ignoring exclusions
prepdir --all

# Use a custom config file
prepdir --config custom_config.yaml

# Enable verbose output
prepdir -v

Configuration
Exclusions for directories and files are defined in config.yaml (or a custom file specified with --config) using .gitignore-style glob patterns:
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
    - *.egg-info
  files:
    - .gitignore
    - LICENSE
    - .DS_Store
    - Thumbs.db
    - .env
    - .coverage
    - coverage.xml
    - .pdm-python
    - *.pyc
    - *.pyo
    - *.log
    - *.bak
    - *.swp
    - **/*.log

Development Setup
For development:
# Clone the repository
git clone https://github.com/eyecantell/prepdir.git
cd prepdir

# Install with PDM in development mode
pdm install

# Run the development version
pdm run prepdir

# Add dependencies if needed
pdm add some-package

# Add development dependencies
pdm add -d pytest

