# check java module

# Code destined to locating the JDK/JVM home
# that conda-forge's "openjdk" package installs
# into a given conda env, for a given OS. Required
# so cet.config can wire JAVA_HOME automatically
# for the JVM-dependent converters (pims.bioformats/
# jpype), mirroring cet.diagnostics.check_gpu's role for
# GPU/DEVICE.

######################################################################
# imports

from os import environ
from os.path import join
from os.path import isfile
from sys import prefix as sys_prefix
from platform import system as platform_system

######################################################################
# defining auxiliary functions


def get_java_home(env_prefix: str | None = None) -> str:
    """
    Returns the JDK home path for a conda
    environment's installed openjdk package.

    Args:
        env_prefix (str | None): The conda env prefix, or None to use the current env's sys.prefix.

    Returns:
        str: The JDK home directory (env_prefix's "Library/lib/jvm" on Windows, env_prefix itself otherwise).
    """
    # falling back to current env's prefix, if none was given
    env_prefix = (env_prefix
                 if env_prefix is not None
                 else sys_prefix)

    # checking current OS
    if platform_system() == 'Windows':

        # returning windows-specific java home path
        return join(env_prefix, 'Library', 'lib', 'jvm')

    # returning java home path (env prefix itself, on linux/mac)
    return env_prefix


def java_home_is_valid(java_home: str) -> bool:
    """
    Checks if a given path points to a
    valid JDK home directory.

    Args:
        java_home (str): Path to a potential JDK home directory.

    Returns:
        bool: True if path contains a bin/java[.exe] executable, False otherwise.
    """
    # getting expected java executable path (OS-dependent)
    java_bin_name = ('java.exe'
                     if platform_system() == 'Windows'
                     else 'java')
    java_bin_path = join(java_home, 'bin', java_bin_name)

    # returning whether java executable exists
    return isfile(java_bin_path)


def print_java_availability() -> None:
    """
    Checks and prints JAVA_HOME status
    for the current conda environment.

    Returns:
        None.
    """
    # printing execution message
    print('checking JAVA_HOME availability...')

    # defining spacer string
    spacer_str = ('#' * 30)

    # getting current JAVA_HOME env var (as set by cet.config, or inherited from
    # elsewhere, e.g. a conda activate script - "(not set)" if absent entirely)
    java_home_env_var = environ.get('JAVA_HOME',
                                    '(not set)')

    # getting this env's expected JAVA_HOME (what cet.config would compute/wire, given
    # a conda-forge openjdk install - see cet.setup.download_jdk)
    expected_java_home = get_java_home()
    expected_java_home_valid = java_home_is_valid(expected_java_home)

    # assembling java availability string
    f_string = f'JAVA_HOME env var: {java_home_env_var}\n'
    f_string += f'Expected JAVA_HOME (current env): {expected_java_home}\n'
    f_string += f'Expected JAVA_HOME valid: {expected_java_home_valid}'

    # printing java availability string
    print(spacer_str)
    print(f_string)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # running print_java_availability function
    print_java_availability()

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
