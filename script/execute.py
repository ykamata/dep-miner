import ast
import importlib
import importlib.util
import os
import shutil
import sys
from typing import Set


def copy_file(src: str, dest: str) -> None:
    """
    Copy a file from source to destination, creating destination directories if needed.

    Args:
        src (str): Source file path to copy from
        dest (str): Destination file path to copy to

    Returns:
        None

    This function:
    1. Creates any missing parent directories for the destination path
    2. Copies the file while preserving metadata (timestamps, permissions)
    """
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)


def distribute_modules(
    imports: Set[str], requirements: Set[str], src_dir: str, dist_dir: str
) -> None:
    """
    Distribute modules and their requirements to a destination directory.

    Args:
        imports (Set[str]): Set of module import paths to copy
        requirements (Set[str]): Set of third-party package requirements
        src_dir (str): Source directory containing modules
        dist_dir (str): Destination directory to copy modules to

    Returns:
        None

    This function:
    1. Creates the destination directory if it doesn't exist
    2. Copies each imported module from source to destination, preserving directory structure
    3. Creates a requirements.txt file listing all third-party dependencies
    """
    os.makedirs(dist_dir, exist_ok=True)
    for module in imports:
        module_path = os.path.join(src_dir, f"{module.replace('.', os.sep)}.py")
        if os.path.exists(module_path):
            copy_file(
                module_path,
                os.path.join(
                    dist_dir,
                    f"{module.replace('.', os.sep)}.py",
                ),
            )

    requirements_txt = os.path.join(dist_dir, "requirements.txt")
    with open(requirements_txt, "w") as f:
        for m in requirements:
            f.write(m + "\n")


def is_standard_lib(module_name: str, std_lib_modules: Set[str]) -> bool:
    """
    Check if a module is part of the Python standard library.

    Args:
        module_name (str): Name of the module to check
        std_lib_modules (Set[str]): Set of standard library module names

    Returns:
        bool: True if module is part of standard library, False otherwise

    This function checks if a given module is part of Python's standard library by:
    1. Checking if it exists in the provided std_lib_modules set
    2. Finding the module spec and checking if its origin path is within the standard library directory
    3. Returns False if module spec cannot be found or has no origin path
    """
    if module_name in std_lib_modules:
        return True

    module_spec = importlib.util.find_spec(module_name)
    if module_spec is None:
        return False

    module_path = module_spec.origin
    if module_path is None:
        return False

    # 標準ライブラリのディレクトリを取得
    std_lib_path = os.path.dirname(os.__file__)
    return module_path.startswith(std_lib_path)


def is_third_party(module_name: str, package_paths: Set[str]) -> bool:
    """
    Check if a module is from a third-party package.

    Args:
        module_name (str): Name of the module to check
        package_paths (Set[str]): Set of paths to third party package directories

    Returns:
        bool: True if module is a third party package, False otherwise

    This function checks if a given module is from a third party package by:
    1. Attempting to import the module
    2. Checking if its file path starts with any of the provided package paths
    3. Returns False if module cannot be imported or has no file path
    """
    try:
        module = importlib.import_module(module_name)
        return module.__file__.startswith(tuple(package_paths))
    except ImportError:
        return False


def is_namespace_package(module_name: str) -> bool:
    """
    Check if a module is a namespace package.

    Args:
        module_name (str): Name of the module to check

    Returns:
        bool: True if module is a namespace package, False otherwise

    This function determines if a module is a namespace package by:
    1. Attempting to import the module
    2. Checking if it has a __path__ attribute (indicating a package)
    3. Checking if it lacks a __file__ attribute (indicating namespace package)
    4. Returns False if module cannot be imported
    """
    try:
        module = importlib.import_module(module_name)
        return hasattr(module, "__path__") and not hasattr(module, "__file__")
    except ImportError:
        return False


