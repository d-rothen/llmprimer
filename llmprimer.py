#!/usr/bin/env python3

import os
import json
import inquirer
import pathspec
from pathlib import Path

# --- Configuration ---
# The name of the directory where the output and local config will be stored.
CONTEXT_DIR_NAME = "LLMContext"
# The name of the final output file.
DUMP_FILE_NAME = "repository_dump.txt"
# The name of the local configuration file.
LOCAL_CONFIG_NAME = "config.json"
# The name of the global configuration file, expected to be next to the script.
GLOBAL_CONFIG_NAME = "config.json"
# Directories to always exclude from the search.
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
            return json.load(f), False # Not global
    elif global_config_path.exists():
        print(f"Using global configuration from: {global_config_path}")
        with open(global_config_path, 'r', encoding='utf-8') as f:
            return json.load(f), True # Is global
    else:
        print("Error: No local or global config.json found.")
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
    return None

def main():
    """
    Main function to run the context building process.
    """
    # --- 1. Setup Paths and Configurations ---
    cwd = Path.cwd()
    script_dir = find_script_directory()
    context_dir = cwd / CONTEXT_DIR_NAME

    config_data, is_global_config = load_config(cwd, script_dir)
    if not config_data:
        return

    language_config = None
    if is_global_config:
        # If we loaded the global config, user needs to pick a language
        selected_language = select_language_config(config_data)
        if not selected_language:
            print("No language selected. Exiting.")
            return
        language_config = config_data[selected_language]
        
        # Create context directory and save the selected language config locally
        context_dir.mkdir(exist_ok=True)
        local_config_path = context_dir / LOCAL_CONFIG_NAME
        with open(local_config_path, 'w', encoding='utf-8') as f:
            json.dump(language_config, f, indent=4)
        print(f"Saved configuration for '{selected_language}' to {local_config_path}")
    else:
        # The loaded config is already the specific local one
        language_config = config_data

    if 'extensions' not in language_config or not language_config['extensions']:
        print("Error: The selected configuration has no 'extensions' defined.")
        return

    target_extensions = set(language_config['extensions'])
    gitignore_spec = get_gitignore_spec(cwd)
    output_file_path = context_dir / DUMP_FILE_NAME
    
    # Ensure context directory exists before writing the dump file
    context_dir.mkdir(exist_ok=True)

    # --- 2. Walk through directories and build the context file ---
    print(f"Starting to process files with extensions: {', '.join(target_extensions)}")
    print(f"Output will be saved to: {output_file_path}")

    file_count = 0
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        # We use os.walk to get directories, which we can then filter.
        for root, dirs, files in os.walk(cwd, topdown=True):
            current_root_path = Path(root)
            
            # Filter out excluded directories
            # We modify 'dirs' in-place to prevent os.walk from traversing them
            excluded_dirs = DEFAULT_EXCLUDED_DIRS.union({CONTEXT_DIR_NAME})
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            # Further filter directories based on .gitignore
            if gitignore_spec:
                 dirs[:] = [d for d in dirs if not gitignore_spec.match_file(str(current_root_path / d) + '/')]

            for filename in files:
                file_path = current_root_path / filename
                
                # Check if the file itself is ignored
                if gitignore_spec and gitignore_spec.match_file(str(file_path)):
                    continue

                # Check if the file has one of the target extensions
                if file_path.suffix in target_extensions:
                    relative_path = file_path.relative_to(cwd)
                    print(f"  Adding: {relative_path}")
                    file_count += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            content = infile.read()
                            outfile.write(f"--- File: {str(relative_path).replace('\\', '/')} ---\n\n")
                            outfile.write(content)
                            outfile.write("\n\n")
                    except Exception as e:
                        print(f"    - Could not read file {relative_path}: {e}")

    print("-" * 50)
    print(f"Processing complete.")
    print(f"Total files added to context: {file_count}")
    print(f"Repository dump created at: {output_file_path}")
    print("-" * 50)


if __name__ == '__main__':
    try:
        # Install dependencies if they are missing
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
