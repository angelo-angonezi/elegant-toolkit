# download jdk module

print('initializing...')  # noqa

# Code destined to installing a JDK (via conda-forge's
# "openjdk" package) into a conda env, ahead of time.
# This is a safeguard, not a strict requirement:
# environments/environment_gpu.yml and environment_cpu.yml
# already pin "openjdk" as a conda dependency, so a normal
# "conda env create -f environments/environment_*.yml" already
# gets one. This module exists for envs that skipped/lost it
# (e.g. "pip install -e ." into a foreign/pre-existing env,
# or manual env editing), as a standalone way to (re)install
# it without recreating the whole env - and to surface the
# resulting JAVA_HOME (see cet.diagnostics.check_java, wired
# automatically into cet.config for the JVM-dependent
# converters under cet.preprocessing.converters, which use
# pims.bioformats/jpype).

######################################################################
# imports

print('importing required libraries...')  # noqa
from subprocess import run
from argparse import ArgumentParser
from sys import prefix as sys_prefix
from cet.diagnostics.check_java import get_java_home
from cet.diagnostics.check_java import java_home_is_valid
from cet.progress_tracker.ProgressTracker import ProgressTracker
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global variables

DEFAULT_ENV_PREFIX = sys_prefix

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
    description = "download jdk module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # env prefix param
    parser.add_argument('-p', '--env-prefix',
                        dest='env_prefix',
                        type=str,
                        default=DEFAULT_ENV_PREFIX,
                        required=False,
                        help=f'defines conda env prefix to install openjdk into (defaults to the '
                             f'currently active/running env: "{DEFAULT_ENV_PREFIX}")')

    # openjdk version param
    parser.add_argument('-v', '--openjdk-version',
                        dest='openjdk_version',
                        type=str,
                        default=None,
                        required=False,
                        help='defines a specific openjdk version to pin (e.g. "24.0.2", matching '
                             'environment_gpu.yml\'s pin) - installs conda-forge\'s latest '
                             'resolvable openjdk by default (matching environment_cpu.yml)')

    # overwrite output param
    parser.add_argument('-ow', '--overwrite-output',
                        dest='overwrite_output',
                        action='store_true',
                        required=False,
                        help='defines whether to reinstall (--force-reinstall) even if a valid JDK '
                             'is already present at --env-prefix\'s JAVA_HOME')

    # skip enter param
    parser.add_argument('-s', '--skip-enter',
                        dest='skip_enter',
                        action='store_true',
                        required=False,
                        help='defines whether to suppress "Enter to continue" input before execution')

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

        # defining placeholder for whether a valid JDK is already present
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
            progress_string += f'checking current JDK...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained (and an install is actually pending)
        else:

            # updating progress string based on attributes
            progress_string += f'installing openjdk...'
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
        java_home = get_java_home(env_prefix=env_prefix)
        self.already_present = (java_home_is_valid(java_home) and not overwrite_output)

        # updating attributes (single opaque "install" step, if not already present)
        self.iterations_num = (0
                               if self.already_present
                               else 1)

        # updating totals string
        totals_string = f'totals...'
        if self.already_present:
            totals_string += f' | valid JDK already present at "{java_home}"'
        else:
            totals_string += f' | openjdk install pending'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def download_jdk(env_prefix: str,
                 openjdk_version: str,
                 overwrite_output: bool,
                 progress_tracker: ModuleProgressTracker
                 ) -> None:
    """
    Given a conda env prefix, installs conda-
    forge's "openjdk" package into it (optionally
    pinned to openjdk_version), skipping the
    install if a valid JDK is already present at
    the resulting JAVA_HOME (unless overwrite_output
    is set).

    Args:
        env_prefix (str): The conda env prefix to install openjdk into.
        openjdk_version (str): A specific openjdk version to pin, or None for the latest resolvable one.
        overwrite_output (bool): Whether to force-reinstall even if a valid JDK is already present.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # checking whether install can be skipped
    java_home = get_java_home(env_prefix=env_prefix)
    if progress_tracker.already_present:

        # printing execution message
        f_string = (f'valid JDK already present at "{java_home}" - skipping install '
                   f'(pass --overwrite-output to reinstall anyway).')
        print(f_string)

        # skipping rest of function
        return None

    # getting conda-forge package spec (pinned, if a version was given)
    package_spec = (f'openjdk={openjdk_version}'
                   if openjdk_version
                   else 'openjdk')

    # assembling conda install command (--freeze-installed keeps conda from
    # resolving/replacing already-installed packages with its own conda-forge
    # builds - see cet.setup.download_pycudadecon's matching flag/comment)
    command = ['conda', 'install', '-y', '-p', env_prefix, '-c', 'conda-forge', '--freeze-installed', package_spec]
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

    # getting openjdk version
    openjdk_version = args_dict['openjdk_version']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running download jdk function
    download_jdk(env_prefix=env_prefix,
                 openjdk_version=openjdk_version,
                 overwrite_output=overwrite_output,
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
