# generate pairwise distances dfs module

print('initializing...')  # noqa

# Code destined to generating
# object-to-object distances dataframe.

######################################################################
# imports

print('importing required libraries...')  # noqa
from numpy import array
from os.path import join
from cet.config import GPU
from pandas import DataFrame
from itertools import combinations
from argparse import ArgumentParser
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from cet.io.cli import get_scales_dict
from cet.gpu.device import transfer_to_gpu
from cet.io.files import get_skip_file_bool
from cet.gpu.device import transfer_from_gpu
from cet.constants import DEFAULT_SCALES_STR
from cet.dataframes.df_ops import concatenate_dfs
from cet.dataframes.df_ops import get_df_values_dict
from cet.measurements.position import string_to_coords
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.dataframes.df_ops import filter_pandas_performance_warnings

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
else:
    from numpy import ndarray

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
    description = "generate pairwise distances dfs module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input path param
    parser.add_argument('-i', '--input-path',
                        dest='input_path',
                        type=str,
                        required=True,
                        help='defines path to joined objects df [.csv]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain distances dfs [.csv])')

    # group col param
    parser.add_argument('-g', '--group-col',
                        dest='group_col',
                        type=str,
                        required=False,
                        default='image_index',
                        help='defines group column name')

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

        # group
        self.groups_num = 0
        self.current_group = 0

        # object pair
        self.object_pairs_num = 0
        self.current_object_pair = 0

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
            progress_string += f' | groups: {self.groups_num}'
            progress_string += f' | object_pairs: {self.object_pairs_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'generating dfs...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_image}/{self.images_num}'
            progress_string += f' | group: {self.current_group}/{self.groups_num}'
            progress_string += f' | object_pair: {self.current_object_pair}/{self.object_pairs_num}'
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

        # getting group col
        group_col = args_dict['group_col']

        # loading df
        df = load_df(input_path=input_path)

        # defining group cols
        group_cols = ['image_name',
                      'image_index']

        # grouping df
        image_groups = df.groupby(group_cols)

        # iterating over df groups
        for df_name, image_group in image_groups:

            # updating progress tracker attributes
            self.images_num += 1

            # getting current group info
            image_name, image_index = df_name

            # defining placeholder value for current iterations dict
            current_iterations_dict = {image_name: 0}

            # grouping df
            df_groups = image_group.groupby(group_col)

            # iterating over df groups
            for _, df_group in df_groups:

                # updating progress tracker attributes
                self.groups_num += 1

                # getting rows num
                rows_num = len(df_group)

                # getting df is valid bool
                group_is_valid = (rows_num > 1)  # must have at least two objects to calculate distance

                # checking if current group is valid
                if not group_is_valid:

                    # skipping to next group
                    continue

                # defining id col
                id_col = 'uid'

                # getting current group objects ids
                current_group_ids = df_group[id_col]

                # converting data types
                current_group_ids = current_group_ids.to_list()

                # getting current ids combinations
                current_object_pairs = combinations(iterable=current_group_ids,
                                                    r=2)

                # iterating over current coords combination
                for _ in current_object_pairs:

                    # updating progress tracker attributes
                    self.object_pairs_num += 1
                    self.iterations_num += 1

                    # updating current iterations dict
                    current_iterations_dict[image_name] += 1

            # updating progress tracker attributes
            self.iterations_dict.update(current_iterations_dict)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | groups: {self.groups_num}'
        totals_string += f' | object_pairs: {self.object_pairs_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_coords_combinations_df(image_name: str,
                               image_index: int,
                               group_col: str,
                               group_id: int,
                               object_ids: list,
                               coords_dict: dict,
                               progress_tracker: ModuleProgressTracker
                               ) -> DataFrame:
    """
    Given a list of object ids, and
    respective coords dict, returns
    a dataframe with all possible
    pairwise combinations between
    coords.

    Args:
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        group_col (str): The column name identifying the group.
        group_id (int): The current group's id.
        object_ids (list): The list of object ids in the group.
        coords_dict (dict): A dictionary mapping each object id to its centroid coords string.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The pairwise combinations df.
    """
    # defining placeholder value for dicts list
    dicts_list = []

    # getting group is not image index bool
    group_not_image_index = (group_col != 'image_index')

    # getting current ids combinations
    current_object_pairs = combinations(iterable=object_ids,
                                        r=2)

    # converting data types
    current_object_pairs = [id_pair for id_pair in current_object_pairs]

    # getting combinations num
    groups_num = len(current_object_pairs)

    # updating progress tracker attributes
    progress_tracker.object_pairs_num = groups_num

    # resetting progress tracker attributes
    progress_tracker.current_object_pair = 0

    # iterating over current coords combination
    for id_pair in current_object_pairs:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_object_pair += 1

        # extracting values from tuple
        id_a, id_b = id_pair

        # getting current id coords
        id_a_coords_str = coords_dict[id_a]
        id_b_coords_str = coords_dict[id_b]

        # converting data types
        id_a_coords = string_to_coords(coords_str=id_a_coords_str)
        id_b_coords = string_to_coords(coords_str=id_b_coords_str)

        # converting data types
        id_a_coords_arr = array(id_a_coords)
        id_b_coords_arr = array(id_b_coords)

        # assembling current pair dict
        current_pair_dict = {'image_name': image_name,
                             'image_index': image_index,
                             'id_a': id_a,
                             'id_b': id_b,
                             'id_a_coords': id_a_coords_str,
                             'id_b_coords': id_b_coords_str,
                             'id_a_coords_arr': id_a_coords_arr,
                             'id_b_coords_arr': id_b_coords_arr}

        # checking whether group is not image index
        if group_not_image_index:

            # updating current pair dict
            current_pair_dict[group_col] = group_id

        # appending current pair dict to dicts list
        dicts_list.append(current_pair_dict)

    # assembling final df
    final_df = DataFrame(dicts_list)

    # returning final df
    return final_df


