# download pycudadecon module

print('initializing...')  # noqa

# Code destined to installing "pycudadecon" (via conda-
# forge's package of the same name) into a conda env,
# ahead of time. Unlike most of this project's pip
# dependencies, pycudadecon can't just live in pyproject.
# toml's [project.optional-dependencies] "gpu" extra: its
# PyPI wheel only ships the Python bindings, not a working
# compiled "cudaDecon" CUDA backend, and building it from
# source at pip-install time isn't reliable on the lab's
# HPC. conda-forge's pycudadecon package bundles a working
# compiled backend, so this module exists as a standalone,
# conda-based way to (re)install it - mirroring
# cet.setup.download_jdk's role for "openjdk" (another
# dependency that can't just be a pip package).

######################################################################
# imports

print('importing required libraries...')  # noqa
from json import loads
from subprocess import run
from subprocess import PIPE
from argparse import ArgumentParser
from sys import prefix as sys_prefix
from cet.diagnostics.check_gpu import gpu_is_available
from cet.progress_tracker.ProgressTracker import ProgressTracker
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global variables

DEFAULT_ENV_PREFIX = sys_prefix
PACKAGE_NAME = 'pycudadecon'

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
    description = "download pycudadecon module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # env prefix param
    parser.add_argument('-p', '--env-prefix',
                        dest='env_prefix',
                        type=str,
                        default=DEFAULT_ENV_PREFIX,
                        required=False,
                        help=f'defines conda env prefix to install pycudadecon into (defaults to the '
                             f'currently active/running env: "{DEFAULT_ENV_PREFIX}")')

    # overwrite output param
    parser.add_argument('-ow', '--overwrite-output',
                        dest='overwrite_output',
                        action='store_true',
                        required=False,
                        help='defines whether to reinstall (--force-reinstall) even if pycudadecon is '
                             'already present at --env-prefix')

    # skip enter param
    parser.add_argument('-s', '--skip-enter',
                        dest='skip_enter',
                        action='store_true',
                        required=False,
                        help='defines whether to suppress "Enter to continue" input before execution')

    # force no gpu param
    parser.add_argument('-fng', '--force-no-gpu',
                        dest='force_no_gpu',
                        action='store_true',
                        required=False,
                        help=f'{PACKAGE_NAME} only runs on a CUDA GPU (see cet.preprocessing.'
                             f'deconvolve_images) - by default this module refuses to install it into an '
                             f'env with no GPU detected, since its conda-forge install has been observed to '
                             f'pull in a large native dependency chain (numpy, mkl, icu, etc.) that can '
                             f'silently replace already-installed packages and break unrelated DLL-dependent '
                             f'tools (e.g. PyQt6/cet-gui) on Windows, for no functional benefit on a '
                             f'GPU-less machine. Pass this flag to install anyway.')

    # creating arguments dictionary
    args_dict = vars(parser.parse_args())

    # returning the arguments dictionary
    return args_dict

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

        # defining placeholder for whether pycudadecon is already present
        self.already_present = False

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
            progress_string += f'checking current pycudadecon install...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained (and an install is actually pending)
        else:

            # updating progress string based on attributes
            progress_string += f'installing pycudadecon...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

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
        env_prefix = args_dict['env_prefix']
        overwrite_output = args_dict['overwrite_output']

        # checking whether install can be skipped
        self.already_present = (package_is_installed(env_prefix=env_prefix, package_name=PACKAGE_NAME)
                                and not overwrite_output)

        # updating attributes (single opaque "install" step, if not already present)
        self.iterations_num = (0
                               if self.already_present
                               else 1)

        # updating totals string
        totals_string = f'totals...'
        if self.already_present:
            totals_string += f' | {PACKAGE_NAME} already present at "{env_prefix}"'
        else:
            totals_string += f' | {PACKAGE_NAME} install pending'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def package_is_installed(env_prefix: str,
                         package_name: str
                         ) -> bool:
    """
    Given a conda env prefix and package name,
    checks whether that package is currently
    installed into that env (via conda or pip -
    "conda list" reports both), without needing
    env_prefix to be the currently active/running
    env (unlike a plain "import package_name"
    check would).

    Args:
        env_prefix (str): The conda env prefix to check.
        package_name (str): The (conda/PyPI) package name to check for.

    Returns:
        bool: True if package_name is installed into env_prefix, False otherwise.
    """
    # running conda list command (raises on non-zero exit code)
    result = run(['conda', 'list', '-p', env_prefix, '--json', package_name],
                stdout=PIPE,
                check=True)

    # parsing json output (a list of installed-package dicts matching package_name)
    installed_packages = loads(result.stdout)

    # returning whether any matching package was found
    return (len(installed_packages) > 0)


def download_pycudadecon(env_prefix: str,
                         overwrite_output: bool,
                         force_no_gpu: bool,
                         progress_tracker: ModuleProgressTracker
                         ) -> None:
    """
    Given a conda env prefix, installs conda-
    forge's "pycudadecon" package into it,
    skipping the install if it's already
    present (unless overwrite_output is set).

    Args:
        env_prefix (str): The conda env prefix to install pycudadecon into.
        overwrite_output (bool): Whether to force-reinstall even if pycudadecon is already present.
        force_no_gpu (bool): Whether to proceed even if no CUDA GPU was detected on this machine.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.

    Raises:
        RuntimeError: If no CUDA GPU is detected and force_no_gpu is False.
    """
    # checking whether install can be skipped
    if progress_tracker.already_present:

        # printing execution message
        f_string = (f'{PACKAGE_NAME} already present at "{env_prefix}" - skipping install '
                   f'(pass --overwrite-output to reinstall anyway).')
        print(f_string)

        # skipping rest of function
        return None

    # refusing to install on a GPU-less machine unless explicitly overridden - pycudadecon
    # (cudaDecon) is CUDA-only with no CPU fallback (see cet.preprocessing.deconvolve_images),
    # so installing it here would only add DLL-conflict risk (see --force-no-gpu's help text)
    # for no functional benefit
    if not (force_no_gpu or gpu_is_available()):
        raise RuntimeError(f'no CUDA GPU detected at "{env_prefix}" - {PACKAGE_NAME} would not be usable '
                           f'there anyway (see cet.preprocessing.deconvolve_images), so refusing to install '
                           f'it (pass --force-no-gpu to install anyway).')

    # assembling conda install command (--freeze-installed keeps conda from
    # resolving/replacing already-installed packages - e.g. pip's numpy - with
    # its own conda-forge builds, which previously broke PyQt6's bundled Qt DLLs)
    command = ['conda', 'install', '-y', '-p', env_prefix, '-c', 'conda-forge', '--freeze-installed', PACKAGE_NAME]
    if overwrite_output:

        # adding force reinstall flag
        command.append('--force-reinstall')

    # running conda install command (raises on non-zero exit code)
    run(command,
        check=True)

    # updating progress tracker attributes (single opaque step, now complete)
    progress_tracker.current_iteration = 1


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
    # getting env prefix
    env_prefix = args_dict['env_prefix']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # getting force no gpu
    force_no_gpu = args_dict['force_no_gpu']

    # running download pycudadecon function
    download_pycudadecon(env_prefix=env_prefix,
                         overwrite_output=overwrite_output,
                         force_no_gpu=force_no_gpu,
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
