# resize masks module

print('initializing...')  # noqa

# Code destined to resizing segmentation
# masks (dilating or eroding).

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from argparse import ArgumentParser
from cet.io.images import save_image
from cet.io.images import load_image
from cet.io.cli import get_scales_dict
from cet.io.files import get_skip_file_bool
from cet.io.files import get_files_in_folder
from cet.constants import DEFAULT_SCALES_STR
from cet.measurements.labels import get_object_ids
from cet.segmentation.mask_ops import resize_labels
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
    description = "resize masks module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing segmentation masks [.tif]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain resized masks [.tif])')

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

    # distance param
    parser.add_argument('-d', '--distance',
                        dest='distance',
                        type=int,
                        required=False,
                        default=5,
                        help='defines distance (in pixels) for dilation/erosion of the masks')

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

        # defining current module specific attributes

        # image
        self.images_num = 0
        self.current_image = 0

        # operation
        self.current_operation = ''

        # distance
        self.distances_num = 0
        self.current_distance = 0

        # object
        self.objects_num = 0
        self.current_object = 0

        # iterations dict
        self.iterations_dict = {}

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
            progress_string += f' | images: {self.images_num}'
            progress_string += f' | distances: {self.distances_num}'
            progress_string += f' | objects: {self.objects_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'resizing masks...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_image}/{self.images_num}'
            progress_string += f' | operation: {self.current_operation}'
            progress_string += f' | distance: {self.current_distance}/{self.distances_num}'
            progress_string += f' | object: {self.current_object}/{self.objects_num}'
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

        # getting distance
        distance = args_dict['distance']

        # getting images
        images = get_files_in_folder(input_folder=input_folder,
                                     extension='.tif')

        # getting absolute distance value (avoids issues with range in case of negative distances)
        distance_abs = abs(distance)

        # updating progress tracker attributes
        self.distances_num = distance_abs

        # iterating over files
        for image_name in images:

            # updating progress tracker attributes
            self.images_num += 1

            # defining placeholder value for current iterations dict
            current_iterations_dict = {image_name: 0}

            # getting current image path
            input_path = join(input_folder,
                              image_name)

            # loading current mask
            mask = load_image(input_path=input_path)

            # getting distances range
            distances_range = range(distance_abs)

            # getting current mask object ids
            object_ids = get_object_ids(mask=mask)

            # getting current image object count (unique mask ids)
            objects_num = len(object_ids)

            # updating progress tracker attributes
            self.objects_num += objects_num

            # getting current image objects range
            objects_range = range(objects_num)

            # iterating over distances
            for _ in distances_range:

                # iterating over objects
                for _ in objects_range:

                    # updating progress tracker attributes
                    self.iterations_num += 1

                    # updating current iterations dict
                    current_iterations_dict[image_name] += 1

            # updating progress tracker attributes
            self.iterations_dict.update(current_iterations_dict)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | distances: {self.distances_num}'
        totals_string += f' | objects: {self.objects_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def resize_mask(input_path: str,
                scales_dict: dict,
                distance: int,
                output_path: str,
                progress_tracker: ModuleProgressTracker
                ) -> None:
    """
    Given a path to a segmentation mask,
    generates and saves resized mask.

    Returns:
        None.
    """
    # reading current image
    image = load_image(input_path=input_path)

    # dilating mask
    image = resize_labels(mask=image,
                          scales_dict=scales_dict,
                          distance=distance,
                          progress_tracker=progress_tracker)

    # saving image
    save_image(save_path=output_path,
               image=image)


def resize_masks(input_folder: str,
                 output_folder: str,
                 scales_dict: str,
                 distance: int,
                 overwrite_output: bool,
                 progress_tracker: ModuleProgressTracker
                 ) -> None:
    """
    Given a path to a folder containing
    segmentation masks, resizes masks,
    saving output to given folder.

    Returns:
        None.
    """
    # getting images in input folder
    images = get_files_in_folder(input_folder=input_folder,
                                 extension='.tif')

    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # getting progress tracker iterations dict
    iterations_dict = progress_tracker.iterations_dict

    # iterating over images in input folder
    for image_name in images:

        # updating progress tracker attributes
        progress_tracker.current_image += 1

        # getting current image iterations num
        current_iterations_num = iterations_dict[image_name]

        # getting current image input/output path
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
            progress_tracker.wait(0.05)

            # updating progress tracker attributes
            progress_tracker.current_iteration += current_iterations_num
            progress_tracker.skipped_iterations += current_iterations_num

            # skipping to next file
            continue

        # resizing current file masks
        resize_mask(input_path=input_path,
                    scales_dict=scales_dict,
                    distance=distance,
                    output_path=output_path,
                    progress_tracker=progress_tracker)


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

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting distance
    distance = args_dict['distance']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running resize_masks function
    resize_masks(input_folder=input_folder,
                 output_folder=output_folder,
                 scales_dict=scales_dict,
                 distance=distance,
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