def calculate_pairwise_distances(combinations_df: DataFrame,
                                 scales_dict: dict
                                 ) -> ndarray:
    """
    Given a combinations df containing
    coordinate arrays and a scales
    dict, calculates and returns the
    pairwise Euclidean distances.

    Args:
        combinations_df (DataFrame): The pairwise combinations df.
        scales_dict (dict): The per-axis pixel-to-micron scales.

    Returns:
        ndarray: The pairwise Euclidean distances.
    """
    # getting current combination coords
    id_a_coords = combinations_df['id_a_coords_arr']
    id_b_coords = combinations_df['id_b_coords_arr']

    # converting data types
    id_a_coords = id_a_coords.to_list()
    id_b_coords = id_b_coords.to_list()

    # converting data types
    id_a_coords = array(id_a_coords)
    id_b_coords = array(id_b_coords)

    # checking if gpu is available
    if GPU:

        # transferring arrays to gpu
        id_a_coords = transfer_to_gpu(arr=id_a_coords)
        id_b_coords = transfer_to_gpu(arr=id_b_coords)

    # transposing coords
    id_a_coords = id_a_coords.transpose()
    id_b_coords = id_b_coords.transpose()

    # extracting coords arrays
    a_zs, a_ys, a_xs = id_a_coords
    b_zs, b_ys, b_xs = id_b_coords

    # getting current distances arrays
    distances_zs = (a_zs - b_zs)
    distances_ys = (a_ys - b_ys)
    distances_xs = (a_xs - b_xs)

    # converting data types
    distances_zs = distances_zs.astype('float32')
    distances_ys = distances_ys.astype('float32')
    distances_xs = distances_xs.astype('float32')

    # checking if scales dict is not None
    if scales_dict:

        # getting specific distance weights for each axis
        z_scale = scales_dict['z']
        y_scale = scales_dict['y']
        x_scale = scales_dict['x']

        # scaling distances (applying weights according to scales dict)
        distances_zs *= z_scale
        distances_ys *= y_scale
        distances_xs *= x_scale

    # squaring distances
    distances_zs = (distances_zs ** 2)
    distances_ys = (distances_ys ** 2)
    distances_xs = (distances_xs ** 2)

    # getting squared distances sum
    distances_sum = (distances_zs + distances_ys + distances_xs)

    # getting square root of squared distances sum
    distances = (distances_sum ** 0.5)

    # checking whether array is in gpu ram
    if GPU:

        # transferring array from gpu
        distances = transfer_from_gpu(arr=distances)

    # returning distances
    return distances


