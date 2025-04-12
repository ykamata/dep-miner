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
        src (str): Source file path
        dest (str): Destination file path

    Returns:
        None
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
    2. Copies each imported module from source to destination
    3. Creates a requirements.txt file with third-party dependencies
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
    """Check if a module is part of the standard library.

    Args:
        module_name (str): Name of the module to check
        std_lib_modules (Set[str]): Set of standard library module names

    Returns:
        bool: True if module is part of standard library, False otherwise

    This function checks if a given module is part of Python's standard library by:
    1. Checking if it exists in the provided std_lib_modules set
    2. Finding the module spec and checking if its origin path is within the standard library directory
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
    """Check if a module is part of the third party library.

    Args:
        module_name (str): Name of the module to check
        package_paths (Set[str]): Set of paths to third party package directories

    Returns:
        bool: True if module is a third party package, False otherwise

    This function checks if a given module is from a third party package by:
    1. Attempting to import the module
    2. Checking if its file path starts with any of the provided package paths
    3. Returns False if module cannot be imported
    """
    try:
        module = importlib.import_module(module_name)
        return module.__file__.startswith(tuple(package_paths))
    except ImportError:
        return False


def is_first_party(module_name: str, current_dir: str) -> bool:
    """Check if a module is part of the first party library.

    Args:
        module_name (str): Name of the module to check
        current_dir (str): Current working directory path

    Returns:
        bool: True if module is a first party module, False otherwise

    This function checks if a given module is a first party module by:
    1. Attempting to import the module
    2. Checking that it's not in a virtual environment (.venv)
    3. Verifying the module file path starts with the current directory
    4. Returns False if module cannot be imported
    """
    try:
        module = importlib.import_module(module_name)
        if ".venv" in module.__file__:
            return False
        return module.__file__.startswith(current_dir)
    except ImportError:
        return False


def get_package_paths() -> Set[str]:
    """Get paths to third party package directories.

    Returns:
        Set[str]: Set of paths to directories containing installed packages

    This function:
    1. Iterates through Python's sys.path
    2. Collects paths containing 'site-packages' or 'dist-packages'
    3. Returns set of package installation directories
    """
    paths = set()
    for path in sys.path:
        if "site-packages" in path or "dist-packages" in path:
            paths.add(path)
    return paths


def _handle_import_from(
    module: str,
    std_lib_modules: Set[str],
    current_dir: str,
    package_paths: Set[str],
) -> tuple[set, set]:
    """Handle ImportFrom node processing.

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
    1. Checking if module is empty
    2. Determining if module is standard library, first party, or third party
    3. Adding first party modules to imports set
    4. Adding third party packages to requirements set
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
    """Handle Import node processing.

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
    1. Checking if module is standard library
    2. Determining if module is first party or third party
    3. Adding first party modules to imports set
    4. Adding third party packages to requirements set
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
    """Parse Python file and extract import dependencies.

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
    1. Parses the Python file into an AST
    2. Iterates through Import and ImportFrom nodes
    3. Processes each import to determine if it is:
       - Standard library (ignored)
       - First party module (added to imports)
       - Third party package (added to requirements)
    4. Returns sets of first party imports and third party requirements
    """
    with open(file_path, "r") as f:
        node = ast.parse(f.read(), file_path)

    imports = set()
    requirements = set()

    for n in ast.iter_child_nodes(node):
        if isinstance(n, ast.ImportFrom):
            imp, req = _handle_import_from(
                n.module, std_lib_modules, current_dir, package_paths
            )
            imports.update(imp)
            requirements.update(req)

        elif isinstance(n, ast.Import):
            for alias in n.names:
                imp, req = _handle_import(
                    alias.name, std_lib_modules, current_dir, package_paths
                )
                imports.update(imp)
                requirements.update(req)

    return imports, requirements


def gather_dependencies() -> None:
    """
    Gather and distribute dependencies for Lambda functions.

    This function:
    1. Gets standard library modules and package paths
    2. For each Lambda directory in SRC_DIR:
        - Analyzes imports in the handler.py file
        - Recursively analyzes imports in all dependent modules
        - Copies handler file and all dependencies to dist directory
        - Creates requirements.txt with third party dependencies

    The function handles three types of dependencies:
    - Standard library modules (ignored)
    - First party modules (copied to dist)
    - Third party packages (added to requirements.txt)

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
                    module_path = os.path.join(
                        current_dir, "src", f"{m.replace('.', os.sep)}.py"
                    )
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
                copy_file(
                    lambda_file, os.path.join(dist_dit, HANDLER_FILE_NAME)
                )
                distribute_modules(imports, requirements, src_dir, dist_dit)


SRC_DIR = "./src/lambdas"
HANDLER_FILE_NAME = "handler.py"
DIST_DIR = "./dist"


if __name__ == "__main__":
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    os.makedirs(DIST_DIR)

    gather_dependencies()
