# generate binary masks module

print('initializing...')  # noqa

# Code destined to generating
# binary masks based on a pixel
# intensity threshold.

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
    from cupy import ndarray
    from cupy import quantile
    from cupy import max as arr_max
    from cupy import std as arr_std
    from cupy import mean as arr_mean
    from cupy import median as arr_median
else:
    from numpy import ndarray
    from numpy import quantile
    from numpy import max as arr_max
    from numpy import std as arr_std
    from numpy import mean as arr_mean
    from numpy import median as arr_median

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
    description = "generate binary masks module"

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
                        help='defines output folder (folder that will contain binary masks [.tif])')

    # mode param
    parser.add_argument('-m', '--mode',
                        dest='mode',
                        type=str,
                        required=False,
                        default='binary',
                        help='defines method to be used for thresholding (binary, mean, median, std, quantile)')

    # lower threshold param
    parser.add_argument('-lt', '--lower-threshold',
                        dest='lower_threshold',
                        type=float,
                        required=False,
                        default=1.0,
                        help='defines lower threshold to be used in mask generation (if binary, raw pixel value, if other, will be used as multiplier/quantile)')

    # upper threshold param
    parser.add_argument('-ut', '--upper-threshold',
                        dest='upper_threshold',
                        type=float,
                        required=False,
                        default=-1.0,  # does not apply upper threshold
                        help='defines upper threshold to be used in mask generation (if binary, raw pixel value, if other, will be used as multiplier [turn off with -1])')

    # positives only param
    parser.add_argument('-p', '--positives-only',
                        dest='positives_only',
                        action='store_true',
                        required=False,
                        help='defines whether to disconsider negative values when computing mean, median, quantile etc (useful for DoG images)')

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


def get_binary_thresholds(image: ndarray,
                          lower_threshold: float,
                          upper_threshold: float
                          ) -> tuple:
    """
    Calculate thresholds based on binary
    threshold values.

    Args:
        image (ndarray): Input image array.
        lower_threshold (float): Lower threshold value.
        upper_threshold (float): Upper threshold value.

    Returns:
        tuple: Updated threshold values.
    """
    # getting image maximum value
    image_max = arr_max(image)

    # extracting value from array
    image_max = image_max.item()

    # updating thresholds
    lower_threshold = lower_threshold if lower_threshold < image_max else image_max
    upper_threshold = upper_threshold if upper_threshold < image_max else image_max

    # assembling updated thresholds tuple
    thresholds = (lower_threshold, upper_threshold)

    # returning updated thresholds tuple
    return thresholds


def get_mean_thresholds(image: ndarray,
                        lower_threshold: float,
                        upper_threshold: float
                        ) -> tuple:
    """
    Calculate thresholds based on image
    mean value.

    Args:
        image (ndarray): Input image array.
        lower_threshold (float): Lower threshold multiplier.
        upper_threshold (float): Upper threshold multiplier.

    Returns:
        tuple: Updated threshold values.
    """
    # getting image mean value
    image_mean = arr_mean(image)

    # extracting value from array
    image_mean = image_mean.item()

    # updating thresholds
    lower_threshold *= image_mean
    upper_threshold *= image_mean

    # assembling updated thresholds tuple
    thresholds = (lower_threshold, upper_threshold)

    # returning updated thresholds tuple
    return thresholds


def get_median_thresholds(image: ndarray,
                          lower_threshold: float,
                          upper_threshold: float
                          ) -> tuple:
    """
    Calculate thresholds based on image
    median value.

    Args:
        image (ndarray): Input image array.
        lower_threshold (float): Lower threshold multiplier.
        upper_threshold (float): Upper threshold multiplier.

    Returns:
        tuple: Updated threshold values.
    """
    # getting image median value
    image_median = arr_median(image)

    # extracting value from array
    image_median = image_median.item()

    # updating thresholds
    lower_threshold *= image_median
    upper_threshold *= image_median

    # assembling updated thresholds tuple
    thresholds = (lower_threshold, upper_threshold)

    # returning updated thresholds tuple
    return thresholds


def get_std_thresholds(image: ndarray,
                       lower_threshold: float,
                       upper_threshold: float
                       ) -> tuple:
    """
    Calculate thresholds based on image
    mean and standard deviation.

    Args:
        image (ndarray): Input image array.
        lower_threshold (float): Lower threshold std multiplier.
        upper_threshold (float): Upper threshold std multiplier.

    Returns:
        tuple: Updated threshold values.
    """
    # getting image mean/std values
    image_mean = arr_mean(image)
    image_std = arr_std(image)

    # extracting values from arrays
    image_mean = image_mean.item()
    image_std = image_std.item()

    # updating thresholds
    lower_threshold = image_mean + (image_std * lower_threshold)
    upper_threshold = image_mean + (image_std * upper_threshold)

    # assembling updated thresholds tuple
    thresholds = (lower_threshold, upper_threshold)

    # returning updated thresholds tuple
    return thresholds