def get_distances_df(df: DataFrame,
                     image_name: str,
                     image_index: int,
                     group_col: str,
                     group_id: int,
                     scales_dict: dict,
                     progress_tracker: ModuleProgressTracker
                     ) -> DataFrame:
    """
    Given a group df containing info
    on object coords, returns its
    respective pairwise distances df.

    Args:
        df (DataFrame): The group's objects df.
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        group_col (str): The column name identifying the group.
        group_id (int): The current group's id.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The group's pairwise distances df.
    """
    # defining id/coords cols
    id_col = 'uid'
    coords_col = 'centroid'

    # getting current group objects ids
    object_ids = df[id_col]

    # converting data types
    object_ids = object_ids.to_list()

    # getting current group coords dict
    coords_dict = get_df_values_dict(df=df,
                                     key_col=id_col,
                                     value_col=coords_col)

    # getting combinations df
    combinations_df = get_coords_combinations_df(image_name=image_name,
                                                 image_index=image_index,
                                                 group_col=group_col,
                                                 group_id=group_id,
                                                 object_ids=object_ids,
                                                 coords_dict=coords_dict,
                                                 progress_tracker=progress_tracker)

    # calculating pairwise distances
    distances = calculate_pairwise_distances(combinations_df=combinations_df,
                                             scales_dict=scales_dict)

    # adding distances col to df
    combinations_df['distance'] = distances

    # defining cols to discard
    cols_to_discard = ['id_a_coords_arr',
                       'id_b_coords_arr']

    # dropping cols
    combinations_df.drop(columns=cols_to_discard,
                         inplace=True)

    # returning distances df
    return combinations_df


def get_images_df(df: DataFrame,
                  image_name: str,
                  image_index: int,
                  group_col: str,
                  scales_dict: dict,
                  progress_tracker: ModuleProgressTracker
                  ) -> DataFrame:
    """
    Given an image df, computes
    pairwise distance between objects
    specified by group col, and
    returns distances df.

    Args:
        df (DataFrame): The image's objects df.
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        group_col (str): The column name identifying the group.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The image's pairwise distances df.
    """
    # defining placeholder value for dfs list
    dfs_list = []

    # grouping df
    df_groups = df.groupby(group_col)

    # getting groups num
    groups_num = len(df_groups)

    # updating progress tracker attributes
    progress_tracker.groups_num = groups_num

    # resetting progress tracker attributes
    progress_tracker.current_group = 0

    # iterating over df groups
    for df_name, df_group in df_groups:

        # updating progress tracker attributes
        progress_tracker.current_group += 1

        # getting current group info
        group_id = int(df_name)  # noqa

        # getting rows num
        rows_num = len(df_group)

        # getting df is valid bool
        group_is_valid = (rows_num > 1)  # must have at least two objects to calculate distance

        # checking if current group is valid
        if not group_is_valid:

            # skipping to next group
            continue

        # getting current group df
        current_df = get_distances_df(df=df_group,
                                      image_name=image_name,
                                      image_index=image_index,
                                      group_col=group_col,
                                      group_id=group_id,
                                      scales_dict=scales_dict,
                                      progress_tracker=progress_tracker)

        # appending current df to dfs list
        dfs_list.append(current_df)

    # concatenating dfs in dfs list
    final_df = concatenate_dfs(dfs_list)

    # returning final df
    return final_df


def generate_pairwise_distances_dfs(input_path: str,
                                    output_folder: str,
                                    group_col: str,
                                    scales_dict: str,
                                    overwrite_output: bool,
                                    progress_tracker: ModuleProgressTracker
                                    ) -> None:
    """
    Given a path to a joined objects
    df, generates pairwise distances
    dfs, based on group col.

    Args:
        input_path (str): The path to the joined objects df.
        output_folder (str): The path to the folder to save per-image distances dfs to.
        group_col (str): The column name to group objects by.
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # loading df
    df = load_df(input_path=input_path)

    # defining group cols
    group_cols = ['image_name',
                  'image_index']

    # grouping df
    df_groups = df.groupby(group_cols)

    # getting groups num
    groups_num = len(df_groups)

    # updating progress tracker attributes
    progress_tracker.images_num = groups_num

    # resetting progress tracker attributes
    progress_tracker.current_image = 0

    # getting progress tracker iterations dict
    iterations_dict = progress_tracker.iterations_dict

    # iterating over df groups
    for df_name, df_group in df_groups:

        # updating progress tracker attributes
        progress_tracker.current_image += 1

        # getting current group info
        image_name, image_index = df_name

        # getting current image iterations num
        current_iterations_num = iterations_dict[image_name]

        # getting current image output path
        output_name = f'{image_name}.csv'
        output_path = join(output_folder,
                           output_name)

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

        # getting current image df
        current_image_df = get_images_df(df=df_group,
                                         image_name=image_name,
                                         image_index=image_index,
                                         group_col=group_col,
                                         scales_dict=scales_dict,
                                         progress_tracker=progress_tracker)

        # saving current image df
        save_df(save_path=output_path,
                df=current_image_df)


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

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting group col
    group_col = args_dict['group_col']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_pairwise_distances_dfs function
    generate_pairwise_distances_dfs(input_path=input_path,
                                    output_folder=output_folder,
                                    group_col=group_col,
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
