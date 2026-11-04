# update module

print('initializing...')  # noqa

# Code destined to upgrading this package in-place from a local
# folder, with no internet access (e.g. on a cluster). The folder
# holds versioned, full snapshots of the repository (see
# build_update_folder.py), named YYYY-MM-DD-v1, YYYY-MM-DD-v2, ...
# (default: join(REPO_ROOT, 'updates'); the most recent version is used).
# Files that are new or different (by sha256) are copied over the
# installed checkout; replaced files are backed up first. Nothing is
# deleted from the checkout unless asked to. A "pip install -e ."
# always runs at the end.
# Deliberately minimal: pip explicitly recommends against importing
# its internals into a running process (see pip docs), and importing
# anything from "cet" itself here (progress tracker, argparse helpers,
# etc.) would mean this process has already loaded modules from the
# very package it's about to overwrite. So this stays stdlib-only
# (no ModuleProgressTracker either), apart from the equally stdlib-only
# cet.setup.update_utils, imported up front, before any file is replaced.

######################################################################
# imports

print('importing required libraries...')  # noqa
import os
from shutil import copy2
from hashlib import sha256
from subprocess import run
from datetime import datetime
from difflib import unified_diff
from argparse import ArgumentParser
from sys import executable as sys_executable
from cet.setup.update_utils import REPO_ROOT
from cet.setup.update_utils import UPDATES_DIR
from cet.setup.update_utils import IGNORED_DIRS
from cet.setup.update_utils import list_versions
from cet.setup.update_utils import IGNORED_ROOT_DIRS
from cet.setup.update_utils import IGNORED_DIR_SUFFIXES
from cet.setup.update_utils import IGNORED_FILE_SUFFIXES
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global variables

# name of the backup folder created inside the repository root
BACKUP_DIR_NAME = '.update_backups'

# top-level folder inside which files absent from the update are
# removed when deleting (the rest of the checkout, e.g. local
# settings files, is never considered for removal)
DELETE_SCOPE = 'src'

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
    description = "update module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=False,
                        default=UPDATES_DIR,
                        help='defines path to folder holding the update versions (default: updates folder in repository root)')

    # version param
    parser.add_argument('-v', '--version',
                        dest='version',
                        type=str,
                        required=False,
                        default=None,
                        help='defines which version (e.g. 2026-10-21-v1) to update to (default: most recent)')

    # delete param
    parser.add_argument('-d', '--delete',
                        dest='delete',
                        action='store_true',
                        required=False,
                        help=f'defines whether to remove files in "{DELETE_SCOPE}" absent from the update, backed up first')

    # dry run param
    parser.add_argument('-dr', '--dry-run',
                        dest='dry_run',
                        action='store_true',
                        required=False,
                        help='defines whether to only list what would change')

    # diff param
    parser.add_argument('--diff',
                        dest='diff',
                        action='store_true',
                        required=False,
                        help='defines whether to also print a git-like diff of modified files (implies --dry-run)')

    # find links param
    parser.add_argument('-fl', '--find-links',
                        dest='find_links',
                        type=str,
                        required=False,
                        default=None,
                        help='defines path to local wheel folder for offline dependency install')

    # getting parsed args
    args = parser.parse_args()

    # creating arguments dictionary
    args_dict = vars(args)

    # returning the arguments dictionary
    return args_dict

######################################################################
# defining auxiliary functions


def resolve_source_root(input_folder: str,
                        version: str | None
                        ) -> str:
    """
    Gets the folder holding the snapshot to update to: the given version
    inside the input folder, the input folder itself if it already is a
    snapshot, or else the most recent version inside it.

    Args:
        input_folder (str): Update folder given by the user.
        version (str | None): Specific version to use.

    Returns:
        str: Folder holding "src" and "pyproject.toml".
    """
    # checking input folder exists
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f'update folder "{input_folder}" does not exist')

    # checking if a version was given
    if version:

        # getting version folder
        source_root = os.path.join(input_folder, version)

        # checking version folder exists
        if not os.path.isdir(source_root):
            raise FileNotFoundError(f'version "{version}" not found in "{input_folder}"')

        # returning version folder
        return source_root

    # returning input folder itself if it already is a snapshot
    if (os.path.isdir(os.path.join(input_folder, 'src'))
            and os.path.isfile(os.path.join(input_folder, 'pyproject.toml'))):
        return input_folder

    # getting versions
    versions = list_versions(input_folder)

    # raising error if no versions
    if not versions:
        raise FileNotFoundError(f'no update versions (YYYY-MM-DD-vN) found in "{input_folder}"')

    # returning most recent version folder
    return os.path.join(input_folder, versions[-1])


