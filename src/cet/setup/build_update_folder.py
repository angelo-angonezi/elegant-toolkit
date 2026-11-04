# build update folder module

print('initializing...')  # noqa

# Code destined to building, on a machine with the git history, the
# versioned, full snapshot of the repository that update.py consumes
# on the (offline) target. It copies every tracked file (and untracked,
# non-ignored ones, only if asked to) from the working tree into
# <output folder>/YYYY-MM-DD-vN, preserving repo-relative paths.
# Unlike update.py, this module does not overwrite the package it runs
# from (it only reads the repository), so it can safely use the
# progress tracker; the shared constants and version naming still
# come from cet.setup.update_utils.

######################################################################
# imports

print('importing required libraries...')  # noqa
import os
from shutil import copy2
from subprocess import run
from argparse import ArgumentParser
from cet.setup.update_utils import REPO_ROOT
from cet.setup.update_utils import UPDATES_DIR
from cet.setup.update_utils import IGNORED_DIRS
from cet.setup.update_utils import next_version
from cet.setup.update_utils import IGNORED_ROOT_DIRS
from cet.setup.update_utils import IGNORED_DIR_SUFFIXES
from cet.setup.update_utils import IGNORED_FILE_SUFFIXES
from cet.progress_tracker.ProgressTracker import ProgressTracker
print('all required libraries successfully imported.')  # noqa

######################################################################
# argument parsing related functions


def get_args_dict() -> dict:
    """
    Parses command-line arguments and returns
    them as a dictionary.

    Returns:
        dict: A dictionary containing all parsed command-line arguments.
    """
    # defining program description
    description = "build update folder module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=False,
                        default=UPDATES_DIR,
                        help='defines path to folder holding the update versions (default: updates folder in repository root)')

    # include untracked param
    parser.add_argument('-iu', '--include-untracked',
                        dest='include_untracked',
                        action='store_true',
                        required=False,
                        help='defines whether to also include untracked files not covered by .gitignore (default: tracked files only)')

    # skip enter param
    parser.add_argument('-s', '--skip-enter',
                        dest='skip_enter',
                        action='store_true',
                        required=False,
                        help='defines whether to suppress "Enter to continue" input before execution')

    # getting parsed args
    args = parser.parse_args()

    # creating arguments dictionary
    args_dict = vars(args)

    # returning the arguments dictionary
    return args_dict

######################################################################
# defining auxiliary functions


def git_lines(*git_args: str) -> list[str]:
    """
    Runs a git command in the repository and returns its non-empty output lines.

    Args:
        *git_args (str): Arguments passed to git.

    Returns:
        list[str]: Output lines.
    """
    # running git (raises on non-zero exit code)
    result = run(['git', '-C', REPO_ROOT, '-c', 'core.quotepath=off', *git_args],
                 check=True, capture_output=True, text=True, encoding='utf-8')

    # returning non-empty lines
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_included(rel_path: str) -> bool:
    """
    Checks whether a repo-relative (forward-slash) path belongs in an update.

    Args:
        rel_path (str): Repo-relative path.

    Returns:
        bool: True if the path is not under an ignored folder and not bytecode.
    """
    # splitting path
    parts = rel_path.split('/')

    # returning inclusion bool
    return (parts[0] not in IGNORED_ROOT_DIRS
            and not any(p in IGNORED_DIRS or p.endswith(IGNORED_DIR_SUFFIXES) for p in parts[:-1])
            and not rel_path.endswith(IGNORED_FILE_SUFFIXES))


def get_rel_paths(include_untracked: bool) -> list[str]:
    """
    Gets the repo-relative (forward-slash) paths of the files to be
    included in a new snapshot.

    Args:
        include_untracked (bool): Whether to also include untracked, non-ignored files.

    Returns:
        list[str]: Repo-relative paths of existing, non-ignored files.
    """
    # getting tracked files
    rel_paths = git_lines('ls-files', '--cached')

    # adding untracked files if requested
    if include_untracked:
        rel_paths += git_lines('ls-files', '--others', '--exclude-standard')

    # filtering ignored paths (dedup, keeping order) and files deleted
    # from the working tree but still in the index
    rel_paths = [p for p in dict.fromkeys(rel_paths)
                 if is_included(p)
                 and os.path.isfile(os.path.join(REPO_ROOT, *p.split('/')))]

    # returning relative paths
    return rel_paths

