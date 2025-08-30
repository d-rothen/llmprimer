#!/usr/bin/env python

import os
import json
import inquirer
import pathspec
from pathlib import Path

# --- Configuration ---
CONTEXT_DIR_NAME = ".LLMContext"
DUMP_FILE_NAME = "repository_dump.txt"
LOCAL_CONFIG_NAME = "config.json"
GLOBAL_CONFIG_NAME = "config.json"
DEFAULT_EXCLUDED_DIRS = {'.git', '.idea', '__pycache__', 'node_modules', '.venv', 'venv'}

def find_script_directory():
    """Finds the directory where the script is located."""
    return Path(__file__).parent.resolve()

def load_config(cwd, script_dir):
    """
    Loads configuration, prioritizing local over global.
    Returns the config data and a boolean indicating if it was the global config.
    """
    local_config_path = cwd / CONTEXT_DIR_NAME / LOCAL_CONFIG_NAME
    global_config_path = script_dir / GLOBAL_CONFIG_NAME

    if local_config_path.exists():
        print(f"Found local configuration at: {local_config_path}")
        with open(local_config_path, 'r', encoding='utf-8') as f:
            return json.load(f), False
    elif global_config_path.exists():
        print(f"Using global configuration from: {global_config_path}")
        with open(global_config_path, 'r', encoding='utf-8') as f:
            return json.load(f), True
    else:
        print(f"Error: No local or global '{GLOBAL_CONFIG_NAME}' found.")
        print(f"Please create a '{GLOBAL_CONFIG_NAME}' file in the script's directory: {script_dir}")
        return None, False

def select_language_config(full_config):
    """
    Prompts the user to select a programming language from the configuration.
    Returns the key of the selected language.
    """
    languages = list(full_config.keys())
    if not languages:
        print("Error: The configuration file contains no language definitions.")
        return None

    questions = [
        inquirer.List('language',
                      message="Select the programming language of the repository",
                      choices=languages,
                      ),
    ]
    answers = inquirer.prompt(questions)
    return answers['language'] if answers else None

def get_gitignore_spec(cwd):
    """
    Finds the .gitignore file in the CWD and returns a PathSpec object.
    """
    gitignore_path = cwd / '.gitignore'
    if gitignore_path.exists():
        print(f"Found .gitignore at: {gitignore_path}")
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    print("No .gitignore found in the current directory.")
    return None

def generate_file_tree(file_paths):
    """Generates a string representation of a file tree."""
    tree = {}
    for path in file_paths:
        parts = path.parts
        current_level = tree
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]

    tree_lines = []
    def build_tree_lines(d, prefix=""):
        # Sort items to ensure consistent order (files before dirs)
        items = sorted(d.keys(), key=lambda k: (len(d[k]) > 0, k))
        for i, name in enumerate(items):
            connector = "├── " if i < len(items) - 1 else "└── "
            tree_lines.append(f"{prefix}{connector}{name}")
            if d[name]:  # It's a directory
                extension = "│   " if i < len(items) - 1 else "    "
                build_tree_lines(d[name], prefix + extension)

    build_tree_lines(tree)
    return "\n".join(tree_lines)

def main():
    """Main function to run the context building process."""
    cwd = Path.cwd()
    script_dir = find_script_directory()
    context_dir = cwd / CONTEXT_DIR_NAME

    config_data, is_global_config = load_config(cwd, script_dir)
    if not config_data:
        return

    language_config = None
    if is_global_config:
        selected_language = select_language_config(config_data)
        if not selected_language:
            print("No language selected. Exiting.")
            return
        language_config = config_data[selected_language]
        context_dir.mkdir(exist_ok=True)
        local_config_path = context_dir / LOCAL_CONFIG_NAME
        with open(local_config_path, 'w', encoding='utf-8') as f:
            json.dump(language_config, f, indent=4)
        print(f"Saved configuration for '{selected_language}' to {local_config_path}")
    else:
        language_config = config_data

    if 'extensions' not in language_config or not language_config['extensions']:
        print("Error: The selected configuration has no 'extensions' defined.")
        return

    target_extensions = set(language_config['extensions'])
    gitignore_spec = get_gitignore_spec(cwd)
    output_file_path = context_dir / DUMP_FILE_NAME

    # --- 1. First Pass: Collect all files to be included ---
    print("\nScanning for relevant files...")
    files_to_include = []
    for root, dirs, files in os.walk(cwd, topdown=True):
        current_root_path = Path(root)
        
        excluded_dirs = DEFAULT_EXCLUDED_DIRS.union({CONTEXT_DIR_NAME})
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        if gitignore_spec:
            dirs[:] = [d for d in dirs if not gitignore_spec.match_file(str(current_root_path / d) + '/')]

        for filename in files:
            file_path = current_root_path / filename
            if gitignore_spec and gitignore_spec.match_file(str(file_path)):
                continue
            if file_path.suffix in target_extensions:
                files_to_include.append(file_path.relative_to(cwd))
    
    files_to_include.sort()
    
    if not files_to_include:
        print("No files found matching the criteria. Nothing to do.")
        return

    # --- 2. Generate file tree and write everything to the output file ---
    print(f"Found {len(files_to_include)} files. Generating context file...")
    context_dir.mkdir(exist_ok=True)
    
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        # Write the file tree header
        outfile.write("Project Structure:\n\n")
        tree_string = generate_file_tree(files_to_include)
        outfile.write(tree_string)
        outfile.write(f"\n\n{'='*80}\n\n")

        # Write the content of each file
        for relative_path in files_to_include:
            print(f"  Adding: {relative_path}")
            full_path = cwd / relative_path
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as infile:
                    content = infile.read()
                    posix_path = str(relative_path).replace("\\", "/")
                    outfile.write(f"--- File: {posix_path} ---\n\n")
                    outfile.write(content)
                    outfile.write("\n\n")
            except Exception as e:
                print(f"    - Could not read file {relative_path}: {e}")

    print("-" * 50)
    print(f"Processing complete.")
    print(f"Total files added to context: {len(files_to_include)}")
    print(f"Repository dump created at: {output_file_path}")
    print("-" * 50)

if __name__ == '__main__':
    try:
        try:
            import inquirer
            import pathspec
        except ImportError:
            print("One or more required packages are not installed.")
            response = input("Do you want to install 'inquirer' and 'pathspec'? (y/n): ")
            if response.lower() == 'y':
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "inquirer", "pathspec"])
                print("Packages installed successfully. Please run the script again.")
            else:
                print("Please install the required packages to run the script.")
            exit()
        
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting.")

