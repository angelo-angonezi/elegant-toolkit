# preprocess images module

print('initializing...')  # noqa

# Code destined to preprocessing
# image pixel intensities.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from argparse import ArgumentParser
from cet.io.images import load_image
from cet.io.images import save_image
from cet.io.dataframes import load_df
from cet.io.files import get_skip_file_bool
from cet.preprocessing.image_ops import remove_bg
from cet.preprocessing.image_ops import rescale_by_reference
from cet.preprocessing.image_ops import normalize_by_reference
from cet.progress_tracker.ProgressTracker import ProgressTracker

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
else:
    from numpy import ndarray

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
    description = "preprocess images module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing images [.tif]')

    # images df path param
    parser.add_argument('-d', '--images-df-path',
                        dest='images_df_path',
                        type=str,
                        required=True,
                        help='defines path to images df [.csv]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain rescaled images [.tif])')

    # image name col param
    parser.add_argument('-n', '--image-name-col',
                        dest='image_name_col',
                        type=str,
                        required=False,
                        default='image_name',
                        help='defines column in images df containing image names')

    # operation param
    parser.add_argument('-r', '--operation',
                        dest='operation',
                        type=str,
                        required=False,
                        default='remove_bg',
                        help='defines operation to be performed (remove_bg/rescale/normalize)')

    # reference col param
    parser.add_argument('-c', '--reference-col',
                        dest='reference_col',
                        type=str,
                        required=False,
                        default='background_mean_intensity',
                        help='defines col name in images df path to be used as base for rescaling/normalization')

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
            progress_string += f'preprocessing images...'
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
        # getting images df path
        images_df_path = args_dict['images_df_path']

        # loading df
        images_df = load_df(input_path=images_df_path)

        # getting df rows num/range
        df_rows_num = len(images_df)
        df_rows_range = range(df_rows_num)

        # iterating over df rows
        for _ in df_rows_range:

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


def process_image(image: ndarray,
                  operation: str,
                  reference_value: int | float
                  ) -> ndarray:
    """
    Given an image, runs specified
    operation using reference value,
    returning processed image.

    Args:
        image (ndarray): The image to process.
        operation (str): The operation to perform ("remove_bg"/"rescale"/"normalize").
        reference_value (int | float): The reference value to use in the operation.

    Returns:
        ndarray: The processed image.

    Raises:
        Exception: If operation is not a recognized operation type.
    """
    # assembling operations dict
    operation_funcs = {'remove_bg': remove_bg,
                       'rescale': rescale_by_reference,
                       'normalize': normalize_by_reference}

    # getting valid function names
    valid_funcs = operation_funcs.keys()
    valid_funcs = list(valid_funcs)

    # getting operation function
    operation_func = operation_funcs.get(operation)

    # checking if operation is valid
    if operation_func is None:

        # defining error message
        e_string = f'Invalid operation "{operation}".\n'
        e_string += f'Valid operations: {valid_funcs}\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # getting processed image
    processed_image = operation_func(image=image,
                                     reference_value=reference_value)

    # returning processed image
    return processed_image


def preprocess_image(input_path: str,
                     operation: str,
                     reference_value: int | float,
                     output_path: str
                     ) -> None:
    """
    Given a path to an image, runs
    specified operation for bg removal/
    rescaling/normalization, saving
    results to given output path.

    Args:
        input_path (str): The path to the image to process.
        operation (str): The operation to perform ("remove_bg"/"rescale"/"normalize").
        reference_value (int | float): The reference value to use in the operation.
        output_path (str): The path to save the processed image to.

    Returns:
        None.
    """
    # loading current image
    image = load_image(input_path=input_path)

    # converting data types
    image = image.astype('float32')

    # getting processed image
    image = process_image(image=image,
                          operation=operation,
                          reference_value=reference_value)

    # converting data types
    image = image.astype('uint16')

    # saving image
    save_image(save_path=output_path,
               image=image)


def preprocess_images(input_folder: str,
                      images_df_path: str,
                      output_folder: str,
                      image_name_col: str,
                      operation: str,
                      reference_col: str,
                      overwrite_output: bool,
                      progress_tracker: ModuleProgressTracker
                      ) -> None:
    """
    Given a path to a folder containing
    images, runs specified operation for
    bg removal/rescaling/normalization,
    saving results to given output
    folder.

    Args:
        input_folder (str): The path to the folder containing images to process.
        images_df_path (str): The path to the images df.
        output_folder (str): The path to the folder to save processed images to.
        image_name_col (str): The column in the images df containing image names.
        operation (str): The operation to perform ("remove_bg"/"rescale"/"normalize").
        reference_col (str): The column in the images df to use as the reference value.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # loading df
    images_df = load_df(input_path=images_df_path)

    # getting df rows
    df_rows = images_df.iterrows()

    # iterating over df rows
    for row_index, row_data in df_rows:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1

        # getting current row info
        image_name = row_data[image_name_col]

        # getting current reference value
        reference_value = row_data[reference_col]

        # getting current input/output paths
        input_path = join(input_folder,
                          image_name)
        output_path = join(output_folder,
                           image_name)

        # getting skip file bool
        skip_file = get_skip_file_bool(file_path=output_path,
                                       overwrite_output=overwrite_output)

        # checking whether to skip current file
        if skip_file:

            # sleeping
            progress_tracker.wait(0.001)

            # updating progress tracker attributes
            progress_tracker.skipped_iterations += 1

            # skipping to next file
            continue

        # preprocessing current image
        preprocess_image(input_path=input_path,
                         operation=operation,
                         reference_value=reference_value,
                         output_path=output_path)


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

    # getting images df path
    images_df_path = args_dict['images_df_path']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting image name col
    image_name_col = args_dict['image_name_col']

    # getting operation
    operation = args_dict['operation']

    # getting rescale col
    reference_col = args_dict['reference_col']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running preprocess_images function
    preprocess_images(input_folder=input_folder,
                      images_df_path=images_df_path,
                      output_folder=output_folder,
                      image_name_col=image_name_col,
                      operation=operation,
                      reference_col=reference_col,
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