def file_hash(path: str) -> str:
    """
    Computes the sha256 hex digest of a file.

    Args:
        path (str): Path to the file.

    Returns:
        str: The hex digest.
    """
    # initializing hasher
    hasher = sha256()

    # reading file in chunks
    with open(path, 'rb') as f:

        # iterating over chunks
        for chunk in iter(lambda: f.read(1 << 20), b''):

            # updating hasher
            hasher.update(chunk)

    # returning digest
    return hasher.hexdigest()


def list_files(root: str) -> list[str]:
    """
    Lists all files under a folder as paths relative to it, skipping
    ignored folders and file types.

    Args:
        root (str): Folder to walk.

    Returns:
        list[str]: Relative file paths.
    """
    # initializing relative paths list
    rel_paths = []

    # walking folder
    for current_dir, dir_names, file_names in os.walk(root):

        # checking if at top level
        at_top_level = os.path.normpath(current_dir) == os.path.normpath(root)

        # pruning ignored folders in-place
        dir_names[:] = [d for d in dir_names
                        if d not in IGNORED_DIRS
                        and not d.endswith(IGNORED_DIR_SUFFIXES)
                        and not (at_top_level and d in IGNORED_ROOT_DIRS)]

        # looping through files in current folder
        for file_name in file_names:

            # skipping ignored file types
            if file_name.endswith(IGNORED_FILE_SUFFIXES):

                # skipping
                continue

            # getting relative path
            rel_path = os.path.relpath(os.path.join(current_dir, file_name), root)

            # appending to list
            rel_paths.append(rel_path)

    # returning relative paths
    return rel_paths


def plan_changes(source_root: str,
                 delete: bool
                 ) -> tuple[list[str], list[str], list[str]]:
    """
    Compares the update snapshot against the repository.

    Args:
        source_root (str): Folder holding the snapshot.
        delete (bool): Whether files absent from the snapshot should be flagged for removal.

    Returns:
        tuple[list[str], list[str], list[str]]: Relative paths of new files,
        modified files and files to remove.
    """
    # initializing lists
    new_files = []
    modified_files = []
    removed_files = []

    # getting update files
    source_files = list_files(source_root)

    # looping through update files
    for rel_path in source_files:

        # getting paths
        source_path = os.path.join(source_root, rel_path)
        target_path = os.path.join(REPO_ROOT, rel_path)

        # flagging new file
        if not os.path.isfile(target_path):
            new_files.append(rel_path)

        # flagging modified file
        elif file_hash(source_path) != file_hash(target_path):
            modified_files.append(rel_path)

    # checking if deleting
    if delete:

        # getting update files set
        source_set = set(source_files)

        # looping through repository files
        for rel_path in list_files(REPO_ROOT):

            # flagging file in delete scope absent from the update
            if rel_path.split(os.sep)[0] == DELETE_SCOPE and rel_path not in source_set:
                removed_files.append(rel_path)

    # returning plan
    return new_files, modified_files, removed_files


def read_text_lines(path: str) -> list[str] | None:
    """
    Reads a file as text lines (line endings normalized).

    Args:
        path (str): Path to the file.

    Returns:
        list[str] | None: Lines, or None if the file looks binary.
    """
    # reading file bytes
    with open(path, 'rb') as f:
        content = f.read()

    # returning None if binary
    if b'\0' in content[:8192]:
        return None

    # returning decoded lines
    return content.decode('utf-8', errors='replace').splitlines()


def print_diff(source_root: str,
               modified_files: list[str]
               ) -> None:
    """
    Prints a git-like unified diff (repository -> update) for each modified file.

    Args:
        source_root (str): Folder holding the snapshot.
        modified_files (list[str]): Relative paths of modified files.

    Returns:
        None.
    """
    # looping through modified files
    for rel_path in modified_files:

        # reading both versions
        repo_lines = read_text_lines(os.path.join(REPO_ROOT, rel_path))
        update_lines = read_text_lines(os.path.join(source_root, rel_path))

        # getting forward-slash path
        display_path = rel_path.replace(os.sep, '/')

        # reporting binary files
        if repo_lines is None or update_lines is None:

            # printing progress message
            print(f'binary files differ: {display_path}')

            # skipping
            continue

        # getting diff lines
        diff_lines = unified_diff(repo_lines,
                                  update_lines,
                                  fromfile=f'repo/{display_path}',
                                  tofile=f'update/{display_path}',
                                  lineterm='')

        # converting data types
        diff_lines = list(diff_lines)

        # reporting line-ending-only differences
        if not diff_lines:

            # printing progress message
            print(f'only line endings differ: {display_path}')

            # skipping
            continue

        # getting diff string
        diff_string = '\n'.join(diff_lines)

        # printing diff
        print(diff_string)


