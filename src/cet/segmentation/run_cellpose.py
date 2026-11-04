# run cellpose module

print('initializing...')  # noqa

# Code destined to running cellpose
# via python pipelines.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from tifffile import imread
from tifffile import imwrite
from cet.config import DEVICE
from argparse import ArgumentParser
from cellpose.io import logger_setup
from cet.io.cli import get_scales_dict
from cellpose.models import CellposeModel
from cet.io.files import get_skip_file_bool
from cet.io.files import get_files_in_folder
from cet.constants import DEFAULT_SCALES_STR
from cet.constants import CELLPOSE_MODEL_PATH
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
    description = "run cellpose module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing images [.tif]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain segmentation masks [.tif])')

    # pretrained model param
    parser.add_argument('-p', '--pretrained-model',
                        dest='pretrained_model',
                        type=str,
                        required=False,
                        default=CELLPOSE_MODEL_PATH,
                        help=f'defines pretrained model to be used in inference (keyword or path) '
                             f'- defaults to "{CELLPOSE_MODEL_PATH}" (matches '
                             f'cet.pipelines.pipeline\'s own -p; run '
                             f'cet-download_cp_models to pre-fetch "cpsam" there, otherwise '
                             f'Cellpose falls back to its own per-user cache on first use)')

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

    # z axis param
    parser.add_argument('-z', '--z-axis',
                        dest='z_axis',
                        type=int,
                        required=False,
                        default=0,
                        help='defines z axis index (-1 for 2D images)')

    # diameter param
    parser.add_argument('-t', '--diameter',
                        dest='diameter',
                        type=int,
                        required=False,
                        default=None,
                        help='defines objects average diameter')

    # min size param
    parser.add_argument('-m', '--min-size',
                        dest='min_size',
                        type=int,
                        required=False,
                        default=3500,
                        help='defines objects minimum size')

    # batch size param
    parser.add_argument('-b', '--batch-size',
                        dest='batch_size',
                        type=int,
                        required=False,
                        default=8,
                        help='defines batch size')

    # verbose param
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        required=False,
                        help='defines whether to print cellpose log info')

    # overwrite output param
    parser.add_argument('-ow', '--overwrite-output',
                        dest='overwrite_output',
                        action='store_true',
                        required=False,
                        help='defines whether overwrite files in output folder (skips existing output by default)')

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
            progress_string += f' | images: {self.iterations_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'running cellpose...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_iteration}/{self.iterations_num}'
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

        Returns:
            None.
        """
        # getting input folder
        input_folder = args_dict['input_folder']

        # getting images
        images = get_files_in_folder(input_folder=input_folder,
                                     extension='.tif')

        # iterating over files
        for _ in images:

            # updating progress tracker attributes
            self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.iterations_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def segment_image(input_path: str,
                  model: CellposeModel,
                  anisotropy: float,
                  z_axis: int,
                  diameter: int | None,
                  min_size: int,
                  batch_size: int,
                  output_path: str
                  ) -> None:
    """
    Given a path to an image, runs
    cellpose with specified parameters
    saving output segmentation masks
    to given output path.

    Returns:
        None.
    """
    # reading image
    image = imread(input_path)

    # converting data types
    image = image.astype('float32')

    # getting image is 3d bool
    image_is_3d = (z_axis >= 0)

    # checking if image is 3d
    if image_is_3d:

        # running cellpose with 3d settings
        cellpose_results = model.eval(x=image,
                                      anisotropy=anisotropy,
                                      z_axis=z_axis,
                                      diameter=diameter,
                                      min_size=min_size,
                                      batch_size=batch_size,
                                      do_3D=True)

    else:

        # running cellpose with 2d settings
        cellpose_results = model.eval(x=image,
                                      diameter=diameter,
                                      min_size=min_size,
                                      batch_size=batch_size)

    # extracting cellpose results
    masks, flows, styles = cellpose_results

    # saving masks
    imwrite(output_path,
            masks)


def run_cellpose(input_folder: str,
                 output_folder: str,
                 pretrained_model: str,
                 scales_dict: str,
                 z_axis: int,
                 diameter: int | None,
                 min_size: int,
                 batch_size: int,
                 verbose: bool,
                 overwrite_output: bool,
                 progress_tracker: ModuleProgressTracker
                 ) -> None:
    """
    Given a path to a folder containing
    images, runs cellpose with specified
    parameters.

    Returns:
        None.
    """
    # getting files in input folder
    files = get_files_in_folder(input_folder=input_folder,
                                extension='.tif')

    # checking verbose toggle
    if verbose:

        # starting cellpose logging
        logger_setup()

    # loading model
    model = CellposeModel(pretrained_model=pretrained_model,
                          gpu=GPU,
                          device=DEVICE)

    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # getting specific distance weights for each axis
    z_scale = scales_dict['z']
    xy_scale = scales_dict['y']

    # calculating anisotropy
    anisotropy = z_scale / xy_scale

    # iterating over files in input folder
    for file_name in files:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1

        # getting current file input/output paths
        input_path = join(input_folder,
                          file_name)
        output_path = join(output_folder,
                           file_name)

        # getting skip file bool
        skip_file = get_skip_file_bool(file_path=output_path,
                                       overwrite_output=overwrite_output)

        # checking whether to skip current file
        if skip_file:

            # sleeping
            progress_tracker.wait(0.05)

            # updating progress tracker attributes
            progress_tracker.skipped_iterations += 1

            # skipping to next file
            continue

        # segmenting current image
        segment_image(input_path=input_path,
                      model=model,
                      anisotropy=anisotropy,
                      z_axis=z_axis,
                      diameter=diameter,
                      min_size=min_size,
                      batch_size=batch_size,
                      output_path=output_path)


def parse_and_run(args_dict: dict,
                  progress_tracker: ModuleProgressTracker
                  ) -> None:
    """
    Extracts args from args_dict
    and runs module function.

    Returns:
        None.
    """
    # getting input folder
    input_folder = args_dict['input_folder']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting pretrained model
    pretrained_model = args_dict['pretrained_model']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting z axis
    z_axis = args_dict['z_axis']

    # getting diameter
    diameter = args_dict['diameter']

    # getting min size
    min_size = args_dict['min_size']

    # getting batch size
    batch_size = args_dict['batch_size']

    # getting verbose
    verbose = args_dict['verbose']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running run_cellpose function
    run_cellpose(input_folder=input_folder,
                 output_folder=output_folder,
                 pretrained_model=pretrained_model,
                 scales_dict=scales_dict,
                 z_axis=z_axis,
                 diameter=diameter,
                 min_size=min_size,
                 batch_size=batch_size,
                 verbose=verbose,
                 overwrite_output=overwrite_output,
                 progress_tracker=progress_tracker)

######################################################################
# defining main function


def main():
    """Runs main code."""
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
