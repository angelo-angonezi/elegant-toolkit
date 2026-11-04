# update utils module

# Code destined to storing the constants and functions shared between
# build_update_folder.py (which builds the versioned snapshots) and
# update.py (which applies them): repository location, ignore rules
# and update version naming. Stdlib-only, so that update.py can import
# it without pulling in anything else from the package it is about to
# overwrite.

######################################################################
# imports

import os
import re
from re import Match
from datetime import datetime

######################################################################
# defining global variables

# repository root (this file lives at <root>/src/cet/setup/)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# default folder holding the versioned update snapshots
UPDATES_DIR = os.path.join(REPO_ROOT, 'updates')

# update version folder name pattern (YYYY-MM-DD-v1, YYYY-MM-DD-v2, ...)
VERSION_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})-v(\d+)$')

# folder names never read from the update folder, never touched in the
# repository, and never considered for deletion (only matched at the
# top level, so e.g. src/cet/ml/data is kept)
IGNORED_ROOT_DIRS = {'.git',
                     '.idea',
                     '.claude',
                     'data',
                     'data_tmp',
                     'data_cl',
                     '.update_backups',
                     'updates',
                     'build',
                     'dist'}

# folder names ignored at any depth
IGNORED_DIRS = {'__pycache__'}

# suffixes of folders (e.g. "cet.egg-info") never synced
IGNORED_DIR_SUFFIXES = ('.egg-info',)

# file suffixes never synced
IGNORED_FILE_SUFFIXES = ('.pyc', '.pyo')

######################################################################
# defining auxiliary functions


def parse_version(name: str) -> tuple[str, int] | None:
    """
    Parses an update version folder name.

    Args:
        name (str): Folder name, e.g. "2026-10-21-v2".

    Returns:
        tuple[str, int] | None: (date, number) sortable key, or None if the name
        does not match YYYY-MM-DD-vN.
    """
    # matching pattern
    match: Match | None = VERSION_PATTERN.match(name)

    # returning None if no match
    if match is None:
        return None

    # returning sortable key (number as int, so that v10 > v9)
    return match.group(1), int(match.group(2))


def list_versions(updates_dir: str) -> list[str]:
    """
    Lists version folder names inside a folder, oldest first.

    Args:
        updates_dir (str): Folder holding the update versions.

    Returns:
        list[str]: Version folder names.
    """
    # returning empty list if folder does not exist
    if not os.path.isdir(updates_dir):
        return []

    # getting version folders
    versions = [d for d in os.listdir(updates_dir)
                if os.path.isdir(os.path.join(updates_dir, d))
                and parse_version(d) is not None]

    # returning sorted versions
    return sorted(versions, key=parse_version)


def next_version(updates_dir: str) -> str:
    """
    Gets the name of the next version to build, YYYY-MM-DD-vN, with N
    one above the highest existing version of the current day (starting at 1).

    Args:
        updates_dir (str): Folder holding the update versions.

    Returns:
        str: The next version name.
    """
    # getting today's date
    today = datetime.now().strftime('%Y-%m-%d')

    # getting today's version numbers
    numbers = [parse_version(v)[1] for v in list_versions(updates_dir)
               if parse_version(v)[0] == today]

    # returning next version name
    return f'{today}-v{max(numbers, default=0) + 1}'

######################################################################
# end of current module
