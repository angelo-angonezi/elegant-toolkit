# check imports module

print('initializing...')  # noqa

# Code destined to checking all
# imports done in project tree.

######################################################################
# imports

from os import walk
from io import StringIO
from os.path import join
from warnings import simplefilter
from cet.constants import CET_PATH
from warnings import catch_warnings
from contextlib import redirect_stdout
from contextlib import redirect_stderr

######################################################################
# defining global variables

CACHE_FOLDERS = ['__pycache__',
                 '__init__',
                 '.git',
                 '.idea',
                 '.cache',
                 'egg-info']

######################################################################
# defining auxiliary functions


def is_cache(path: str,
             cache_folders: list
             ) -> bool:
    """
    Checks if a given path contains
    cache-related keywords.

    Args:
        path (str): Path to a folder or file to check.
        cache_folders (list): List of cache folder/file names to search for in path.

    Returns:
        bool: True if path contains any cache keywords, False otherwise.
    """
    # getting cache bool list
    cache_bool_list = [(cache_str in path)
                       for cache_str
                       in cache_folders]

    # getting cache bool
    cache_bool = any(cache_bool_list)

    # returning cache bool
    return cache_bool


def get_pyfile_paths(start_path: str,
                     cache_folders: list
                     ) -> list:
    """
    Recursively finds all .py files
    in folder and subdirectories.

    Args:
        start_path (str): Path to the folder to search.
        cache_folders (list): List of cache folder names to exclude from search.

    Returns:
        list: List of absolute paths to all .py files found.
    """
    # defining placeholder value for paths list
    paths_list = []

    # getting folders/subfolders/files in start path
    folders_subfolders_files = walk(start_path,
                                    topdown=False)

    # iterating over folders/subfolders/files
    for item in folders_subfolders_files:

        # getting current folder path/subfolders/files
        folder_path, _, files = item

        # iterating over files
        for file in files:

            # getting current file path
            file_path = join(folder_path,
                             file)

            # getting file is cache bool
            file_is_cache = is_cache(path=file_path,
                                     cache_folders=cache_folders)

            # getting file is .py bool
            file_is_py = file_path.endswith('.py')
            file_not_py = (not file_is_py)

            # getting skip bool list
            skip_bool_list = [file_is_cache,
                              file_not_py]

            # getting cache bool
            skip_bool = any(skip_bool_list)

            # checking skip bool
            if skip_bool:

                # skipping to next file
                continue

            # appending current path to paths list
            paths_list.append(file_path)

    # returning files list
    return paths_list


def get_file_imports(file_path: str) -> list:
    """
    Scans a Python file for all
    import statements.

    Args:
        file_path (str): Path to a .py file to scan.

    Returns:
        list: List of import statement strings found in the file.
    """
    # defining placeholder value for file imports
    file_imports = []

    # defining indent string
    indent_str = '   '

    # defining read mode
    read_mode = 'r'

    # defining encoding (important for pipeline gui button icons)
    encoding = 'utf-8'

    # reading current file
    with open(file=file_path, mode=read_mode, encoding=encoding) as open_file:

        # getting current file lines
        lines = open_file.readlines()

        # iterating over lines
        for line in lines:

            # getting line is indent bool
            line_is_indent = line.startswith(indent_str)

            # checking if line starts with indent
            if line_is_indent:

                # removing initial spaces from line
                line = line.replace(indent_str, '')

            # getting line is import bool
            line_is_import = (line.startswith('from') or line.startswith('import'))

            # checking if line is import
            if line_is_import:

                # cleaning line
                line = line.replace('\n', '')

                # appending current import to file imports
                file_imports.append(line)

    # returning file imports
    return file_imports


def get_imports_list(file_paths: list) -> list:
    """
    Collects and deduplicates all
    import statements from multiple files.

    Args:
        file_paths (list): List of paths to .py files to scan.

    Returns:
        list: Sorted list of unique import statement strings.
    """
    # defining placeholder value for imports list
    imports_list = []

    # iterating over file paths
    for file_path in file_paths:

        # getting current file imports
        file_imports = get_file_imports(file_path=file_path)

        # extending imports list
        imports_list.extend(file_imports)

    # removing duplicates (converting to set)
    imports_list = set(imports_list)

    # converting data types (converting back to list)
    imports_list = list(imports_list)

    # sorting list (by length of the strings, so imports match the way they appear on each module)
    imports_list = sorted(imports_list,
                          key=lambda x: (len(x), x))

    # returning imports list
    return imports_list


