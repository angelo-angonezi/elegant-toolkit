# generate mask distances df module

print('initializing...')  # noqa

# Code destined to generating
# dot-to-mask distances dataframe.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from pandas import Series
from argparse import ArgumentParser
from cet.io.images import load_image
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from cet.io.cli import get_scales_dict
from cet.dataframes.df_ops import add_col
from cet.io.files import get_skip_file_bool
from cet.constants import DEFAULT_SCALES_STR
from cet.segmentation.mask_ops import get_bool_mask
from cet.measurements.position import get_pixel_coords
from cet.measurements.position import string_to_coords
from cet.measurements.position import coords_to_string
from cet.measurements.distance import get_shortest_distance
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.dataframes.df_ops import filter_pandas_performance_warnings
print('all required libraries successfully imported.')  # noqa

# filtering Pandas Performance Warnings
filter_pandas_performance_warnings()

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
    description = "generate mask distances df module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input path param
    parser.add_argument('-i', '--input-path',
                        dest='input_path',
                        type=str,
                        required=True,
                        help='defines path to joined objects df [.csv]')

    # masks folder param
    parser.add_argument('-m', '--masks-folder',
                        dest='masks_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing "bounding" segmentation masks [.tif]')

    # output path param
    parser.add_argument('-o', '--output-path',
                        dest='output_path',
                        type=str,
                        required=True,
                        help='defines path to output file [.csv]')

    # masks name param
    parser.add_argument('-n', '--mask-name',
                        dest='mask_name',
                        type=str,
                        required=False,
                        default='lamina',
                        help='defines name of masks')

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

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

        # embryo
        self.embryos_num = 0
        self.current_embryo = 0

        # nucleus
        self.nuclei_num = 0
        self.current_nucleus = 0

        # dot
        self.dots_num = 0
        self.current_dot = 0

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
            progress_string += f' | embryos: {self.embryos_num}'
            progress_string += f' | nuclei: {self.nuclei_num}'
            progress_string += f' | dots: {self.dots_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'generating dfs...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_image}/{self.images_num}'
            progress_string += f' | embryo: {self.current_embryo}/{self.embryos_num}'
            progress_string += f' | nucleus: {self.current_nucleus}/{self.nuclei_num}'
            progress_string += f' | dot: {self.current_dot}/{self.dots_num}'
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
        # getting input path
        input_path = args_dict['input_path']

        # loading df
        df = load_df(input_path=input_path)

        # defining group cols
        group_cols = ['image_name',
                      'image_index']

        # grouping df
        image_groups = df.groupby(group_cols)

        # iterating over df groups
        for image_group_name, image_group in image_groups:

            # updating progress tracker attributes
            self.images_num += 1

            # defining group col
            group_col = 'embryo_id'

            # grouping df
            embryos_groups = image_group.groupby(group_col)

            # iterating over df groups
            for embryo_id, embryo_group in embryos_groups:

                # updating progress tracker attributes
                self.embryos_num += 1

                # defining group col
                group_col = 'nucleus_id'

                # grouping df
                nucleus_groups = embryo_group.groupby(group_col)

                # iterating over df groups
                for nucleus_id, nucleus_group in nucleus_groups:

                    # updating progress tracker attributes
                    self.nuclei_num += 1

                    # getting df rows num/range
                    df_rows_num = len(nucleus_group)
                    df_rows_range = range(df_rows_num)

                    # iterating over df rows
                    for _ in df_rows_range:

                        # updating progress tracker attributes
                        self.dots_num += 1
                        self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | embryos: {self.embryos_num}'
        totals_string += f' | nuclei: {self.nuclei_num}'
        totals_string += f' | dots: {self.dots_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_mask_distance_result(row_data: Series,
                             results_by_row_index: dict,
                             result_key: str
                             ) -> object:
    """
    Given a df row and a dict of
    precomputed dot-to-mask distance
    results (keyed by row index),
    returns given result key's value
    for current row.

    Args:
        row_data (Series): The df row to look up.
        results_by_row_index (dict): A dictionary mapping row index to its precomputed results.
        result_key (str): The result key to return.

    Returns:
        object: The requested result value, or None if not present.
    """
    # getting current row index
    row_index = row_data.name

    # getting current row result (empty dict if row was never visited)
    row_result = results_by_row_index.get(row_index, {})

    # returning requested result value (None if not present)
    return row_result.get(result_key)