def get_quantile_thresholds(image: ndarray,
                            lower_threshold: float,
                            upper_threshold: float
                            ) -> tuple:
    """
    Calculate thresholds based on image
    quantile values.

    Args:
        image (ndarray): Input image array.
        lower_threshold (float): Lower quantile value.
        upper_threshold (float): Upper quantile value.

    Returns:
        tuple: Updated threshold values.
    """
    # getting image lower quantile / updating threshold
    lower_threshold = quantile(image, lower_threshold)

    # getting uppper threshold bool
    apply_upper_threshold = (upper_threshold != -1)

    # checking whether to apply upper threshold
    if apply_upper_threshold:

        # getting image upper quantile / updating threshold
        upper_threshold = quantile(image, upper_threshold)

    # assembling updated thresholds tuple
    thresholds = (lower_threshold, upper_threshold)

    # returning updated thresholds tuple
    return thresholds


def get_thresholds(image: ndarray,
                   mode: str,
                   lower_threshold: float,
                   upper_threshold: float,
                   positives_only: bool
                   ) -> tuple:
    """
    Calculate thresholds based on specified
    mode and input image statistics.

    Args:
        image (ndarray): Input image array.
        mode (str): Thresholding mode (binary, mean, median, std, quantile).
        lower_threshold (float): Lower threshold value.
        upper_threshold (float): Upper threshold value.
        positives_only (bool): Whether to ignore negative values.

    Returns:
        tuple: Updated threshold values.
    """
    # checking whether to disconsider negative values
    if positives_only:

        # filtering negative values
        image = image[image > 0]

    # assembling thresholds funcs dict
    thresholds_funcs = {'binary': get_binary_thresholds,
                        'mean': get_mean_thresholds,
                        'median': get_median_thresholds,
                        'std': get_std_thresholds,
                        'quantile': get_quantile_thresholds}

    # getting valid function names
    valid_funcs = thresholds_funcs.keys()
    valid_funcs = list(valid_funcs)

    # getting threshold function
    threshold_func = thresholds_funcs.get(mode)

    # checking if normalization is valid
    if threshold_func is None:

        # defining error message
        e_string = f'Invalid threshold "{mode}".\n'
        e_string += f'Valid thresholds: {valid_funcs}\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # getting thresholds
    thresholds = threshold_func(image=image,
                                lower_threshold=lower_threshold,
                                upper_threshold=upper_threshold)

    # returning thresholds
    return thresholds


def generate_binary_mask(input_path: str,
                         mode: str,
                         lower_threshold: int | float,
                         upper_threshold: int | float,
                         positives_only: bool,
                         output_path: str
                         ) -> None:
    """
    Generate a binary mask from an image
    using specified thresholding mode.

    Args:
        input_path (str): Path to input image file.
        mode (str): Thresholding mode.
        lower_threshold (int | float): Lower threshold value.
        upper_threshold (int | float): Upper threshold value.
        positives_only (bool): Whether to ignore negative values.
        output_path (str): Path to save binary mask.

    Returns:
        None.
    """
    # reading current image
    image = load_image(input_path=input_path)

    # converting data types
    image = image.astype('float32')

    # getting thresholds
    lower_threshold, upper_threshold = get_thresholds(image=image,
                                                      mode=mode,
                                                      lower_threshold=lower_threshold,
                                                      upper_threshold=upper_threshold,
                                                      positives_only=positives_only)

    # getting uppper threshold bool
    apply_upper_threshold = (upper_threshold != -1)

    # checking whether to apply upper threshold
    if apply_upper_threshold:

        # applying upper threshold (discards pixels with higher intensity than threshold)
        image[image > upper_threshold] = 0

    # applying lower threshold
    image[image < lower_threshold] = 0

    # setting filtered pixels to 255
    image[image >= lower_threshold] = 255

    # converting image to 8bit
    image = image.astype('uint8')

    # saving image
    save_image(save_path=output_path,
               image=image)


def generate_binary_masks(input_folder: str,
                          output_folder: str,
                          mode: str,
                          lower_threshold: int | float,
                          upper_threshold: int | float,
                          positives_only: bool,
                          overwrite_output: bool,
                          progress_tracker: ModuleProgressTracker
                          ) -> None:
    """
    Generate binary masks from all images
    in input folder using specified mode.

    Args:
        input_folder (str): Path to folder containing images.
        output_folder (str): Path to folder for binary masks.
        mode (str): Thresholding mode.
        lower_threshold (int | float): Lower threshold value.
        upper_threshold (int | float): Upper threshold value.
        positives_only (bool): Whether to ignore negative values.
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

        # generating binary mask for current image
        generate_binary_mask(input_path=current_input_path,
                             mode=mode,
                             lower_threshold=lower_threshold,
                             upper_threshold=upper_threshold,
                             positives_only=positives_only,
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

    # getting mode
    mode = args_dict['mode']

    # getting lower threshold
    lower_threshold = args_dict['lower_threshold']

    # getting upper threshold
    upper_threshold = args_dict['upper_threshold']

    # getting positives only
    positives_only = args_dict['positives_only']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_binary_masks function
    generate_binary_masks(input_folder=input_folder,
                          output_folder=output_folder,
                          mode=mode,
                          lower_threshold=lower_threshold,
                          upper_threshold=upper_threshold,
                          positives_only=positives_only,
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
