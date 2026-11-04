# check version module

# Code destined to reporting the installed
# "elegant-toolkit" (cet) package version,
# mirroring cet.diagnostics.check_gpu/check_java's
# role as a simple "cet-*" diagnostic entry point.
# Also reports whether the "cpu" or "gpu" optional-dependency
# extra (see pyproject.toml's [project.optional-dependencies])
# was installed - this is an install-time property of the env,
# independent of whether a GPU is actually visible right now
# (e.g. on an HPC login node with no GPU attached), so it is
# NOT the same check as cet.diagnostics.check_gpu's runtime
# CuPy/PyTorch probing. Detected via "cupy-cuda13x"'s presence,
# since only the "gpu" extra pulls it in.

######################################################################
# imports

from importlib.metadata import version
from importlib.metadata import PackageNotFoundError

######################################################################
# defining auxiliary functions


def get_cet_version() -> str:
    """
    Returns the installed cet package version.

    Returns:
        str: The installed "elegant-toolkit" distribution version, or "(not installed)" if absent.
    """
    # trying to get version
    try:

        # getting installed distribution version
        cet_version = version('elegant-toolkit')

    except PackageNotFoundError:

        # updating version placeholder
        cet_version = '(not installed)'

    # returning cet version
    return cet_version


def get_cet_variant() -> str:
    """
    Returns which optional-dependency extra
    (see pyproject.toml) cet was installed with.

    Returns:
        str: "GPU" if "cupy-cuda13x" is installed (the "gpu" extra), "CPU" otherwise.
    """
    # trying to get cupy-cuda13x's version
    try:

        # getting installed distribution version
        version('cupy-cuda13x')

    except PackageNotFoundError:

        # returning cpu variant string (gpu extra's cupy-cuda13x is absent)
        return 'CPU'

    # returning gpu variant string (gpu extra's cupy-cuda13x is present)
    return 'GPU'


def print_cet_version() -> None:
    """
    Prints the installed cet package version
    and GPU/CPU variant.

    Returns:
        None.
    """
    # getting cet version and variant
    cet_version = get_cet_version()
    cet_variant = get_cet_variant()

    # printing cet version and variant
    print(f'cet {cet_version} ({cet_variant})')

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # running print_cet_version function
    print_cet_version()

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
