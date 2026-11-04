# crop images module

print('initializing...')  # noqa

# Code destined to cropping images
# of generic objects (embryos, nuclei, dots, etc.), based on either
# an objects df's boundaries or a fixed size centered on each centroid.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.images import load_image
from cet.io.images import save_image
from cet.io.dataframes import load_df
from cet.io.files import get_skip_file_bool
from cet.segmentation.mask_ops import filter_mask
from cet.segmentation.mask_ops import crop_object
from cet.measurements.position import string_to_coords
from cet.measurements.position import get_centroid_boundaries
from cet.progress_tracker.ProgressTracker import ProgressTracker

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import pad
else:
    from numpy import pad

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
    description = "crop images module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing images [.tif]')

    # objects df path param
    parser.add_argument('-d', '--objects-df-path',
                        dest='objects_df_path',
                        type=str,
                        required=True,
                        help='defines path to objects df [.csv]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines path to output folder (folder that will contain image crops [.tif])')

    # margin param
    parser.add_argument('-m', '--margin',
                        dest='margin',
                        type=int,
                        required=False,
                        default=0,
                        help='defines margin (in pixels) to be applied in crop boundaries')

    # mask param
    parser.add_argument('-k', '--mask',
                        dest='mask',
                        action='store_true',
                        required=False,
                        help='defines whether images being cropped are masks (crops will only contain pixels matching object_id)')

    # fixed size param
    parser.add_argument('-f', '--fixed-size',
                        dest='fixed_size',
                        type=str,
                        required=False,
                        default=None,
                        help='defines whether to crop all images in a fixed size (z,y,x) based on centroid (overrides df boundaries)')

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

        # crop
        self.crops_num = 0
        self.current_crop = 0

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
            progress_string += f' | crops: {self.crops_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'cropping images...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_image}/{self.images_num}'
            progress_string += f' | crop: {self.current_crop}/{self.crops_num}'
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
        # getting objects df path
        objects_df_path = args_dict['objects_df_path']

        # loading df
        df = load_df(input_path=objects_df_path)

        # defining group cols
        group_cols = ['image_name',
                      'image_index']

        # grouping df
        df_groups = df.groupby(group_cols)

        # iterating over df groups
        for _, df_group in df_groups:

            # updating progress tracker attributes
            self.images_num += 1

            # getting df rows num/range
            df_rows_num = len(df_group)
            df_rows_range = range(df_rows_num)

            # iterating over df rows
            for _ in df_rows_range:

                # updating progress tracker attributes
                self.crops_num += 1
                self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | crops: {self.crops_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_fixed_size_pad_widths(boundaries: tuple,
                              margin: int,
                              image_shape: tuple
                              ) -> tuple:
    """
    Given raw (pre-margin, pre-clamp)
    crop boundaries, a margin, and the
    source image's shape, returns the
    (before, after) pad widths needed
    per axis (z, y, x) to bring a
    clamped crop back up to the
    originally requested fixed size.

    Args:
        boundaries (tuple): The raw (pre-margin, pre-clamp) crop boundaries.
        margin (int): The margin (in pixels) to apply to crop boundaries.
        image_shape (tuple): The source image's shape.

    Returns:
        tuple: The (before, after) pad widths needed per axis (z, y, x).
    """
    # extracting coords from boundaries
    z_min, z_max, y_min, y_max, x_min, x_max = boundaries

    # extracting axis maxes from image shape
    z_axis_max, y_axis_max, x_axis_max = image_shape[:3]

    # getting pad widths needed on each side (zero unless requested boundary exceeds image bounds)
    z_pad_widths = (max(0, margin - z_min), max(0, (z_max + margin) - z_axis_max))
    y_pad_widths = (max(0, margin - y_min), max(0, (y_max + margin) - y_axis_max))
    x_pad_widths = (max(0, margin - x_min), max(0, (x_max + margin) - x_axis_max))

    # assembling pad widths tuple
    pad_widths = (z_pad_widths, y_pad_widths, x_pad_widths)

    # returning pad widths
    return pad_widths


def crop_objects(input_path: str,
                 df: DataFrame,
                 margin: int,
                 mask: bool,
                 output_folder: str,
                 fixed_size: str | None,
                 overwrite_output: bool,
                 progress_tracker: ModuleProgressTracker
                 ) -> None:
    """
    Given a path to an image, and its
    respective objects df group, saves
    each object crop in given output
    folder.

    Args:
        input_path (str): The path to the image to crop.
        df (DataFrame): The objects df group for the current image.
        margin (int): The margin (in pixels) to apply to crop boundaries.
        mask (bool): Whether the image being cropped is a mask (crops will only contain pixels matching object_id).
        output_folder (str): The path to the folder to save crops to.
        fixed_size (str | None): The fixed crop size (z,y,x), or None to use df boundaries.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # loading image
    image = load_image(input_path=input_path)

    # getting image dimensions num
    image_dims = image.ndim

    # getting image is multichannel bool
    image_is_multichannel = (image_dims == 4)

    # getting df rows
    df_rows = df.iterrows()

    # getting crops num
    crops_num = len(df)

    # updating progress tracker attributes
    progress_tracker.crops_num = crops_num

    # resetting progress tracker attributes
    progress_tracker.current_crop = 0

    # getting fixed size is none bool
    fixed_size_is_none = (fixed_size is None)

    # iterating over df rows
    for row_index, row_data in df_rows:

        # updating progress tracker attributes
        progress_tracker.current_crop += 1
        progress_tracker.current_iteration += 1

        # getting current row info
        crop_name = row_data['crop_name']

        # getting current crop output path
        output_path = join(output_folder,
                           crop_name)

        # getting skip file bool
        skip_file = get_skip_file_bool(file_path=output_path,
                                       overwrite_output=overwrite_output)

        # checking whether to skip current crop
        if skip_file:

            # sleeping
            progress_tracker.wait(0.05)

            # updating progress tracker attributes
            progress_tracker.skipped_iterations += 1

            # skipping to next crop
            continue

        # checking whether crop should be in fixed size or use df boundaries

        if fixed_size_is_none: # crop using df boundaries

            # getting boundaries from df
            boundaries_str = row_data['boundaries']

            # converting data types
            boundaries = string_to_coords(coords_str=boundaries_str)

        else:  # crop with fixed size

            # getting object centroid coords from df
            object_coords_str = row_data['centroid']

            # converting data types
            object_coords = string_to_coords(coords_str=object_coords_str)
            fixed_size_dims = string_to_coords(coords_str=fixed_size)  # noqa

            # getting fixed size boundaries
            boundaries = get_centroid_boundaries(coords=object_coords,
                                                 bounding_dims=fixed_size_dims)

        # cropping object
        current_crop = crop_object(image=image,
                                   boundaries=boundaries,
                                   margin=margin)

        # checking whether crop should be padded back up to requested fixed size
        if fixed_size:

            # getting pad widths needed to match originally requested fixed size
            pad_widths = get_fixed_size_pad_widths(boundaries=boundaries,
                                                   margin=margin,
                                                   image_shape=image.shape)

            # adding no-op pad width for channel axis (multi-channel images)
            if image_is_multichannel:

                # updating pad widths
                pad_widths += ((0, 0),)

            # padding crop (fills clipped-off edges with zeros, keeping object correctly positioned)
            current_crop = pad(current_crop, pad_widths, mode='constant')

        # checking whether crop is mask
        if mask:

            # getting object id from df
            object_id = row_data['object_id']

            # filtering crop to contain only current object id pixels
            current_crop = filter_mask(mask=current_crop,
                                       object_id=object_id)

        # saving current crop
        save_image(save_path=output_path,
                   image=current_crop)

        # sleeping
        progress_tracker.wait(0.001)


def crop_images(input_folder: str,
                objects_df_path: str,
                output_folder: str,
                margin: int,
                mask: bool,
                fixed_size: str | None,
                overwrite_output: bool,
                progress_tracker: ModuleProgressTracker
                ) -> None:
    """
    Given a path to a folder containing
    images, saves single object crops in
    given output folder, based on
    boundaries coordinates in given
    objects df.

    Args:
        input_folder (str): The path to the folder containing images to crop.
        objects_df_path (str): The path to the objects df.
        output_folder (str): The path to the folder to save crops to.
        margin (int): The margin (in pixels) to apply to crop boundaries.
        mask (bool): Whether images being cropped are masks.
        fixed_size (str | None): The fixed crop size (z,y,x), or None to use df boundaries.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # loading df
    df = load_df(input_path=objects_df_path)

    # defining group cols
    group_cols = ['image_name',
                  'image_index']

    # grouping df
    df_groups = df.groupby(group_cols)

    # iterating over df groups
    for df_name, df_group in df_groups:

        # updating progress tracker attributes
        progress_tracker.current_image += 1

        # getting current group info
        image_name, image_index = df_name

        # getting current image path
        image_path = join(input_folder,
                          image_name)

        # cropping current image objects
        crop_objects(input_path=image_path,
                     df=df_group,
                     margin=margin,
                     mask=mask,
                     output_folder=output_folder,
                     fixed_size=fixed_size,
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
    # getting input folder
    input_folder = args_dict['input_folder']

    # getting objects df path
    objects_df_path = args_dict['objects_df_path']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting margin
    margin = args_dict['margin']

    # getting mask
    mask = args_dict['mask']

    # getting fixed size
    fixed_size = args_dict['fixed_size']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running crop_images function
    crop_images(input_folder=input_folder,
                objects_df_path=objects_df_path,
                output_folder=output_folder,
                margin=margin,
                mask=mask,
                fixed_size=fixed_size,
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
