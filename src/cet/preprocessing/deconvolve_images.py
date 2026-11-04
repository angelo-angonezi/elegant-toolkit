# deconvolve images module

print('initializing...')  # noqa

# Code destined to running
# deconvolution on images.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from tifffile import imread
from tifffile import imwrite
from pycudadecon import decon
from argparse import ArgumentParser
from cet.io.cli import get_scales_dict
from cet.io.files import get_skip_file_bool
from cet.io.files import get_files_in_folder
from cet.constants import DEFAULT_SCALES_STR
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
    description = "deconvolve images module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing images [.tif]')

    # psf file param
    parser.add_argument('-p', '--psf-path',
                        dest='psf_path',
                        type=str,
                        required=True,
                        help='defines path to point spread function file [.tif]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain deconvolved images [.tif])')

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

    # wavelength param
    parser.add_argument('-w', '--wavelength',
                        dest='wavelength',
                        type=int,
                        required=False,
                        default=455,
                        help='defines wavelength')

    # numerical aperture param
    parser.add_argument('-n', '--numerical-aperture',
                        dest='numerical_aperture',
                        type=float,
                        required=False,
                        default=1.5,
                        help='defines numerical aperture')

    # refractive index param
    parser.add_argument('-r', '--refractive-index',
                        dest='refractive_index',
                        type=float,
                        required=False,
                        default=1.518,
                        help='defines refractive index')

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
            progress_string += f'deconvolving images...'
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


def deconvolve_image(input_path: str,
                     psf: ndarray,
                     xy_scale: float,
                     z_scale: float,
                     wavelength: int,
                     numerical_aperture: float,
                     refractive_index: float,
                     output_path: str
                     ) -> None:
    """
    Given a path to an image, runs
    deconvolution with specified
    parameters saving deconvolved image
    to given output path.

    Args:
        input_path (str): The path to the image to deconvolve.
        psf (ndarray): The point spread function array.
        xy_scale (float): The lateral (x/y) pixel scale, in microns.
        z_scale (float): The axial (z) pixel scale, in microns.
        wavelength (int): The wavelength.
        numerical_aperture (float): The numerical aperture.
        refractive_index (float): The refractive index.
        output_path (str): The path to save the deconvolved image to.

    Returns:
        None.
    """
    # reading image
    image = imread(input_path)

    # running deconvolution
    deconvolved_image = decon(images=image,
                              psf=psf,
                              dxpsf=xy_scale,
                              dxdata=xy_scale,
                              dzpsf=z_scale,
                              dzdata=z_scale,
                              wavelength=wavelength,
                              na=numerical_aperture,
                              nimm=refractive_index)

    # saving image
    imwrite(output_path,
            deconvolved_image)


def deconvolve_images(input_folder: str,
                      psf_path: str,
                      output_folder: str,
                      scales_dict: str,
                      wavelength: int,
                      numerical_aperture: float,
                      refractive_index: float,
                      overwrite_output: bool,
                      progress_tracker: ModuleProgressTracker
                      ) -> None:
    """
    Given a path to a folder containing
    images, runs deconvolution with
    specified parameters.

    Args:
        input_folder (str): The path to the folder containing images to deconvolve.
        psf_path (str): The path to the point spread function file.
        output_folder (str): The path to the folder to save deconvolved images to.
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        wavelength (int): The wavelength.
        numerical_aperture (float): The numerical aperture.
        refractive_index (float): The refractive index.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting files in input folder
    files = get_files_in_folder(input_folder=input_folder,
                                extension='.tif')

    # reading psf
    psf = imread(psf_path)

    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # getting specific distance weights for each axis
    z_scale = scales_dict['z']
    xy_scale = scales_dict['y']

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

        # deconvolving current image
        deconvolve_image(input_path=input_path,
                         psf=psf,
                         xy_scale=xy_scale,
                         z_scale=z_scale,
                         wavelength=wavelength,
                         numerical_aperture=numerical_aperture,
                         refractive_index=refractive_index,
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

    # getting psf path
    psf_path = args_dict['psf_path']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting wavelength
    wavelength = args_dict['wavelength']

    # getting numerical aperture
    numerical_aperture = args_dict['numerical_aperture']

    # getting refractive index
    refractive_index = args_dict['refractive_index']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running deconvolve_images function
    deconvolve_images(input_folder=input_folder,
                      psf_path=psf_path,
                      output_folder=output_folder,
                      scales_dict=scales_dict,
                      wavelength=wavelength,
                      numerical_aperture=numerical_aperture,
                      refractive_index=refractive_index,
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