def install_package(find_links: str | None) -> None:
    """
    Runs the editable install without internet access, refreshing the
    "cet-*" entry points. Dependencies are only installed if a local wheel
    folder is given.

    Args:
        find_links (str | None): Optional local folder with wheels.

    Returns:
        None.
    """
    # assembling offline pip command (uses sys.executable, per pip's own
    # guidance, rather than assuming a bare "pip"/"pip3" on PATH)
    command = [sys_executable,
               '-m',
               'pip',
               'install',
               '-e',
               REPO_ROOT,
               '--no-index',
               '--no-build-isolation']

    # checking if local wheels were given
    if find_links:

        # using local wheels for dependencies
        command += ['--find-links', find_links]

    # if no local wheels
    else:

        # leaving dependencies as-is
        command += ['--no-deps']

    # printing execution message
    print('running "pip install -e ." (offline)...')

    # running pip command (raises on non-zero exit code)
    run(command,
        check=True)


def update_from_folder(input_folder: str,
                       version: str | None,
                       delete: bool,
                       dry_run: bool,
                       diff: bool,
                       find_links: str | None
                       ) -> None:
    """
    Updates this checkout from a local folder.

    Args:
        input_folder (str): Folder holding the update versions.
        version (str | None): Specific version to use (default: most recent).
        delete (bool): Whether to remove files absent from the update (backed up first).
        dry_run (bool): Whether to only report what would change.
        diff (bool): Whether to also print a diff of modified files (implies dry_run).
        find_links (str | None): Local wheel folder for offline dependency install.

    Returns:
        None.
    """
    # getting update source root
    source_root = resolve_source_root(input_folder=os.path.abspath(input_folder),
                                      version=version)

    # refusing to update from the checkout itself
    if os.path.normcase(source_root) == os.path.normcase(REPO_ROOT):
        raise ValueError('update folder is the repository itself')

    # planning changes
    new_files, modified_files, removed_files = plan_changes(source_root=source_root,
                                                            delete=delete)

    # printing summary
    print(f'update source: {source_root}')
    print(f'new: {len(new_files)} | modified: {len(modified_files)} | removed: {len(removed_files)}')

    # looping through change tags
    for tag, rel_paths in (('+', new_files), ('~', modified_files), ('-', removed_files)):

        # looping through changed files
        for rel_path in rel_paths:

            # printing changed file
            print(f'  {tag} {rel_path}')

    # printing diff if requested
    if diff:
        print_diff(source_root=source_root,
                   modified_files=modified_files)

    # returning if dry run or diff
    if dry_run or diff:
        print('dry run: no files were changed')
        return None

    # checking if there is anything to copy or remove
    if new_files or modified_files or removed_files:

        # creating timestamped backup folder path
        backup_root = os.path.join(REPO_ROOT, BACKUP_DIR_NAME, datetime.now().strftime('%Y%m%d_%H%M%S'))

        # backing up files about to be replaced or removed
        for rel_path in modified_files + removed_files:

            # getting backup path
            backup_path = os.path.join(backup_root, rel_path)

            # creating backup folder
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # copying file to backup
            copy2(os.path.join(REPO_ROOT, rel_path), backup_path)

        # copying new and modified files
        for rel_path in new_files + modified_files:

            # getting target path
            target_path = os.path.join(REPO_ROOT, rel_path)

            # creating target folder
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # copying file
            copy2(os.path.join(source_root, rel_path), target_path)

        # removing files (backed up above)
        for rel_path in removed_files:
            os.remove(os.path.join(REPO_ROOT, rel_path))

        # printing backup location
        if modified_files or removed_files:
            print(f'previous versions backed up to: {backup_root}')

    # if nothing to copy or remove
    else:

        # printing execution message
        print('files already up to date!')

    # installing package
    install_package(find_links=find_links)

    # printing execution message
    print('update complete!')


def parse_and_run(args_dict: dict) -> None:
    """
    Extracts args from args_dict
    and runs module function.

    Args:
        args_dict (dict): A dictionary containing all parsed command-line arguments.

    Returns:
        None.
    """
    # getting input folder
    input_folder = args_dict['input_folder']

    # getting version
    version = args_dict['version']

    # getting delete
    delete = args_dict['delete']

    # getting dry run
    dry_run = args_dict['dry_run']

    # getting diff
    diff = args_dict['diff']

    # getting find links
    find_links = args_dict['find_links']

    # running update from folder function
    update_from_folder(input_folder=input_folder,
                       version=version,
                       delete=delete,
                       dry_run=dry_run,
                       diff=diff,
                       find_links=find_links)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # getting args dict
    args_dict = get_args_dict()

    # running parse and run function
    parse_and_run(args_dict=args_dict)

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