def is_first_party(module_name: str, current_dir: str) -> bool:
    """
    Check if a module is a first-party (local project) module.

    Args:
        module_name (str): Name of the module to check
        current_dir (str): Current working directory path

    Returns:
        bool: True if module is a first party module, False otherwise

    This function determines if a module is a first party module by checking:
    1. If the module can be imported successfully
    2. If the module has a valid file path
    3. If the module is not in a virtual environment (.venv, venv, etc)
    4. If the module is not a pip editable install
    5. If the module file path starts with the current directory
    6. Handles special cases for:
        - Zip imports
        - Compiled extensions (.pyd, .so files)
        - Namespace packages
        - Frozen modules
    """
    try:
        module = importlib.import_module(module_name)
        module_file = getattr(module, "__file__", None)

        # Skip if module doesn't have a file path
        if module_file is None:
            return False

        # Handle zip imports
        if module_file and ".zip" in module_file:
            zip_path = module_file.split(".zip")[0] + ".zip"
            return zip_path.startswith(current_dir)

        # Handle compiled extensions (.pyd, .so files)
        if module_file.endswith((".pyd", ".so")):
            return module_file.startswith(current_dir)

        # Handle namespace packages
        if is_namespace_package(module_name):
            return any(path.startswith(current_dir) for path in module.__path__)

        # Handle frozen modules
        if hasattr(module, "__spec__") and module.__spec__.origin == "frozen":
            return False

        # Check for common virtual environment patterns
        if any(
            pattern in module_file
            for pattern in [
                ".venv",
                "venv",
                "virtualenv",
                "poetry/virtualenvs",
                "conda",
                "env",
                "envs",
                ".tox",  # For tox testing environments
            ]
        ):
            return False

        # Check for pip editable installs
        if ".egg-link" in module_file:
            return False

        return module_file.startswith(current_dir)
    except ImportError:
        return False


def get_package_paths() -> Set[str]:
    """
    Get paths to all third-party package installation directories.

    Returns:
        Set[str]: Set of paths to directories containing installed packages

    This function:
    1. Iterates through Python's sys.path
    2. Collects paths containing:
        - site-packages: System-wide installed packages
        - dist-packages: Distribution-specific packages
        - .local/lib/python: User-installed packages on Unix systems
        - AppData/Local/Programs/Python: User-installed packages on Windows
        - Library/Python: User-installed packages on macOS
    3. Returns a set of all package installation directories found
    """
    paths = set()
    for path in sys.path:
        # if "site-packages" in path or "dist-packages" in path:
        if any(
            pattern in path
            for pattern in [
                "site-packages",
                "dist-packages",
                ".local/lib/python",  # User-installed packages on Unix-like systems
                "AppData/Local/Programs/Python",  # User-installed packages on Windows
                "Library/Python",  # macOS user packages
            ]
        ):
            paths.add(path)
    return paths


def _handle_import_from(
    module: str,
    std_lib_modules: Set[str],
    current_dir: str,
    package_paths: Set[str],
) -> tuple[set, set]:
    """
    Process an ImportFrom AST node to classify the imported module.

    Args:
        module (str): Name of the imported module
        std_lib_modules (Set[str]): Set of standard library module names
        current_dir (str): Current working directory path
        package_paths (Set[str]): Set of paths to third party package directories

    Returns:
        tuple[set, set]: Tuple containing:
            - Set of first party module imports
            - Set of third party package requirements

    This function processes an ImportFrom AST node by:
    1. Checking if module name is empty
    2. Determining module type:
        - Standard library module (ignored)
        - First party module (added to imports set)
        - Third party package (added to requirements set)
    3. Returns sets of discovered imports and requirements
    """
    imports = set()
    requirements = set()

    if not module:
        return imports, requirements

    if is_standard_lib(module, std_lib_modules):
        return imports, requirements
    elif is_first_party(module, current_dir):
        imports.add(module)
    elif is_third_party(module, package_paths):
        requirements.add(module)

    return imports, requirements


def _handle_import(
    alias_name: str,
    std_lib_modules: Set[str],
    current_dir: str,
    package_paths: Set[str],
) -> tuple[set, set]:
    """
    Process an Import AST node to classify the imported module.

    Args:
        alias_name (str): Name of the imported module/alias
        std_lib_modules (Set[str]): Set of standard library module names
        current_dir (str): Current working directory path
        package_paths (Set[str]): Set of paths to third party package directories

    Returns:
        tuple[set, set]: Tuple containing:
            - Set of first party module imports
            - Set of third party package requirements

    This function processes an Import AST node by:
    1. Determining module type:
        - Standard library module (ignored)
        - First party module (added to imports set)
        - Third party package (added to requirements set)
    2. Returns sets of discovered imports and requirements
    """
    imports = set()
    requirements = set()

    if is_standard_lib(alias_name, std_lib_modules):
        return imports, requirements
    elif is_first_party(alias_name, current_dir):
        imports.add(alias_name)
    elif is_third_party(alias_name, package_paths):
        requirements.add(alias_name)

    return imports, requirements


