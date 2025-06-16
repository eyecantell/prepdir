# Installation Guide for prepdir

This document provides instructions for installing `prepdir` version 0.13.0, a lightweight CLI and library utility for preparing code projects for AI assistants.

## 📋 Prerequisites

- **Python**: Version 3.8 or higher. Check with:
  ```bash
  python --version
  ```
- **pip**: Ensure `pip` is installed for your Python version:
  ```bash
  python -m ensurepip --upgrade
  python -m pip install --upgrade pip
  ```
- **Operating System**: Compatible with Windows, macOS, or Linux.
- **Optional for Development**:
  - `pdm` for dependency management and development tasks:
    ```bash
    pip install pdm
    ```
  - Git for cloning the repository.

## 📦 Installation Methods

### 1. **Using pip (Recommended)**

Install `prepdir` directly from PyPI for the latest stable release (0.13.0):

```bash
pip install prepdir
```

Verify the installation:

```bash
prepdir --version
# Should output: prepdir, version 0.13.0
```

This method is ideal for most users, providing access to both the CLI (`prepdir`) and programmatic usage (`from prepdir import run, validate_output_file`).

### 2. **From GitHub**

Install the latest version directly from the GitHub repository for access to the most recent updates:

```bash
pip install git+https://github.com/eyecantell/prepdir.git
```

Verify the installation:

```bash
prepdir --version
```

This method is useful for users who want the latest commits, including potential pre-release features.

### 3. **From Source**

For development or customization, install `prepdir` from the source code:

```bash
# Clone the repository
git clone https://github.com/eyecantell/prepdir.git
cd prepdir

# Install dependencies and prepdir in editable mode
pip install -e .
```

Alternatively, use `pdm` for dependency management:

```bash
# Install pdm if not already installed
pip install pdm

# Install dependencies
pdm install
```

Verify the installation:

```bash
pdm run prepdir --version
# Should output: prepdir, version 0.13.0
```

This method allows you to modify the source code and run tests.

## 🔧 Post-Installation Setup

### **Verify Installation**

Run the following to confirm `prepdir` is installed correctly:

```bash
prepdir --version
```

If the command is not found, ensure your Python environment’s `bin` directory is in your system’s `PATH`. For example, on Unix-like systems:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### **Programmatic Usage**

To use `prepdir` as a library (new in 0.13.0), ensure it’s installed and import it in your Python code:

```python
from prepdir import run, validate_output_file

content = run(directory=".", extensions=["py"])
print(content)
```

### **Configuration**

`prepdir` uses a default configuration but supports custom settings. To create a local configuration file:

```bash
prepdir --init
```

This creates `.prepdir/config.yaml` in your project directory. See [README.md](README.md) for configuration details, including UUID scrubbing and file exclusion options.

### **Logging**

Set the logging level for debugging (new in 0.13.0):

```bash
LOGLEVEL=DEBUG prepdir
```

Valid `LOGLEVEL` values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

## 🛠️ Development Setup

For contributing to `prepdir`:

1. Clone the repository:

   ```bash
   git clone https://github.com/eyecantell/prepdir.git
   cd prepdir
   ```

2. Install dependencies with `pdm`:

   ```bash
   pdm install
   ```

3. Run tests to verify the setup:

   ```bash
   pdm run pytest
   ```

4. Run the development version:

   ```bash
   pdm run prepdir
   ```

5. Publish to PyPI (maintainers only, requires credentials):

   ```bash
   pdm publish
   ```

## 🚫 Troubleshooting

- **Command not found**: Ensure `pip install prepdir` was run in the correct Python environment and that the `bin` directory is in your `PATH`.
- **Permission errors**: Use `pip install --user prepdir` or a virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  pip install prepdir
  ```
- **Python version errors**: Verify Python 3.8+ with `python --version`. Upgrade if needed:
  ```bash
  sudo apt-get install python3.8  # Example for Ubuntu
  ```
- **pdm errors**: Ensure `pdm` is installed (`pip install pdm`) and run `pdm install` in the project directory.
- **Missing dependencies**: Run `pip install --upgrade pip` and retry installation.

For further issues, check the [README.md](README.md#common-issues) or file an issue on [GitHub](https://github.com/eyecantell/prepdir/issues).

## 🔗 Resources

- [README.md](README.md) for usage and configuration details.
- [CHANGELOG.md](docs/CHANGELOG.md) for version history.
- [GitHub Repository](https://github.com/eyecantell/prepdir)
- [PyPI](https://pypi.org/project/prepdir/)