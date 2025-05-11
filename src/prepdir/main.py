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


def is_excluded_dir(dirname):
    """Check if directory should be excluded from traversal."""
    excluded = ['.git', '__pycache__', '.pdm-build']
    return dirname in excluded

def is_excluded_file(filename):
    """Check if directory should be excluded from traversal."""
    excluded = ['.gitignore', 'LICENSE']
    return filename in excluded


def display_file_content(file_full_path : str, directory: str):
    """Display the content of a file with appropriate header."""
    dashes = '=-' * 15 + "="

    relative_path = os.path.relpath(file_full_path, directory)

    print(f"{dashes} Begin File: '{relative_path}' {dashes}")
    
    try:
        with open(relative_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    except UnicodeDecodeError:
        print("[Binary file or encoding not supported]")
    except Exception as e:
        print(f"[Error reading file: {str(e)}]")

    print(f"{dashes} End File: '{relative_path}' {dashes}")


def traverse_directory(directory, extensions=None):
    """
    Traverse the directory and display file contents.
    
    Args:
        directory (str): Starting directory path
        extensions (list): List of file extensions to include (without the dot)
    """
    # Convert directory to absolute path
    directory = os.path.abspath(directory)
    
    # Track if any files were found
    files_found = False
    
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories in-place
        dirs[:] = [d for d in dirs if not is_excluded_dir(d)]
        
        for file in files:

            if is_excluded_file(file):
                continue 
            
            # Check extension if filter is provided
            if extensions:
                file_ext = os.path.splitext(file)[1].lstrip('.')
                if file_ext not in extensions:
                    continue
            
            # At this point we have a file to display
            files_found = True
            #print(f"Found: {relative_path}")
            
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
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        sys.exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.")
        sys.exit(1)
    
    print(f"Traversing directory: {os.path.abspath(args.directory)}")
    print(f"Extensions filter: {args.extensions if args.extensions else 'None'}")
    print("-" * 60)
    
    traverse_directory(args.directory, args.extensions)


if __name__ == "__main__":
    main()