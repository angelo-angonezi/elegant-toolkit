# create psf module

print('initializing...')  # noqa

# Code destined to generating a synthetic
# point spread function (PSF), based on
# microscope optical parameters.

######################################################################
# imports

print('importing required libraries...')  # noqa
from torch import Tensor
from os.path import join
from numpy import ndarray
from cet.config import DEVICE
from functools import partial
from argparse import ArgumentParser
from cet.io.images import save_image
from cet.io.cli import get_scales_dict
from cet.io.files import get_skip_file_bool
from cet.constants import DEFAULT_SCALES_STR
from psf_generator.propagators.propagator import Propagator
from psf_generator.utils.misc import convert_tensor_to_array
from cet.progress_tracker.ProgressTracker import ProgressTracker
from psf_generator.propagators.scalar_cartesian_propagator import ScalarCartesianPropagator
from psf_generator.propagators.scalar_spherical_propagator import ScalarSphericalPropagator
from psf_generator.propagators.vectorial_cartesian_propagator import VectorialCartesianPropagator
from psf_generator.propagators.vectorial_spherical_propagator import VectorialSphericalPropagator
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global parameters

# defining default vectorial polarization (circular polarization,
# approximating an unpolarized fluorescence emitter)
E0X = (2 ** 0.5) / 2
E0Y = E0X * 1j

######################################################################
# argument parsing related functions


def get_wavelengths_list(wavelength_str: str) -> list:
    """
    Given a string of comma-separated
    wavelengths, returns a list of ints.

    Args:
        wavelength_str (str): A string containing wavelength(s) separated by commas.

    Returns:
        list: A list of wavelengths (ints).
    """
    # splitting wavelength string
    wavelength_split = wavelength_str.split(',')

    # converting data types
    wavelengths_list = [int(wavelength.strip()) for wavelength in wavelength_split if wavelength.strip()]

    # returning wavelengths list
    return wavelengths_list


