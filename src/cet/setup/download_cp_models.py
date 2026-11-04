# download cp models module

print('initializing...')  # noqa

# Code destined to downloading the Cellpose "cpsam" model
# weights (used by cet.segmentation.run_cellpose for embryo/
# nuclei segmentation) into a local folder ahead of time. This
# is a safeguard, not a strict requirement: Cellpose already
# downloads "cpsam" on its own the first time it's needed (see
# cellpose.models.CellposeModel.__init__/cache_CPSAM_model_path)
# - but only into its own fixed per-user cache
# (cellpose.models.MODEL_DIR, typically "~/.cellpose/models"),
# *not* cet.constants.CELLPOSE_MODEL_PATH
# ("~/.cet/cellpose/models/cpsam", under CET_HOME) that
# cet.pipelines.pipeline passes to run_cellpose, and that
# run_cellpose itself now defaults to for standalone
# invocations too. If that path
# doesn't already exist, Cellpose silently falls
# back to its per-user cache dir instead (with a logged
# warning), so a pipeline run and this download command can
# otherwise end up disagreeing about which "cpsam" copy is
# actually in use. Pre-populating the project-relative path
# here avoids that fallback (and its per-user, first-run-is-
# slow download) entirely. (Note: the Cellpose weights are now
# stored under the per-user CET_HOME folder, not the repo.)

######################################################################
# imports

print('importing required libraries...')  # noqa
from os import makedirs
from os.path import join
from os.path import basename
from cet.constants import ONE_MB
from argparse import ArgumentParser
import cellpose.models as cellpose_models
from cet.io.files import get_skip_file_bool
from cet.constants import CELLPOSE_MODEL_PATH
from cet.setup.download_ops import download_file
from cet.constants import CELLPOSE_MODELS_FOLDER
from cet.setup.download_ops import get_url_content_length
from cet.progress_tracker.ProgressTracker import ProgressTracker
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global variables

DEFAULT_OUTPUT_FOLDER = CELLPOSE_MODELS_FOLDER
MODEL_FILENAME = str(basename(CELLPOSE_MODEL_PATH))  # 'cpsam' - derived rather than re-hardcoded,
# so it can never drift from cet.constants.CELLPOSE_MODEL_PATH


def _get_cpsam_model_url() -> str:
    """
    Resolves the cpsam model download URL
    across cellpose versions. Pinned
    cellpose==4.0.7 (environments/
    environment_gpu.yml) exposes it directly
    as cellpose.models._CPSAM_MODEL_URL. Newer
    cellpose releases (e.g. whatever pip
    resolves for the unpinned environments/
    environment_cpu.yml) dropped that constant
    in favor of a generic "_MODEL_URL" base
    joined with the model's backbone filename
    at download time (see cellpose.models.
    cache_model_path) - so that base is joined
    with MODEL_FILENAME ("cpsam") here instead.

    Returns:
        str: The resolved cpsam model download url.

    Raises:
        ImportError: If neither known URL constant is found on cellpose.models.
    """
    # pinned/older cellpose - full URL already includes the filename
    if hasattr(cellpose_models, '_CPSAM_MODEL_URL'):
        return cellpose_models._CPSAM_MODEL_URL

    # newer cellpose - base URL, filename joined separately
    if hasattr(cellpose_models, '_MODEL_URL'):
        return cellpose_models._MODEL_URL + MODEL_FILENAME

    # neither known constant found - surfacing a clear error rather than
    # an opaque ImportError/AttributeError from deeper in the module
    raise ImportError('could not resolve the cpsam model download URL from '
                      'cellpose.models (looked for "_CPSAM_MODEL_URL" and '
                      '"_MODEL_URL") - the installed cellpose version may be '
                      'unsupported.')


CPSAM_MODEL_URL = _get_cpsam_model_url()

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
    description = "download cp models module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        default=DEFAULT_OUTPUT_FOLDER,
                        required=False,
                        help=f'defines folder to download the cpsam model into (matches '
                             f'cet.constants.CELLPOSE_MODELS_FOLDER, also used by '
                             f'cet.pipelines.pipeline and cet.segmentation.run_cellpose\'s '
                             f'own -p default; defaults to "{DEFAULT_OUTPUT_FOLDER}")')

    # overwrite output param
    parser.add_argument('-ow', '--overwrite-output',
                        dest='overwrite_output',
                        action='store_true',
                        required=False,
                        help='defines whether to re-download even if the cpsam model is '
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
            progress_string += f'downloading cpsam model...'
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
        # updating iterations (bytes num)
        self.iterations_num = get_url_content_length(CPSAM_MODEL_URL)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | bytes: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def download_cp_models(output_folder: str,
                       overwrite_output: bool,
                       progress_tracker: ModuleProgressTracker
                       ) -> None:
    """
    Given an output folder, downloads the Cellpose
    "cpsam" model weights into it (as "cpsam"),
    skipping the download if already present
    (unless overwrite_output is set).

    Args:
        output_folder (str): The folder to download the cpsam model into.
        overwrite_output (bool): Whether to re-download even if the model is already present.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting model path
    model_path = join(output_folder,
                      MODEL_FILENAME)

    # getting skip file bool
    skip_file = get_skip_file_bool(file_path=model_path,
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

    # downloading model weights (temp-file-then-rename, same atomicity Cellpose's own
    # download_url_to_file provided - see cet.setup.download_utils.download_file)
    download_file(url=CPSAM_MODEL_URL,
                  output_path=model_path,
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

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running download_cp_models function
    download_cp_models(output_folder=output_folder,
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
