Installation Guide for prepdirProject StructureAfter setting up, your project directory should look like this:prepdir/├── .github/│   └── workflows/│       └── ci.yml├── pyproject.toml├── README.md├── INSTALL.md├── tests/│   ├── test_main.py│   └── test_data/│       ├── sample_project/│       │   ├── file1.py│       │   ├── file2.txt│       │   ├── ignored.custom_config_file_regex_single_star│       │   ├── logs/│       │   │   ├── app.custom_config_file_regex_double_star│       │   └── custom_config_dir/│       │       ├── config│       └── custom_config.yaml└── src/    └── prepdir/        ├── init.py        ├── main.py        └── config.yamlThis structure follows PDM's best practices with the package inside the src directory.Installation MethodsMethod 1: Install with PDM (Recommended)PDM is a modern Python package manager that this project uses.
Install PDM if you don't have it
pip install pdm
Navigate to the directory containing pyproject.toml
cd /path/to/prepdir
Install in development mode (editable)
pdm install
Run the tool directly
pdm run prepdir
Method 2: Build and InstallTo create a distributable package and install it:
Build the package
pdm build
Install the wheel
pip install dist/*.whl
Method 3: Install from GitHubpip install git+https://github.com/eyecantell/prepdir.git
Method 4: Install from PyPIpip install prepdir
Publishing to PyPIIf you want to share your tool with others, you can publish it to PyPI:Make sure PDM is installed:pip install pdm
Build the package:pdm build
Upload to PyPI (requires PyPI credentials):pdm publish
Usage after InstallationAfter installation, you can use the tool from anywhere:
Output all files in current directory to prepped_dir.txt
prepdir
Output to a custom file
prepdir -o output.txt
Filter files by extension
prepdir -e py md
Specify a different directory
prepdir /path/to/directory -e py
Include all files and directories, ignoring exclusions
prepdir --all
Use a custom config file
prepdir --config custom_config.yaml
Initialize a local config
prepdir --init
Enable verbose output
prepdir -v
Show the version number
prepdir --version
TestingTo run the test suite, ensure pytest is installed (included in development dependencies):
Install development dependencies
pdm install
Run tests
pdm run pytest
ConfigurationExclusions for directories and files are defined in config.yaml, with the following precedence:
Custom config specified via --config (highest precedence)Project config at .prepdir/config.yaml in your projectGlobal config at ~/.prepdir/config.yamlDefault config.yaml included with the prepdir package (lowest precedence)
The output file (e.g., prepped_dir.txt) is automatically excluded. The configuration uses .gitignore-style glob patterns.To initialize a project-level config with the default exclusions:prepdir --init
If .prepdir/config.yaml already exists, use --force to overwrite:prepdir --init --force
Example config.yaml:exclude:  directories:    - .git    - pycache    - .pdm-build    - .venv    - venv    - .idea    - node_modules    - dist    - build    - .pytest_cache    - .mypy_cache    - .cache    - .eggs    - .tox    - ".egg-info"  files:    - .gitignore    - LICENSE    - .DS_Store    - Thumbs.db    - .env    - .coverage    - coverage.xml    - .pdm-python    - ".pyc"    - ".pyo"    - ".log"    - ".bak"    - ".swp"    - "**/*.log"
To use a project-level configuration, create .prepdir/config.yaml in your project directory:prepdir --init
To use a global configuration, create ~/.prepdir/config.yaml:mkdir -p ~/.prepdirecho "exclude:\n  directories:\n    - .git\n  files:\n    - *.pyc" > ~/.prepdir/config.yaml
UpgradingIf you previously used config.yaml in your project directory (versions <0.6.0), move it to .prepdir/config.yaml:mkdir -p .prepdirmv config.yaml .prepdir/config.yaml
Alternatively, specify the old path with --config config.yaml.Development SetupFor development:
Clone the repository
git clone https://github.com/eyecantell/prepdir.gitcd prepdir
Install with PDM in development mode
pdm install
Run the development version
pdm run prepdir
Add dependencies if needed
pdm add some-package
Add development dependencies
pdm add -d pytest
Continuous IntegrationThis project uses GitHub Actions for continuous integration. The CI workflow runs the test suite on every push and pull request to the main branch, testing across multiple Python versions (3.8, 3.9, 3.10, 3.11). The workflow is defined in .github/workflows/ci.yml.LicenseMIT
