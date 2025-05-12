#!/usr/bin/env python3
"""
prepdir - Utility to traverse directories and prepare file contents for review

This tool walks through directories printing relative paths and file contents,
making it easy to share code and project structures with AI assistants for
review, analysis, and improvement suggestions.
"""
import os
import argparse
import sys
import yaml
import fnmatch
from contextlib import redirect_stdout
from pathlib import Path
from importlib.metadata import version
from importlib import resources

# Add conditional import for compatibility
if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

def get_package_config():
    """Read the default config.yaml from the package or source directory."""
    try:
        # Try accessing config.yaml as a package resource (prepdir/config.yaml)
        with resources.files('prepdir').joinpath('config.yaml').open('r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback for development: try reading from source directory
        source_config = Path(__file__).parent.parent.parent / 'config.yaml'
        if source_config.exists():
            with source_config.open('r', encoding='utf-8') as f:
                return f.read()
        print(f"Error: Could not find config.yaml in package or source directory.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read package config.yaml: {str(e)}", file=sys.stderr)
        sys.exit(1)


def init_config(config_path=".prepdir/config.yaml", force=False):
    """Initialize a local config.yaml with the package's default config."""
    config_path = Path(config_path)
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    
    if config_path.exists() and not force:
        print(f"Error: '{config_path}' already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)
    
    try:
        default_config = get_package_config()
        with config_path.open('w', encoding='utf-8') as f:
            f.write(default_config)
        print(f"Created '{config_path}' with default configuration.")
    except Exception as e:
        print(f"Error: Failed to create '{config_path}': {str(e)}", file=sys.stderr)
        sys.exit(1)


def load_config(config_path=".prepdir/config.yaml"):
    """Load exclusion configuration from YAML file with precedence:
    1. Custom config specified by config_path
    2. Local .prepdir/config.yaml
    3. Global ~/.prepdir/config.yaml
    4. Default package config
    """
    # 1. Try custom config specified by config_path (if not the default)
    if config_path != ".prepdir/config.yaml":
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            return (
                config.get('exclude', {}).get('directories', []),
                config.get('exclude', {}).get('files', [])
            )
        except FileNotFoundError:
            print(f"Warning: Config file '{config_path}' not found, falling back to other configs.", file=sys.stderr)
        except yaml.YAMLError as e:
            print(f"Error: Invalid YAML in '{config_path}': {str(e)}", file=sys.stderr)
            sys.exit(1)

    # 2. Try local .prepdir/config.yaml
    local_config = Path(".prepdir/config.yaml")
    if local_config.exists():
        try:
            with local_config.open('r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            return (
                config.get('exclude', {}).get('directories', []),
                config.get('exclude', {}).get('files', [])
            )
        except yaml.YAMLError as e:
            print(f"Error: Invalid YAML in '{local_config}': {str(e)}", file=sys.stderr)
            sys.exit(1)

    # 3. Try global ~/.prepdir/config.yaml
    home_config = Path.home() / ".prepdir" / "config.yaml"
    if home_config.exists():
        try:
            with home_config.open('r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            return (
                config.get('exclude', {}).get('directories', []),
                config.get('exclude', {}).get('files', [])
            )
        except yaml.YAMLError as e:
            print(f"Error: Invalid YAML in '{home_config}': {str(e)}", file=sys.stderr)
            sys.exit(1)

    # 4. Fall back to default config.yaml from package or source
    try:
        config_content = get_package_config()
        config = yaml.safe_load(config_content) or {}
        return (
            config.get('exclude', {}).get('directories', []),
            config.get('exclude', {}).get('files', [])
        )
    except Exception as e:
        print(f"Warning: Failed to load package config.yaml: {str(e)}. Using default exclusions.", file=sys.stderr)
        return (
            ['.git', '__pycache__', '.pdm-build', '.venv', 'venv', '.idea', 'node_modules', 'dist', 'build', '.pytest_cache', '.mypy_cache', '.cache', '.eggs', '.tox', '*.egg-info'],
            ['.gitignore', 'LICENSE', '.DS_Store', 'Thumbs.db', '.env', '.env.production', '.coverage', 'coverage.xml', '.pdm-python', 'pdm.lock', '*.pyc', '*.pyo', '*.log', '*.bak', '*.swp', '**/*.log']
        )


def is_excluded_dir(dirname, root, directory, excluded_dirs):
    """Check if directory should be excluded from traversal using glob patterns."""
    relative_path = os.path.relpath(os.path.join(root, dirname), directory)
    for pattern in excluded_dirs:
        # Handle directory patterns (e.g., node_modules/, *.egg-info/)
        pattern = pattern.rstrip('/')
        if fnmatch.fnmatch(dirname, pattern) or fnmatch.fnmatch(relative_path, pattern):
            return True
    return False


def is_excluded_file(filename, root, directory, excluded_files, output_file):
    """Check if file should be excluded from traversal using glob patterns or if it's the output file."""
    # Check if the file is the output file
    full_path = os.path.abspath(os.path.join(root, filename))
    if output_file and full_path == os.path.abspath(output_file):
        return True
    
    # Check against glob patterns
    relative_path = os.path.relpath(full_path, directory)
    for pattern in excluded_files:
        if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(relative_path, pattern):
            return True
    return False


def display_file_content(file_full_path: str, directory: str):
    """Display the content of a file with appropriate header."""
    dashes = '=-' * 15 + "="

    relative_path = os.path.relpath(file_full_path, directory)

    print(f"{dashes} Begin File: '{relative_path}' {dashes}")
    
    try:
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    except UnicodeDecodeError:
        print("[Binary file or encoding not supported]")
    except Exception as e:
        print(f"[Error reading file: {str(e)}]")

    print(f"{dashes} End File: '{relative_path}' {dashes}")


def traverse_directory(directory, extensions=None, excluded_dirs=None, excluded_files=None, include_all=False, verbose=False, output_file=None):
    """
    Traverse the directory and display file contents.
    
    Args:
        directory (str): Starting directory path
        extensions (list): List of file extensions to include (without the dot)
        excluded_dirs (list): Directory glob patterns to exclude
        excluded_files (list): File glob patterns to exclude
        include_all (bool): If True, ignore exclusion lists
        verbose (bool): If True, print additional information about skipped files
        output_file (str): Path to the output file to exclude from traversal
    """
    # Convert directory to absolute path
    directory = os.path.abspath(directory)
    
    # Track if any files were found
    files_found = False
    
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories in-place, unless include_all is True
        if not include_all:
            # Identify excluded directories for logging
            skipped_dirs = [d for d in dirs if is_excluded_dir(d, root, directory, excluded_dirs)]
            if verbose:
                for d in skipped_dirs:
                    print(f"Skipping directory: {os.path.join(root, d)} (excluded in config)", file=sys.stderr)
            dirs[:] = [d for d in dirs if not is_excluded_dir(d, root, directory, excluded_dirs)]
        
        for file in files:
            # Always check if the file is the output file
            full_path = os.path.abspath(os.path.join(root, file))
            if output_file and full_path == os.path.abspath(output_file):
                if verbose:
                    print(f"Skipping file: {full_path} (output file)", file=sys.stderr)
                continue
            
            # Check if file is excluded (unless include_all is True)
            if not include_all and is_excluded_file(file, root, directory, excluded_files, output_file=None):
                if verbose:
                    print(f"Skipping file: {os.path.join(root, file)} (excluded in config)", file=sys.stderr)
                continue 
            
            # Check extension if filter is provided
            if extensions:
                file_ext = os.path.splitext(file)[1].lstrip('.')
                if file_ext not in extensions:
                    if verbose:
                        print(f"Skipping file: {os.path.join(root, file)} (extension not in {extensions})", file=sys.stderr)
                    continue
            
            # At this point we have a file to display
            files_found = True
            
            # Display file content
            full_path = os.path.join(root, file)
            display_file_content(full_path, directory)
    
    if not files_found:
        if extensions:
            print(f"No files with extension(s) {', '.join(extensions)} found.")
        else:
            print("No files found.")


def main():
    parser = argparse.ArgumentParser(
        prog='prepdir',
        description='Traverse directory and prepare file contents for review.'
    )
    parser.add_argument(
        'directory', 
        nargs='?', 
        default='.', 
        help='Directory to traverse (default: current directory)'
    )
    parser.add_argument(
        '-e', '--extensions', 
        nargs='+', 
        help='Filter files by extension(s) (without dot, e.g., "py txt")'
    )
    parser.add_argument(
        '-o', '--output',
        default='prepped_dir.txt',
        help='Output file for results (default: prepped_dir.txt)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Include all files and directories, ignoring exclusions in config.yaml'
    )
    parser.add_argument(
        '--config',
        default='.prepdir/config.yaml',
        help='Path to configuration YAML file (default: .prepdir/config.yaml in current directory)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print verbose output about skipped files and directories'
    )
    parser.add_argument(
        '--init',
        action='store_true',
        help='Initialize a local .prepdir/config.yaml with default configuration'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force overwrite of existing config file when using --init'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {version("prepdir")}',
        help='Show the version number and exit'
    )
    
    args = parser.parse_args()
    
    # Handle --init
    if args.init:
        init_config(args.config, args.force)
        sys.exit(0)
    
    # Validate directory for traversal
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Load exclusions from config, unless --all is specified
    excluded_dirs, excluded_files = ([], []) if args.all else load_config(args.config)
    
    # Prepare output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Traversing directory: {os.path.abspath(args.directory)}")
    print(f"Extensions filter: {args.extensions if args.extensions else 'None'}")
    print(f"Output file: {output_path}")
    print(f"Config file: {args.config}")
    print(f"Ignoring exclusions: {args.all}")
    print(f"Verbose mode: {args.verbose}")
    print("-" * 60)
    
    # Redirect output to file
    with output_path.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                args.directory,
                args.extensions,
                excluded_dirs,
                excluded_files,
                args.all,
                args.verbose,
                output_file=str(output_path)
            )


if __name__ == "__main__":
    main()