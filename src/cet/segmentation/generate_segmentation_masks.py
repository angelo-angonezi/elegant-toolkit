# generate segmentation masks module

print('initializing...')  # noqa

# Code destined to generating
# segmentation masks based on
# previously created binary masks.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from argparse import ArgumentParser
from cet.io.images import save_image
from cet.io.images import load_image
from cet.io.files import get_skip_file_bool
from cet.io.files import get_files_in_folder
from cet.progress_tracker.ProgressTracker import ProgressTracker

# doing conditional imports depending on gpu availability

if GPU:
    from cupyx.scipy.ndimage import label
else:
    from scipy.ndimage import label

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
    description = "generate segmentation masks module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing binary masks [.tif]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain segmentation masks [.tif])')

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
            progress_string += f'generating masks...'
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

        Args:
            args_dict (dict): A dictionary containing all parsed command-line arguments.

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


def generate_segmentation_mask(input_path: str,
                               output_path: str
                               ) -> None:
    """
    Generate and save a segmentation mask
    from a binary mask.

    Args:
        input_path (str): Path to binary mask file.
        output_path (str): Path to save segmentation mask.

    Returns:
        None.
    """
    # reading current image mask
    binary_mask = load_image(input_path=input_path)

    # getting current mask ids
    segmentation_mask, _ = label(binary_mask)

    # converting segmentation mask to 16bit
    segmentation_mask = segmentation_mask.astype('uint16')

    # saving updated image
    save_image(save_path=output_path,
               image=segmentation_mask)


def generate_segmentation_masks(input_folder: str,
                                output_folder: str,
                                overwrite_output: bool,
                                progress_tracker: ModuleProgressTracker
                                ) -> None:
    """
    Generate segmentation masks from binary
    masks in input folder.

    Args:
        input_folder (str): Path to folder containing binary masks.
        output_folder (str): Path to folder for segmentation masks.
        overwrite_output (bool): Whether to overwrite existing output.
        progress_tracker (ModuleProgressTracker): Progress tracking instance.

    Returns:
        None.
    """
    # getting images in input folder
    images = get_files_in_folder(input_folder=input_folder,
                                 extension='.tif')

    # iterating over images in input folder
    for image_name in images:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1

        # getting current image input/output paths
        current_input_path = join(input_folder,
                                  image_name)
        current_output_path = join(output_folder,
                                   image_name)

        # getting skip file bool
        skip_file = get_skip_file_bool(file_path=current_output_path,
                                       overwrite_output=overwrite_output)

        # checking whether to skip current file
        if skip_file:

            # sleeping
            progress_tracker.wait(0.05)

            # updating progress tracker attributes
            progress_tracker.skipped_iterations += 1

            # skipping to next file
            continue

        # generating segmentation mask for current image
        generate_segmentation_mask(input_path=current_input_path,
                                   output_path=current_output_path)


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
    # getting input folder
    input_folder = args_dict['input_folder']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_segmentation_masks function
    generate_segmentation_masks(input_folder=input_folder,
                                output_folder=output_folder,
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
