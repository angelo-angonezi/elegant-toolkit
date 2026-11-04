# download loci jar module

print('initializing...')  # noqa

# Code destined to downloading the Bio-Formats
# "loci_tools.jar" (used by pims.bioformats.
# BioformatsReader, itself used by cet.
# preprocessing.converters.ics_to_tif/vsi_to_tif/
# tif_to_tif for .ics/.vsi conversion) into a
# local folder ahead of time. This is a safeguard,
# not a strict requirement: pims.bioformats
# already downloads loci_tools.jar on its own the
# first time a BioformatsReader is instantiated
# and no jar is found (see pims.bioformats.
# _find_jar/download_jar) - but that first-run
# download happens silently in the middle of a
# pipeline run (with a UserWarning: "loci_tools.
# jar not found, downloading"). Pre-populating the
# jar here, into the exact directory pims.
# bioformats checks first (its own package
# directory - see pims.bioformats.
# _gen_jar_locations), avoids that mid-run
# warning/delay entirely.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os import makedirs
from os.path import join
from os.path import dirname
from cet.constants import ONE_MB
from argparse import ArgumentParser
import pims.bioformats as pims_bioformats
from cet.io.files import get_skip_file_bool
from cet.setup.download_ops import download_file
from cet.setup.download_ops import get_url_content_length
from cet.progress_tracker.ProgressTracker import ProgressTracker
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global variables

DEFAULT_JAR_VERSION = '6.7.0'  # matches pims.bioformats.download_jar's own default,
# so the version installed here is exactly what pims would otherwise fetch itself
JAR_FILENAME = 'loci_tools.jar'
DEFAULT_OUTPUT_FOLDER = dirname(pims_bioformats.__file__)  # pims' own package directory -
# the first location pims.bioformats._gen_jar_locations checks for an existing jar
LOCI_JAR_URL_TEMPLATE = 'http://downloads.openmicroscopy.org/bio-formats/{version}/artifacts/loci_tools.jar'

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
    description = "download loci jar module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        default=DEFAULT_OUTPUT_FOLDER,
                        required=False,
                        help=f'defines folder to download loci_tools.jar into (matches pims\' own '
                             f'package directory, the first location pims.bioformats checks for an '
                             f'existing jar; defaults to "{DEFAULT_OUTPUT_FOLDER}")')

    # jar version param
    parser.add_argument('-v', '--jar-version',
                        dest='jar_version',
                        type=str,
                        default=DEFAULT_JAR_VERSION,
                        required=False,
                        help=f'defines the Bio-Formats "loci_tools.jar" version to download (matches '
                             f'pims.bioformats.download_jar\'s own default; defaults to '
                             f'"{DEFAULT_JAR_VERSION}")')

    # overwrite output param
    parser.add_argument('-ow', '--overwrite-output',
                        dest='overwrite_output',
                        action='store_true',
                        required=False,
                        help='defines whether to re-download even if loci_tools.jar is '
                             'already present under --output-folder')

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

        # if total iterations already obtained (and a download is actually pending)
        else:

            # getting done/total in MB for display
            done_mb = (self.current_iteration / ONE_MB)
            total_mb = (self.iterations_num / ONE_MB)

            # rounding values
            done_mb = round(done_mb)
            total_mb = round(total_mb)

            # updating progress string based on attributes
            progress_string += f'downloading loci_tools.jar...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | {done_mb}/{total_mb}MB'
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
        # getting jar version
        jar_version = args_dict['jar_version']

        # getting jar url
        jar_url = LOCI_JAR_URL_TEMPLATE.format(version=jar_version)

        # updating iterations (bytes num)
        self.iterations_num = get_url_content_length(jar_url)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | bytes: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def download_loci_jar(output_folder: str,
                      jar_version: str,
                      overwrite_output: bool,
                      progress_tracker: ModuleProgressTracker
                      ) -> None:
    """
    Given an output folder and a Bio-Formats
    version, downloads loci_tools.jar into it,
    skipping the download if already present
    (unless overwrite_output is set).

    Args:
        output_folder (str): The folder to download loci_tools.jar into.
        jar_version (str): The Bio-Formats version to download loci_tools.jar from.
        overwrite_output (bool): Whether to re-download even if the jar is already present.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting jar url
    jar_url = LOCI_JAR_URL_TEMPLATE.format(version=jar_version)

    # getting jar path
    jar_path = join(output_folder,
                    JAR_FILENAME)

    # getting skip file bool
    skip_file = get_skip_file_bool(file_path=jar_path,
                                   overwrite_output=overwrite_output)

    # checking whether to skip current file
    if skip_file:

        # sleeping
        progress_tracker.wait(0.05)

        # updating progress tracker attributes
        progress_tracker.current_iteration += progress_tracker.iterations_num

        # skipping download
        return None

    # creating output folder (does nothing if it already exists)
    makedirs(output_folder,
             exist_ok=True)

    # downloading loci_tools.jar (temp-file-then-rename, same atomicity pims' own
    # download_jar provides - see cet.setup.download_ops.download_file)
    download_file(url=jar_url,
                  output_path=jar_path,
                  progress_tracker=progress_tracker)


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

    # getting jar version
    jar_version = args_dict['jar_version']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running download_loci_jar function
    download_loci_jar(output_folder=output_folder,
                      jar_version=jar_version,
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
