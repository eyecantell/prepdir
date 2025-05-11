# prepdir

A simple utility that prepares your code project for sharing with AI assistants by automatically formatting file contents with clear separation between files.

## Quick Start

```bash
# Install from PyPI
pip install prepdir

# Run in your project directory
prepdir

# View the generated prepped_dir.txt file
```

That's it! The tool creates a `prepped_dir.txt` file containing all your project files, neatly formatted for sharing.

## Why Use prepdir?

When asking AI assistants for help with your code, providing proper context is crucial. prepdir automatically:

* Creates a single text file with all your project's code
* Adds clear separators between files
* Shows relative file paths
* Skips irrelevant files (like `.git` directories)
* Makes it easy to copy-paste into AI chats

## Basic Usage

```bash
# Generate a file with all project files
prepdir

# Only include Python and Markdown files
prepdir -e py md

# Process a different directory
prepdir /path/to/your/project

# Custom output file name
prepdir -o my_project_files.txt
```

## Options

```
prepdir [DIRECTORY] [OPTIONS]

Arguments:
  DIRECTORY              Directory to process (default: current directory)

Options:
  -e, --extensions       Filter by file extensions (e.g., py js md)
  -o, --output FILE      Output file name (default: prepped_dir.txt)
  --all                  Include all files (ignore exclusion rules)
  --config FILE          Use a custom config file
  -v, --verbose          Show detailed logs of skipped files
  --version              Show version number
  --help                 Show this help message
```

## Configuration

By default, prepdir skips common files and directories you wouldn't want to share, like:
- Version control directories (`.git`)
- Cache directories (`__pycache__`, `.pytest_cache`)
- Build artifacts (`dist`, `build`)
- Environment directories (`.venv`, `venv`)
- Log and temporary files (`*.log`, `*.pyc`)

You can customize these exclusions in three ways:

1. **Global config**: Create `~/.prepdir/config.yaml`
2. **Project config**: Add `config.yaml` in your project directory
3. **Custom config**: Use `--config custom_config.yaml`

Example config.yaml:
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

## Examples

```bash
# Create project_files.txt with only Python files
prepdir -o project_files.txt -e py

# Process a specific directory, include all files
prepdir /path/to/directory --all

# Use a custom config with verbose logging
prepdir --config custom_config.yaml -v
```

## Use Cases

- **AI Code Review**: Easily share your codebase with AI assistants
- **Project Analysis**: Get comprehensive views of your project structure
- **Bug Hunting**: Provide full context when asking for debugging help
- **Knowledge Transfer**: Help AI understand your project quickly

## Installation

```bash
# Install from PyPI
pip install prepdir

# Or install from GitHub
pip install git+https://github.com/eyecantell/prepdir.git
```

## For Developers

### Development Setup

This project uses PDM for dependency management and packaging:

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

# Install the wheel locally
pip install dist/*.whl

# Publish to PyPI (requires credentials)
pdm publish
```

### Testing

```bash
# Run the test suite
pdm run pytest
```

## License

MIT