def generate_mask_distances_df(input_path: str,
                               masks_folder: str,
                               output_path: str,
                               mask_name: str,
                               scales_dict: str,
                               overwrite_output: bool,
                               progress_tracker: ModuleProgressTracker
                               ) -> None:
    """
    Given a path to a joined dots df,
    saves new df containing dots
    distance to the mask.

    Args:
        input_path (str): The path to the joined objects df.
        masks_folder (str): The path to the folder containing "bounding" segmentation masks.
        output_path (str): The path to save the updated df to.
        mask_name (str): The name of the masks (used to name the new distance/coord cols).
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        overwrite_output (bool): Whether to overwrite an existing output file.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting skip file bool
    skip_file = get_skip_file_bool(file_path=output_path,
                                   overwrite_output=overwrite_output)

    # checking whether to skip current file
    if skip_file:

        # sleeping
        progress_tracker.wait(0.05)

        # updating progress tracker attributes
        progress_tracker.current_iteration += progress_tracker.iterations_num
        progress_tracker.skipped_iterations += progress_tracker.iterations_num

        # skipping
        return None

    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # loading df
    df = load_df(input_path=input_path)

    # defining new col names
    distance_col = f'distance_to_{mask_name}'
    dot_coord_col = 'dot_coord'
    mask_coord_col = f'{mask_name}_coord'

    # defining placeholder value for results by row index dict
    results_by_row_index = {}

    # defining group cols
    group_cols = ['image_name',
                  'image_index']

    # grouping df
    image_groups = df.groupby(group_cols)

    # iterating over df groups
    for image_group_name, image_group in image_groups:

        # updating progress tracker attributes
        progress_tracker.current_image += 1

        # getting current group info
        image_name, image_index = image_group_name

        # getting current mask path
        input_path = join(masks_folder,
                          image_name)

        # loading current mask
        mask = load_image(input_path=input_path)

        # defining group col
        group_col = 'embryo_id'

        # grouping df
        embryos_groups = image_group.groupby(group_col)

        # getting current embryo count
        embryos_num = len(embryos_groups)

        # updating progress tracker attributes
        progress_tracker.embryos_num = embryos_num

        # resetting progress tracker attributes
        progress_tracker.current_embryo = 0

        # iterating over df groups
        for embryo_id, embryo_group in embryos_groups:

            # updating progress tracker attributes
            progress_tracker.current_embryo += 1

            # defining group col
            group_col = 'nucleus_id'

            # grouping df
            nuclei_groups = embryo_group.groupby(group_col)

            # getting current nuclei count
            nuclei_num = len(nuclei_groups)

            # updating progress tracker attributes
            progress_tracker.nuclei_num = nuclei_num

            # resetting progress tracker attributes
            progress_tracker.current_nucleus = 0

            # iterating over df groups
            for nucleus_id, nucleus_group in nuclei_groups:

                # updating progress tracker attributes
                progress_tracker.current_nucleus += 1

                # converting data types
                nucleus_id = int(nucleus_id)  # noqa

                # getting current object mask
                current_mask = get_bool_mask(mask=mask,
                                             object_id=nucleus_id)

                # getting current mask coords
                mask_coords = get_pixel_coords(mask=current_mask)

                # getting mask coords num
                mask_coords_count = len(mask_coords[0])
                mask_coords_empty = (mask_coords_count == 0)

                # getting df rows
                df_rows = nucleus_group.iterrows()

                # getting current dots count
                dots_num = len(nucleus_group)

                # updating progress tracker attributes
                progress_tracker.dots_num = dots_num

                # resetting progress tracker attributes
                progress_tracker.current_dot = 0

                # iterating over df rows
                for row_index, row_data in df_rows:

                    # updating progress tracker attributes
                    progress_tracker.current_iteration += 1
                    progress_tracker.current_dot += 1

                    # getting current row info
                    dot_coord_str = row_data['centroid']

                    # converting data types
                    dot_coord = string_to_coords(coords_str=dot_coord_str)

                    # checking if mask coords count is not empty
                    if mask_coords_empty:

                        # getting current dot distance to mask
                        shortest_distance, shortest_coord = (None, None)

                    else:

                        # getting current dot distance to mask
                        shortest_distance, shortest_coord = get_shortest_distance(coord=dot_coord,
                                                                                  coords=mask_coords,
                                                                                  scales_dict=scales_dict)

                    # converting data types
                    mask_coord_str = coords_to_string(coords=shortest_coord)

                    # storing current row result
                    results_by_row_index[row_index] = {'distance': shortest_distance,
                                                       'dot_coord': dot_coord_str,
                                                       'mask_coord': mask_coord_str}

    # adding distance/coords cols
    add_col(df=df,
            col_name=distance_col,
            func=get_mask_distance_result,
            func_kwargs={'results_by_row_index': results_by_row_index,
                         'result_key': 'distance'})
    add_col(df=df,
            col_name=dot_coord_col,
            func=get_mask_distance_result,
            func_kwargs={'results_by_row_index': results_by_row_index,
                         'result_key': 'dot_coord'})
    add_col(df=df,
            col_name=mask_coord_col,
            func=get_mask_distance_result,
            func_kwargs={'results_by_row_index': results_by_row_index,
                         'result_key': 'mask_coord'})

    # saving df
    save_df(save_path=output_path,
            df=df)


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
    # getting input path
    input_path = args_dict['input_path']

    # getting masks folder
    masks_folder = args_dict['masks_folder']

    # getting output path
    output_path = args_dict['output_path']

    # getting masks name
    mask_name = args_dict['mask_name']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_mask_distances_df function
    generate_mask_distances_df(input_path=input_path,
                               masks_folder=masks_folder,
                               output_path=output_path,
                               mask_name=mask_name,
                               scales_dict=scales_dict,
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
