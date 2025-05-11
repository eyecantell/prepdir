# prepdir

A utility to traverse directories and prepare file contents, designed specifically for sharing code projects with AI assistants for review and analysis.

## Features

- Recursively walks through directories
- Displays relative paths and file contents
- Skips `.git` and `__pycache__` directories
- Filters files by extension
- Easy-to-use command-line interface
- Perfect for sending code to AI assistants for review

## Installation

### Using PDM (recommended)

```bash
# Install PDM if you don't already have it
pip install pdm

# Install in development mode
pdm install

# Install for system-wide use
pdm build
pip install dist/*.whl
```

### Using pip

```bash
# Install from PyPI (once published)
pip install prepdir

# Install from GitHub
pip install git+https://github.com/eyecantell/prepdir.git
```

## Usage

```bash
# Show all files in current directory
prepdir

# Show all files in specified directory
prepdir /path/to/directory

# Only show Python files
prepdir -e py

# Show Python and Markdown files
prepdir -e py md

# Specific directory and extensions
prepdir /path/to/directory -e py md
```

## Use Cases

1. **AI Code Review**: Easily prepare your entire codebase for AI assistants
2. **Project Analysis**: Get a comprehensive view of project structure and content
3. **Knowledge Transfer**: Help AI understand your project context quickly
4. **Bug Hunting**: Provide full context when asking for debugging help

## Development

This project uses [PDM](https://pdm.fming.dev/) for dependency management and packaging.

```bash
# Clone the repository
git clone https://github.com/eyecantell/prepdir.git
cd prepdir

# Install development dependencies
pdm install

# Run in development mode
pdm run prepdir
```

## License

MIT