def parse_imports(
    file_path: str,
    std_lib_modules: Set[str],
    package_paths: Set[str],
    current_dir: str,
) -> tuple[Set[str], Set[str]]:
    """
    Parse a Python file and extract all import dependencies.

    Args:
        file_path (str): Path to Python file to parse
        std_lib_modules (Set[str]): Set of standard library module names
        package_paths (Set[str]): Set of paths to third party package directories
        current_dir (str): Current working directory path

    Returns:
        tuple[Set[str], Set[str]]: Tuple containing:
            - Set of first party module imports
            - Set of third party package requirements

    This function:
    1. Reads and parses the Python file into an AST
    2. Iterates through all Import and ImportFrom nodes
    3. Classifies each imported module as:
        - Standard library module (ignored)
        - First party module (added to imports set)
        - Third party package (added to requirements set)
    4. Returns combined sets of all discovered imports and requirements
    """
    with open(file_path, "r") as f:
        node = ast.parse(f.read(), file_path)

    imports = set()
    requirements = set()

    for n in ast.iter_child_nodes(node):
        if isinstance(n, ast.ImportFrom):
            imp, req = _handle_import_from(n.module, std_lib_modules, current_dir, package_paths)
            imports.update(imp)
            requirements.update(req)

        elif isinstance(n, ast.Import):
            for alias in n.names:
                imp, req = _handle_import(alias.name, std_lib_modules, current_dir, package_paths)
                imports.update(imp)
                requirements.update(req)

    return imports, requirements


def gather_dependencies() -> None:
    """
    Gather and distribute dependencies for all Lambda functions.

    This function:
    1. Gets standard library modules and package installation paths
    2. For each Lambda function directory in SRC_DIR:
        - Analyzes imports in the handler.py file
        - Recursively analyzes imports in all dependent modules
        - Copies handler file and all dependencies to dist directory
        - Creates requirements.txt with third party dependencies

    The function handles three types of dependencies:
    - Standard library modules: Ignored since they're available in Lambda runtime
    - First party modules: Copied to dist directory maintaining package structure
    - Third party packages: Added to requirements.txt for installation

    Returns:
        None
    """
    std_lib_modules = set(sys.builtin_module_names)
    package_paths = get_package_paths()
    current_dir = os.getcwd()

    for lambda_dir in os.listdir(SRC_DIR):
        lambda_path = os.path.join(SRC_DIR, lambda_dir)
        imports = set()
        requirements = set()
        if os.path.isdir(lambda_path):
            lambda_file = os.path.join(lambda_path, HANDLER_FILE_NAME)
            if os.path.exists(lambda_file):
                # analyze import modules by a file
                _imports, _requirements = parse_imports(
                    lambda_file, std_lib_modules, package_paths, current_dir
                )
                imports |= _imports
                requirements |= _requirements

                # lambda dependencies
                queue = _imports.copy()
                while queue:
                    m = queue.pop()
                    module_path = os.path.join(current_dir, "src", f"{m.replace('.', os.sep)}.py")
                    __imports, __requirements = parse_imports(
                        module_path,
                        std_lib_modules,
                        package_paths,
                        current_dir,
                    )
                    imports |= __imports
                    requirements |= __requirements

                    queue |= __imports

                # add module's dependencies
                src_dir = os.path.join(current_dir, "src")
                dist_dit = os.path.join(DIST_DIR, lambda_dir)
                copy_file(lambda_file, os.path.join(dist_dit, HANDLER_FILE_NAME))
                distribute_modules(imports, requirements, src_dir, dist_dit)


SRC_DIR = "./src/lambdas"
HANDLER_FILE_NAME = "handler.py"
DIST_DIR = "./dist"


if __name__ == "__main__":
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    os.makedirs(DIST_DIR)

    gather_dependencies()
