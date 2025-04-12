# Execute Script

This script is designed to gather and distribute dependencies for AWS Lambda functions. It analyzes Python files to determine their import dependencies, copying the necessary files to a specified distribution directory and generating a `requirements.txt` file for third-party dependencies.

## Overview

The main functionalities of the script include:

- **Copying files**: Ensures that files are copied from the source to the destination, creating required directories along the way.
- **Distributing modules**: Copies modules and their requirements to a specified directory.
- **Identifying module types**: Checks if modules are part of the standard library, first-party, or third-party libraries.
- **Gathering dependencies**: Recursively analyzes imports in specified Lambda functions and their dependencies.

## Functions

`copy_file(src: str, dest: str) -> None`

Copies a file from a source to a destination, creating destination directories if necessary.

`distribute_modules(imports: Set[str], requirements: Set[str], src_dir: str, dist_dir: str) -> None`

Distributes modules and their requirements to a specified destination directory. It creates a `requirements.txt` file containing third-party dependencies.

`is_standard_lib(module_name: str, std_lib_modules: Set[str]) -> bool`

Checks if a module is part of Python's standard library.

`is_third_party(module_name: str, package_paths: Set[str]) -> bool`

Determines if a module is part of a third-party package.

`is_first_party(module_name: str, current_dir: str) -> bool`

Checks if a module is part of the first-party library.

`get_package_paths() -> Set[str]`

Retrieves paths to directories containing installed third-party packages.

`parse_imports(file_path: str, std_lib_modules: Set[str], package_paths: Set[str], current_dir: str) -> tuple[Set[str], Set[str]]`

Parses a Python file to extract its import dependencies.

`gather_dependencies() -> None`

Main function that orchestrates the gathering and distribution of dependencies for Lambda functions.

## Usage

To run the script, simply execute it in your terminal:

```bash
python script/execute.py
```

Make sure to have the necessary permissions and the environment set up for executing Lambda functions.

## Directory Structure

- `script/execute.py`: The main script file.
- `src/lambdas`: Directory containing the Lambda function source files.
- `dist`: Directory where the dependencies will be copied to.
- `requirements.txt`: Generated file containing third-party package requirements.

## Requirements

Ensure you have Python installed, and that your environment is set up for AWS Lambda development.

## Author

ykamata