######################################################################
# progress tracking related functions


class ModuleProgressTracker(ProgressTracker):
    """
    Defines ModuleProgressTracker class.
    """
    # defining ProgressTracker init
    def __init__(self) -> None:
        """
        Initializes a ModuleProgressTracker
        instance and defines class attributes.
        """
        # inheriting attributes and methods from ProgressTracker
        super().__init__()

    # overwriting class methods (using current module specific attributes)

    def get_progress_string(self) -> str:
        """
        Returns a formatted progress
        string, based on current progress
        attributes.

        Returns:
            str: The current progress string.
        """
        # assembling current progress string
        progress_string = f''

        # checking if iterations total has already been obtained
        if not self.totals_updated.is_set():

            # updating progress string based on attributes
            progress_string += f'calculating totals...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'copying files...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | {self.current_iteration}/{self.iterations_num} files'
            progress_string += f' | progress: {self.progress_percentage_str}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'
            progress_string += f' | ETC: {self.etc_str}'

        # returning progress string
        return progress_string

    def update_totals(self,
                      args_dict: dict
                      ) -> None:
        """
        Implements module specific method
        to update total iterations num.

        Args:
            args_dict (dict): A dictionary containing all parsed command-line arguments.

        Returns:
            None.
        """
        # getting relevant args
        include_untracked = args_dict['include_untracked']

        # getting files to be copied
        rel_paths = get_rel_paths(include_untracked=include_untracked)

        # getting files num
        files_num = len(rel_paths)

        # getting files range
        files_range = range(files_num)

        # iterating over files
        for _ in files_range:

            # updating progress tracker attributes
            self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | files to copy: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def build_update_folder(output_folder: str,
                        include_untracked: bool,
                        progress_tracker: ModuleProgressTracker
                        ) -> None:
    """
    Builds a new versioned, full snapshot of the repository.

    Args:
        output_folder (str): Folder holding the update versions (the new
            version folder is created inside it).
        include_untracked (bool): Whether to also include untracked, non-ignored files.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting new version name and folder
    version = next_version(updates_dir=output_folder)
    version_folder = os.path.join(output_folder, version)

    # getting files to be copied
    rel_paths = get_rel_paths(include_untracked=include_untracked)

    # looping through files
    for rel_path in rel_paths:

        # getting paths
        source_path = os.path.join(REPO_ROOT, *rel_path.split('/'))
        target_path = os.path.join(version_folder, *rel_path.split('/'))

        # creating target folder
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        # copying file
        copy2(source_path, target_path)

        # updating progress tracker
        progress_tracker.current_iteration += 1

    # defining summary string
    f_string = f'update version: {version}\n'
    f_string += f'update folder: {os.path.abspath(version_folder)}'

    # updating progress tracker attributes
    progress_tracker.end_string = f'{f_string}\n{progress_tracker.end_string}'


def parse_and_run(args_dict: dict,
                  progress_tracker: ModuleProgressTracker
                  ) -> None:
    """
    Extracts args from args_dict
    and runs module function.

    Args:
        args_dict (dict): A dictionary containing all parsed command-line arguments.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting output folder
    output_folder = args_dict['output_folder']

    # getting include untracked
    include_untracked = args_dict['include_untracked']

    # running build update folder function
    build_update_folder(output_folder=output_folder,
                        include_untracked=include_untracked,
                        progress_tracker=progress_tracker)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # initializing current module progress tracker instance
    progress_tracker = ModuleProgressTracker()

    # running code in separate thread
    progress_tracker.run(function=parse_and_run,
                         args_parser=get_args_dict)

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
