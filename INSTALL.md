Installation Guide for prepdir

## Project Structure

After setting up, your project directory should look like this:

```
prepdir/
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── README.md
├── INSTALL.md
├── tests/
│   ├── test_main.py
│   └── test_data/
│       ├── sample_project/
│       │   ├── file1.py
│       │   ├── file2.txt
│       │   ├── ignored.custom_config_file_regex_single_star
│       │   ├── logs/
│       │   │   ├── app.custom_config_file_regex_double_star
│       │   └── custom_config_dir/
│       │       ├── config
│       └── custom_config.yaml
└── src/
    └── prepdir/
        ├── __init__.py
        ├── main.py
        └── config.yaml
```

This structure follows PDM's best practices with the package inside the src directory.

## Installation Methods

### Method 1: Install with PDM (Recommended)

PDM is a modern Python package manager that this project uses.

1. Install PDM if you don't have it
   ```
   pip install pdm
   ```
2. Navigate to the directory containing pyproject.toml
   ```
   cd /path/to/prepdir
   ```
3. Install in development mode (editable)
   ```
   pdm install
   ```
4. Run the tool directly
   ```
   pdm run prepdir
   ```

### Method 2: Build and Install

To create a distributable package and install it:

1. Build the package
   ```
   pdm build
   ```
2. Install the wheel
   ```
   pip install dist/*.whl
   ```

### Method 3: Install from GitHub

```bash
pip install git+https://github.com/eyecantell/prepdir.git
```

### Method 4: Install from PyPI

```bash
pip install prepdir
```

After installation, `prepdir` can be used as a CLI tool or as a Python library (version 0.13.0 and later).

## Publishing to PyPI

If you want to share your tool with others, you can publish it to PyPI:

1. Make sure PDM is installed:
   ```
   pip install pdm
   ```
2. Build the package:
   ```
   pdm build
   ```
3. Upload to PyPI (requires PyPI credentials):
   ```
   pdm publish
   ```

## Usage after Installation

### CLI Usage

After installation, you can use the tool from the command line:

- Output all files in current directory to prepped_dir.txt (UUIDs scrubbed by default)
  ```
  prepdir
  ```
- Output to a custom file
  ```
  prepdir -o output.txt
  ```
- Filter files by extension
  ```
  prepdir -e py md
  ```
- Specify a different directory
  ```
  prepdir /path/to/directory -e py
  ```
- Include all files and directories, ignoring exclusions
  ```
  prepdir --all
  ```
- Include prepdir-generated files (excluded by default)
  ```
  prepdir --include-prepdir-files
  ```
- Disable UUID scrubbing
  ```
  prepdir --no-scrub-uuids
  ```
- Use a custom replacement UUID
  ```
  prepdir --replacement-uuid 00000000-0000-0000-0000-000000000000
  ```
- Use a custom config file
  ```
  prepdir --config custom_config.yaml
  ```
- Initialize a local config
  ```
  prepdir --init
  ```
- Enable verbose output
  ```
  prepdir -v
  ```
- Show the version number
  ```
  prepdir --version
  ```

### Programmatic Usage (Version 0.13.0+)

Use `prepdir` as a library in your Python project:

```python
from prepdir import run

# Generate content for Python files and print
content = run(
    directory="/path/to/project",
    extensions=["py"],
    verbose=True
)
print(content)

# Generate and save to a file
content = run(
    directory="/path/to/project",
    extensions=["py", "md"],
    output_file="project_review.txt",
    scrub_uuids=False
)
```

The `run()` function accepts the following parameters:
- `directory`: Directory to traverse (default: current directory).
- `extensions`: List of file extensions to include (e.g., `["py", "md"]`).
- `output_file`: Path to save output (if `None`, returns content as string).
- `include_all`: If `True`, ignore exclusion lists in config.
- `config_path`: Path to custom configuration YAML file.
- `verbose`: If `True`, log additional information about skipped files.
- `include_prepdir_files`: If `True`, include prepdir-generated files.
- `scrub_uuids`: If `True`, scrub UUIDs in file contents (default: `True`).
- `replacement_uuid`: UUID to replace detected UUIDs with (default: `"00000000-0000-0000-0000-000000000000"`).