def validate_imports(imports_list: list) -> tuple:
    """
    Attempts to import each statement
    and captures any output or errors.

    Args:
        imports_list (list): List of import statement strings to validate.

    Returns:
        tuple: A tuple of (failed_imports, captured_output) where failed_imports
               is a list of import commands that failed, and captured_output is
               a dict mapping successful imports to their stdout/stderr/warnings.
    """
    # getting imports count
    imports_count = len(imports_list)

    # defining placeholder value for current import index
    current_import_index = 0

    # defining placeholder value for failed imports list
    failed_imports = []

    # defining placeholder value for captured output dict
    captured_output = {}

    # iterating over imports list
    for import_command in imports_list:

        # updating current import index
        current_import_index += 1

        # printing execution message
        f_string = f'running import {current_import_index} of {imports_count} ({import_command})'
        print(f_string)

        # defining placeholder buffer for current import's stdout/stderr
        output_buffer = StringIO()

        # trying to run current import
        try:

            # capturing warnings raised during current import (instead of printing live)
            with catch_warnings(record=True) as caught_warnings:

                # forcing every warning to be caught (default filters can silently skip repeats)
                simplefilter('always')

                # capturing stdout/stderr produced during current import
                with redirect_stdout(output_buffer), redirect_stderr(output_buffer):

                    # attempting to run current import
                    exec(import_command)

                # appending caught warnings to current output buffer
                for warning in caught_warnings:

                    # writing current warning to buffer
                    output_buffer.write(f'{warning.category.__name__}: {warning.message}\n')

        # handling exception
        except Exception as e:

            # writing current error to buffer
            output_buffer.write(f'Error: {e}\n')

            # appending current import to failed imports list
            failed_imports.append(import_command)

        # getting current import captured text
        current_output = output_buffer.getvalue()

        # checking if current import produced any output
        if current_output:

            # storing current import output
            captured_output[import_command] = current_output

    # returning failed imports list and captured output dict
    return failed_imports, captured_output


def get_import_package(import_command: str) -> str:
    """
    Extracts the base package name
    from an import statement.

    Args:
        import_command (str): An import statement string (e.g., "from X import Y" or "import X").

    Returns:
        str: The base package name (X in both cases).
    """
    # getting import command split
    import_split = import_command.split(' ')

    # getting package name (second word in both
    # "from X import Y" and "import X" structures)
    package = import_split[1]

    # returning package
    return package


def get_failed_packages(failed_imports: list) -> list:
    """
    Extracts unique base package names
    from failed import commands.

    Args:
        failed_imports (list): List of failed import command strings.

    Returns:
        list: Sorted list of unique base package names that failed.
    """
    # defining placeholder value for failed packages list
    failed_packages = []

    # iterating over failed imports
    for import_command in failed_imports:

        # getting current import package
        package = get_import_package(import_command=import_command)

        # appending current package to failed packages list
        failed_packages.append(package)

    # removing duplicates (converting to set)
    failed_packages = set(failed_packages)

    # converting data types (converting back to list)
    failed_packages = list(failed_packages)

    # sorting list
    failed_packages = sorted(failed_packages)

    # returning failed packages list
    return failed_packages


def check_imports(start_path: str,
                  cache_folders: list
                  ) -> None:
    """
    Validates all imports found in a
    folder's Python files, reporting failures.

    Args:
        start_path (str): Path to the folder containing .py files to check.
        cache_folders (list): List of cache folder names to exclude.

    Returns:
        None.

    Raises:
        Exception: If any imports fail, raises an exception with a summary of failed packages.
    """
    # printing execution message
    print('checking imports...')

    # getting file paths
    file_paths = get_pyfile_paths(start_path=start_path,
                                  cache_folders=cache_folders)

    # getting imports list
    imports_list = get_imports_list(file_paths=file_paths)

    # validating imports
    failed_imports, captured_output = validate_imports(imports_list=imports_list)

    # getting has captured output bool
    has_captured_output = bool(captured_output)

    # checking if any import produced output/warnings
    if has_captured_output:

        # printing execution message
        print('\noutput/warnings captured during import checks:')

        # getting dict items
        dict_items = captured_output.items()

        # iterating over captured output items
        for output_item in dict_items:

            # getting current import command/output
            import_command, output = output_item

            # printing current import output
            print(f'- {import_command}\n{output}')

    # getting failed imports count
    failed_imports_count = len(failed_imports)

    # getting no failures bool
    no_failures = (failed_imports_count == 0)

    # checking if there were any failures
    if no_failures:

        # printing execution message
        print('all imports successful!')

        # skipping rest of function
        return None

    # getting failed packages (grouped, unique base packages)
    failed_packages = get_failed_packages(failed_imports=failed_imports)

    # assembling error message
    e_string = f'{failed_imports_count} import(s) failed.\n'
    e_string += f'Failed packages ({len(failed_packages)}):\n'
    for package in failed_packages:
        e_string += f'- {package}\n'

    # quitting
    raise Exception(e_string)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # running check_imports function
    check_imports(start_path=CET_PATH,
                  cache_folders=CACHE_FOLDERS)

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
