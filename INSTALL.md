# Installation Guide for prepdir

## Project Structure

After setting up, your project directory should look like this:

```
prepdir/
├── pyproject.toml
├── README.md
├── INSTALL.md
└── src/
    └── prepdir/
        ├── __init__.py
        └── main.py
```

This structure follows PDM's best practices with the package inside the `src` directory.

## Installation Methods

### Method 1: Install with PDM (Recommended)

[PDM](https://pdm.fming.dev/) is a modern Python package manager that this project uses.

```bash
# Install PDM if you don't have it
pip install pdm

# Navigate to the directory containing pyproject.toml
cd /path/to/prepdir

# Install in development mode (editable)
pdm install

# Run the tool directly
pdm run prepdir
```

### Method 2: Build and Install

To create a distributable package and install it:

```bash
# Build the package
pdm build

# Install the wheel
pip install dist/*.whl
```

### Method 3: Install from GitHub

```bash
pip install git+https://github.com/eyecantell/prepdir.git
```

### Method 4: Install from PyPI (once published)

```bash
pip install prepdir
```

## Publishing to PyPI

If you want to share your tool with others, you can publish it to PyPI:

1. Make sure PDM is installed:
   ```bash
   pip install pdm
   ```

2. Build the package:
   ```bash
   pdm build
   ```

3. Upload to PyPI (requires PyPI credentials):
   ```bash
   pdm publish
   ```

## Usage after Installation

After installation, you can use the tool from anywhere:

```bash
# List all files in current directory
prepdir

# Filter files by extension
prepdir -e py md

# Specify a different directory
prepdir /path/to/directory -e py
```

## Development Setup

For development:

```bash
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
```