### Sample Output

```plaintext
File listing generated 2025-06-13 09:28:00.123456 by prepdir (pip install prepdir)
Base directory is '/path/to/project'
=-=-=-=-=-=-=-= Begin File: 'src/main.py' =-=-=-=-=-=-=-=
print("Hello, World!")
=-=-=-=-=-=-=-= End File: 'src/main.py' =-=-=-=-=-=-=-=
=-=-=-=-=-=-=-= Begin File: 'README.md' =-=-=-=-=-=-=-=
# My Project
This is a sample project.
=-=-=-=-=-=-=-= End File: 'README.md' =-=-=-=-=-=-=-=
```

## Testing

To run the test suite, ensure pytest is installed (included in development dependencies):

1. Install development dependencies
   ```
   pdm install
   ```
2. Run tests
   ```
   pdm run pytest
   ```

## Configuration

Exclusions for directories and files, as well as UUID scrubbing settings, are defined in `config.yaml`, with the following precedence:

1. Custom config specified via `--config` or `config_path` (highest precedence)
2. Project config at `.prepdir/config.yaml` in your project
3. Global config at `~/.prepdir/config.yaml`
4. Default `config.yaml` included with the prepdir package (lowest precedence)

The output file (e.g., `prepped_dir.txt`) and `prepdir`-generated files are automatically excluded by default. Use `--include-prepdir-files` or `include_prepdir_files=True` to include them. UUIDs are scrubbed by default as standalone tokens; use `--no-scrub-uuids` or `scrub_uuids=False` to disable. The configuration uses .gitignore-style glob patterns for exclusions.

To initialize a project-level config with the default exclusions and UUID settings:

```
prepdir --init
```

If `.prepdir/config.yaml` already exists, use `--force` to overwrite:

```
prepdir --init --force
```

### Example config.yaml:

```yaml
EXCLUDE:
  DIRECTORIES:
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
  FILES:
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
SCRUB_UUIDS: true
REPLACEMENT_UUID: "00000000-0000-0000-0000-000000000000"
```

To use a project-level configuration, create `.prepdir/config.yaml` in your project directory:

```
prepdir --init
```

To use a global configuration, create `~/.prepdir/config.yaml`:

```
mkdir -p ~/.prepdir
echo "EXCLUDE:\n  DIRECTORIES:\n    - .git\n  FILES:\n    - *.pyc\nSCRUB_UUIDS: false\nREPLACEMENT_UUID: \"00000000-0000-0000-0000-000000000000\"" > ~/.prepdir/config.yaml
```

## Upgrading

If you previously used `config.yaml` in your project directory (versions <0.6.0), move it to `.prepdir/config.yaml`:

```
mkdir -p .prepdir
mv config.yaml .prepdir/config.yaml
```

Alternatively, specify the old path with `--config config.yaml`.

For versions <0.10.0, update configuration keys to uppercase (`EXCLUDE`, `DIRECTORIES`, `FILES`, `SCRUB_UUIDS`, `REPLACEMENT_UUID`) to comply with Dynaconf requirements.

For versions <0.12.0, add `SCRUB_UUIDS` and `REPLACEMENT_UUID` to your `config.yaml` if you wish to customize UUID scrubbing behavior. Note that UUID scrubbing now matches standalone UUIDs (with word boundaries) and file delimiters are shortened to 15 characters.

For versions <0.13.0, note the addition of the `run()` function for programmatic use, allowing `prepdir` to be imported as a library.

## Development Setup

For development:

1. Clone the repository
   ```
   git clone https://github.com/eyecantell/prepdir.git
   cd prepdir
   ```
2. Install with PDM in development mode
   ```
   pdm install
   ```
3. Run the development version
   ```
   pdm run prepdir
   ```
4. Add dependencies if needed
   ```
   pdm add some-package
   ```
5. Add development dependencies
   ```
   pdm add -d pytest
   ```

## Continuous Integration

This project uses GitHub Actions for continuous integration. The CI workflow runs the test suite on every push and pull request to the main branch, testing across multiple Python versions (3.8, 3.9, 3.10, 3.11). The workflow is defined in `.github/workflows/ci.yml`.

## License

MIT