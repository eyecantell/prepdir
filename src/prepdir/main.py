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
from contextlib import redirect_stdout
from pathlib import Path


def load_config(config_path="config.yaml"):
    """Load exclusion configuration from YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        return (
            config.get('exclude', {}).get('directories', []),
            config.get('exclude', {}).get('files', [])
        )
    except FileNotFoundError:
        print(f"Warning: Config file '{config_path}' not found. Using defaults.")
        return ['.git', '__pycache__', '.pdm-build'], ['.gitignore', 'LICENSE']
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in '{config_path}': {str(e)}")
        sys.exit(1)


def is_excluded_dir(dirname, excluded_dirs):
    """Check if directory should be excluded from traversal."""
    return dirname in excluded_dirs


def is_excluded_file(filename, excluded_files):
    """Check if file should be excluded from traversal."""
    return filename in excluded_files


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


def traverse_directory(directory, extensions=None, excluded_dirs=None, excluded_files=None):
    """
    Traverse the directory and display file contents.
    
    Args:
        directory (str): Starting directory path
        extensions (list): List of file extensions to include (without the dot)
        excluded_dirs (list): Directories to exclude
        excluded_files (list): Files to exclude
    """
    # Convert directory to absolute path
    directory = os.path.abspath(directory)
    
    # Track if any files were found
    files_found = False
    
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories in-place
        dirs[:] = [d for d in dirs if not is_excluded_dir(d, excluded_dirs)]
        
        for file in files:
            if is_excluded_file(file, excluded_files):
                continue 
            
            # Check extension if filter is provided
            if extensions:
                file_ext = os.path.splitext(file)[1].lstrip('.')
                if file_ext not in extensions:
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
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        sys.exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.")
        sys.exit(1)
    
    # Load exclusions from config
    excluded_dirs, excluded_files = load_config()
    
    # Prepare output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Traversing directory: {os.path.abspath(args.directory)}")
    print(f"Extensions filter: {args.extensions if args.extensions else 'None'}")
    print(f"Output file: {output_path}")
    print("-" * 60)
    
    # Redirect output to file
    with output_path.open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            traverse_directory(
                args.directory,
                args.extensions,
                excluded_dirs,
                excluded_files
            )


if __name__ == "__main__":
    main()