# Execute Script

This script is designed to gather and distribute dependencies for AWS Lambda functions. It analyzes Python files to determine their import dependencies, copying the necessary files to a specified distribution directory and generating a `requirements.txt` file for third-party dependencies.

## Overview

The main functionalities of the script include:

- **Copying files**: Ensures that files are copied from the source to the destination, creating required directories along the way.
- **Distributing modules**: Copies modules and their requirements to a specified directory.
- **Identifying module types**: Checks if modules are part of the standard library, first-party, or third-party libraries.
- **Gathering dependencies**: Recursively analyzes imports in specified Lambda functions and their dependencies.

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