def get_args_dict() -> dict:
    """
    Parses command-line arguments and returns
    them as a dictionary.

    Returns:
        dict: A dictionary containing all parsed command-line arguments.
    """
    # defining program description
    description = "create psf module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines path to output folder to save point spread function file(s) [.tif] to')

    # wavelength param
    parser.add_argument('-w', '--wavelength',
                        dest='wavelength',
                        type=str,
                        required=False,
                        default='455',
                        help='defines wavelength(s) (comma-separated list, e.g. "405,561,640")')

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

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

    # psf xy size param
    parser.add_argument('-xy', '--psf-size-xy',
                        dest='psf_size_xy',
                        type=int,
                        required=False,
                        default=255,
                        help='defines lateral (x/y) size of point spread function, in pixels')

    # psf z size param
    parser.add_argument('-z', '--psf-size-z',
                        dest='psf_size_z',
                        type=int,
                        required=False,
                        default=65,
                        help='defines axial (z) size (number of planes) of point spread function, in pixels')

    # model param
    parser.add_argument('-md', '--model',
                        dest='model',
                        type=str,
                        required=False,
                        default='vectorial_spherical',
                        help='defines point spread function model ("scalar_cartesian", "scalar_spherical", "vectorial_cartesian" or "vectorial_spherical")')

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
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'creating psfs...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | wavelength: {self.current_iteration}/{self.iterations_num}'
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
        # getting wavelength
        wavelength = args_dict['wavelength']

        # getting wavelengths list
        wavelengths_list = get_wavelengths_list(wavelength_str=wavelength)

        # iterating over wavelengths
        for _ in wavelengths_list:

            # updating progress tracker attributes
            self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | wavelengths: {self.iterations_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_psf_intensity(field: Tensor) -> ndarray:
    """
    Given a propagator's output field
    (complex tensor, of shape
    z,component,x,y), returns intensity
    array (sum of squared component
    magnitudes, converted to numpy).

    Args:
        field (Tensor): The propagator's output field.

    Returns:
        ndarray: The computed intensity array.
    """
    # squaring field magnitude (per component)
    squared_field = (field.abs() ** 2)

    # summing components (scalar models have a single component; vectorial models have 3)
    intensity = squared_field.sum(dim=1)

    # converting data type
    intensity = convert_tensor_to_array(intensity)

    # returning intensity array
    return intensity


def get_propagator(model: str,
                   n_pix_pupil: int,
                   n_pix_psf: int,
                   device: str,
                   wavelength: int,
                   numerical_aperture: float,
                   pix_size: float,
                   defocus_step: float,
                   n_defocus: int,
                   refractive_index: float
                   ) -> Propagator:
    """
    Given a model name and propagator
    parameters, returns initialized
    propagator instance.

    Args:
        model (str): The point spread function model ("scalar_cartesian", "scalar_spherical", "vectorial_cartesian" or "vectorial_spherical").
        n_pix_pupil (int): The number of pupil pixels.
        n_pix_psf (int): The number of point spread function pixels.
        device (str): The device to run the propagator on.
        wavelength (int): The wavelength.
        numerical_aperture (float): The numerical aperture.
        pix_size (float): The lateral pixel size, in nanometers.
        defocus_step (float): The axial defocus step, in nanometers.
        n_defocus (int): The number of defocus planes.
        refractive_index (float): The refractive index.

    Returns:
        Propagator: The initialized propagator instance.

    Raises:
        Exception: If model is not a recognized propagator name.
    """
    # assembling common propagator kwargs
    common_kwargs = {'n_pix_pupil': n_pix_pupil,
                     'n_pix_psf': n_pix_psf,
                     'device': device,
                     'wavelength': wavelength,
                     'na': numerical_aperture,
                     'pix_size': pix_size,
                     'defocus_step': defocus_step,
                     'n_defocus': n_defocus,
                     'n_i': refractive_index}

    # assembling propagators dict (mapping model name to propagator class)
    propagators_dict = {'scalar_cartesian': ScalarCartesianPropagator,
                        'scalar_spherical': ScalarSphericalPropagator,
                        'vectorial_cartesian': partial(VectorialCartesianPropagator, e0x=E0X, e0y=E0Y),
                        'vectorial_spherical': partial(VectorialSphericalPropagator, e0x=E0X, e0y=E0Y)}

    # getting current propagator class
    propagator_class = propagators_dict.get(model)

    # checking if model is valid
    if propagator_class is None:

        # defining error message
        e_string = f'Invalid model "{model}".\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # initializing propagator
    propagator = propagator_class(**common_kwargs)

    # returning propagator
    return propagator


def create_psf(output_folder: str,
               wavelength: int,
               numerical_aperture: float,
               refractive_index: float,
               scales_dict: str,
               psf_size_xy: int,
               psf_size_z: int,
               model: str,
               overwrite_output: bool,
               progress_tracker: ModuleProgressTracker
               ) -> None:
    """
    Given point spread function
    parameters, generates and saves
    synthetic point spread function to
    given output folder.

    Args:
        output_folder (str): The path to the folder to save the point spread function file to.
        wavelength (int): The wavelength.
        numerical_aperture (float): The numerical aperture.
        refractive_index (float): The refractive index.
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        psf_size_xy (int): The lateral (x/y) size of the point spread function, in pixels.
        psf_size_z (int): The axial (z) size (number of planes) of the point spread function, in pixels.
        model (str): The point spread function model.
        overwrite_output (bool): Whether to overwrite an existing output file.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # assembling current output path
    output_path = join(output_folder,
                       f'psf_{wavelength}.tif')

    # getting skip file bool
    skip_file = get_skip_file_bool(file_path=output_path,
                                   overwrite_output=overwrite_output)

    # checking whether to skip current file
    if skip_file:

        # sleeping
        progress_tracker.wait(0.05)

        # updating progress tracker attributes
        progress_tracker.skipped_iterations += 1

        # skipping current file
        return

    # updating progress tracker attributes
    progress_tracker.current_iteration += 1

    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # converting scales from microns to nanometers (psf_generator convention)
    pix_size = (scales_dict['x'] * 1000)
    defocus_step = (scales_dict['z'] * 1000)

    # getting current device
    device = str(DEVICE)

    # getting propagator instance
    propagator = get_propagator(model=model,
                                n_pix_pupil=psf_size_xy,
                                n_pix_psf=psf_size_xy,
                                device=device,
                                wavelength=wavelength,
                                numerical_aperture=numerical_aperture,
                                pix_size=pix_size,
                                defocus_step=defocus_step,
                                n_defocus=psf_size_z,
                                refractive_index=refractive_index)

    # computing focus field
    field = propagator.compute_focus_field()

    # getting psf intensity
    psf = get_psf_intensity(field=field)

    # saving psf
    save_image(save_path=output_path,
               image=psf)


def create_psfs(output_folder: str,
                wavelength: str,
                numerical_aperture: float,
                refractive_index: float,
                scales_dict: str,
                psf_size_xy: int,
                psf_size_z: int,
                model: str,
                overwrite_output: bool,
                progress_tracker: ModuleProgressTracker
                ) -> None:
    """
    Given point spread function
    parameters, generates and saves
    one synthetic point spread function
    file per wavelength, to given
    output folder.

    Args:
        output_folder (str): The path to the folder to save the point spread function file(s) to.
        wavelength (str): A string containing wavelength(s) separated by commas.
        numerical_aperture (float): The numerical aperture.
        refractive_index (float): The refractive index.
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        psf_size_xy (int): The lateral (x/y) size of the point spread function, in pixels.
        psf_size_z (int): The axial (z) size (number of planes) of the point spread function, in pixels.
        model (str): The point spread function model.
        overwrite_output (bool): Whether to overwrite an existing output file.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting wavelengths list
    wavelengths_list = get_wavelengths_list(wavelength_str=wavelength)

    # iterating over wavelengths list
    for current_wavelength in wavelengths_list:

        # creating psf for current wavelength
        create_psf(output_folder=output_folder,
                  wavelength=current_wavelength,
                  numerical_aperture=numerical_aperture,
                  refractive_index=refractive_index,
                  scales_dict=scales_dict,
                  psf_size_xy=psf_size_xy,
                  psf_size_z=psf_size_z,
                  model=model,
                  overwrite_output=overwrite_output,
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

    # getting wavelength
    wavelength = args_dict['wavelength']

    # getting numerical aperture
    numerical_aperture = args_dict['numerical_aperture']

    # getting refractive index
    refractive_index = args_dict['refractive_index']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting psf xy size
    psf_size_xy = args_dict['psf_size_xy']

    # getting psf z size
    psf_size_z = args_dict['psf_size_z']

    # getting model
    model = args_dict['model']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running create_psfs function
    create_psfs(output_folder=output_folder,
               wavelength=wavelength,
               numerical_aperture=numerical_aperture,
               refractive_index=refractive_index,
               scales_dict=scales_dict,
               psf_size_xy=psf_size_xy,
               psf_size_z=psf_size_z,
               model=model,
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
