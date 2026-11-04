# generate dots distances df module

print('initializing...')  # noqa

# Code destined to generating
# dot-to-dot distances dataframe.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from cet.io.cli import get_scales_dict
from cet.io.files import get_skip_file_bool
from cet.gpu.device import transfer_from_gpu
from cet.constants import DEFAULT_SCALES_STR
from scipy.optimize import linear_sum_assignment
from cet.dataframes.df_ops import concatenate_dfs
from cet.measurements.position import string_to_coords
from cet.measurements.position import coords_to_string
from cet.measurements.distance import get_distance_type
from cet.measurements.distance import get_scaled_distances
from cet.measurements.distance import get_shortest_distance
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.dataframes.df_ops import filter_pandas_performance_warnings

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import array
    from cupy import ndarray
else:
    from numpy import array
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
    description = "generate dots distances df module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input path param
    parser.add_argument('-i', '--input-path',
                        dest='input_path',
                        type=str,
                        required=True,
                        help='defines path to joined dots df [.csv]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain dot distances dfs [.csv])')

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

    # dot1 description param
    parser.add_argument('-d1', '--dot1-description',
                        dest='dot1_description',
                        type=str,
                        required=True,
                        help='defines description of first dot type to calculate distances for')

    # dot2 description param
    parser.add_argument('-d2', '--dot2-description',
                        dest='dot2_description',
                        type=str,
                        required=True,
                        help='defines description of second dot type to calculate distances for')

    # distance mode param
    parser.add_argument('-m', '--distance-mode',
                        dest='distance_mode',
                        type=str,
                        required=False,
                        default='hungarian',
                        choices=['hungarian', 'legacy'],
                        help='defines dot-pair matching algorithm: "hungarian" (optimal one-to-one assignment) or "legacy" (per-dot nearest-neighbor, allows reuse, pre-Hungarian behavior)')

    # distance threshold param
    parser.add_argument('-t', '--distance-threshold',
                        dest='distance_threshold',
                        type=float,
                        required=False,
                        default=0.6,
                        help='defines distance (in microns) to be used as threshold to consider overlap')

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

        # dot pair
        self.dot_pairs_num = 0
        self.current_dot_pair = 0

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
            progress_string += f' | embryos: {self.embryos_num}'
            progress_string += f' | nuclei: {self.nuclei_num}'
            progress_string += f' | dot_pairs: {self.dot_pairs_num}'
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
            progress_string += f' | dot_pair: {self.current_dot_pair}/{self.dot_pairs_num}'
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

        # getting dot descriptions
        dot1_description = args_dict['dot1_description']
        dot2_description = args_dict['dot2_description']

        # getting distance mode
        distance_mode = args_dict['distance_mode']

        # loading df
        df = load_df(input_path=input_path)

        # filtering df down to the two dot descriptions being compared
        descriptions = [dot1_description, dot2_description]
        df = df[df['description'].isin(descriptions)]

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
            image_name, image_index = df_name  # noqa

            # defining placeholder value for current iterations dict
            current_iterations_dict = {image_name: 0}

            # defining group col
            group_col = 'embryo_id'

            # grouping df
            embryo_groups = image_group.groupby(group_col)

            # iterating over df groups
            for _, embryo_group in embryo_groups:

                # updating progress tracker attributes
                self.embryos_num += 1

                # defining group col
                group_col = 'nucleus_id'

                # grouping df
                nucleus_groups = embryo_group.groupby(group_col)

                # iterating over df groups
                for _, nucleus_group in nucleus_groups:

                    # updating progress tracker attributes
                    self.nuclei_num += 1

                    # getting current group dot1/dot2 dfs
                    df1 = nucleus_group[nucleus_group['description'] == dot1_description]
                    df2 = nucleus_group[nucleus_group['description'] == dot2_description]

                    # getting dot counts
                    df1_len = len(df1)
                    df2_len = len(df2)

                    # getting validity bools
                    df1_valid = df1_len > 0
                    df2_valid = df2_len > 0
                    both_valid = (df1_valid and df2_valid)

                    # checking if each df contains at least one dot
                    if not both_valid:

                        # skipping to next nucleus
                        continue

                    # getting current nucleus dot pairs count (one pair per dot1 dot in legacy mode,
                    # one pair per optimal assignment match in hungarian mode)
                    dot_pairs_count = df1_len if distance_mode == 'legacy' else min(df1_len, df2_len)

                    # getting dot pairs range
                    dot_pairs_range = range(dot_pairs_count)

                    # iterating over dot pairs
                    for _ in dot_pairs_range:

                        # updating progress tracker attributes
                        self.dot_pairs_num += 1
                        self.iterations_num += 1

                        # updating current iterations dict
                        current_iterations_dict[image_name] += 1

            # updating progress tracker attributes
            self.iterations_dict.update(current_iterations_dict)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | embryos: {self.embryos_num}'
        totals_string += f' | nuclei: {self.nuclei_num}'
        totals_string += f' | dot_pairs: {self.dot_pairs_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_legacy_dot_pairs_dicts(df1_coords: list,
                               df1_coords_strs: list,
                               df2_coords_arr: ndarray,
                               image_name: str,
                               image_index: int,
                               embryo_id: int,
                               nucleus_id: int,
                               dot1_description: str,
                               dot2_description: str,
                               scales_dict: dict,
                               distance_threshold: float,
                               progress_tracker: ModuleProgressTracker
                               ) -> list:
    """
    Given dot1/dot2 coords, returns dot-pair
    dicts using per-dot nearest-neighbor matching
    (legacy mode; dot2 points may be reused across
    multiple dot1 points).

    Args:
        df1_coords (list): The dot1 coords (tuples).
        df1_coords_strs (list): The dot1 coords as strings.
        df2_coords_arr (ndarray): The dot2 coords, as a transposed array.
        image_name (str): The current image name.
        image_index (int): The current image index.
        embryo_id (int): The current embryo id.
        nucleus_id (int): The current nucleus id.
        dot1_description (str): The description of the first dot type to compare.
        dot2_description (str): The description of the second dot type to compare.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        distance_threshold (float): The distance (in microns) to use as overlap threshold.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        list: A list of dot-pair dicts.
    """
    # defining placeholder value for dicts list
    dicts_list = []

    # iterating over dot1 coords (legacy: per-dot nearest neighbor, dot2 points may be reused)
    for df1_index, df1_coord in enumerate(df1_coords):

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_dot_pair += 1

        # getting current dot shortest distance pair
        shortest_distance, shortest_coord = get_shortest_distance(coord=df1_coord,
                                                                  coords=df2_coords_arr,
                                                                  scales_dict=scales_dict)

        # getting current distance type
        distance_type = get_distance_type(distance=shortest_distance,
                                          distance_threshold=distance_threshold)

        # converting data types
        shortest_coords_str = coords_to_string(coords=shortest_coord)

        # assembling current dict
        current_dict = {'image_name': image_name,
                        'image_index': image_index,
                        'embryo_id': embryo_id,
                        'nucleus_id': nucleus_id,
                        'description': 'dot_pair',
                        f'{dot1_description}_coords': df1_coords_strs[df1_index],
                        f'{dot2_description}_coords': shortest_coords_str,
                        'distance': shortest_distance,
                        'distance_type': distance_type}

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # returning dicts list
    return dicts_list


def get_hungarian_dot_pairs_dicts(df1_coords: list,
                                  df1_coords_strs: list,
                                  df2_coords_arr: ndarray,
                                  df2_coords_strs: list,
                                  image_name: str,
                                  image_index: int,
                                  embryo_id: int,
                                  nucleus_id: int,
                                  dot1_description: str,
                                  dot2_description: str,
                                  scales_dict: dict,
                                  distance_threshold: float,
                                  progress_tracker: ModuleProgressTracker
                                  ) -> list:
    """
    Given dot1/dot2 coords, returns dot-pair
    dicts using an optimal one-to-one assignment
    (Hungarian algorithm).

    Args:
        df1_coords (list): The dot1 coords (tuples).
        df1_coords_strs (list): The dot1 coords as strings.
        df2_coords_arr (ndarray): The dot2 coords, as a transposed array.
        df2_coords_strs (list): The dot2 coords as strings.
        image_name (str): The current image name.
        image_index (int): The current image index.
        embryo_id (int): The current embryo id.
        nucleus_id (int): The current nucleus id.
        dot1_description (str): The description of the first dot type to compare.
        dot2_description (str): The description of the second dot type to compare.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        distance_threshold (float): The distance (in microns) to use as overlap threshold.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        list: A list of dot-pair dicts.
    """
    # defining placeholder value for cost matrix rows
    cost_rows = []

    # iterating over dot1 coords
    for df1_coord in df1_coords:

        # getting current row distances (dot1 coord to every dot2 coord)
        row_distances = get_scaled_distances(coords_a=df1_coord,
                                             coords_b=df2_coords_arr,
                                             scales_dict=scales_dict)

        # appending current row to cost rows
        cost_rows.append(row_distances)

    # assembling cost matrix
    cost_matrix = array(cost_rows)

    # checking if gpu is available
    if GPU:

        # transferring cost matrix from gpu (scipy's assignment solver needs a numpy array)
        cost_matrix = transfer_from_gpu(arr=cost_matrix)

    # getting optimal one-to-one dot pair assignment (hungarian algorithm)
    df1_indices, df2_indices = linear_sum_assignment(cost_matrix)

    # defining placeholder value for dicts list
    dicts_list = []

    # iterating over assigned dot pair indices
    for df1_index, df2_index in zip(df1_indices, df2_indices):

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_dot_pair += 1

        # getting current pair distance
        shortest_distance = cost_matrix[df1_index][df2_index]

        # getting current distance type
        distance_type = get_distance_type(distance=shortest_distance,
                                          distance_threshold=distance_threshold)

        # assembling current dict
        current_dict = {'image_name': image_name,
                        'image_index': image_index,
                        'embryo_id': embryo_id,
                        'nucleus_id': nucleus_id,
                        'description': 'dot_pair',
                        f'{dot1_description}_coords': df1_coords_strs[df1_index],
                        f'{dot2_description}_coords': df2_coords_strs[df2_index],
                        'distance': shortest_distance,
                        'distance_type': distance_type}

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # returning dicts list
    return dicts_list


def get_nucleus_df(df: DataFrame,
                   image_name: str,
                   image_index: int,
                   embryo_id: int,
                   nucleus_id: int,
                   dot1_description: str,
                   dot2_description: str,
                   distance_mode: str,
                   scales_dict: dict,
                   distance_threshold: float,
                   progress_tracker: ModuleProgressTracker
                   ) -> DataFrame:
    """
    Given a nuclei df containing info
    on dot1/dot2 coords, returns
    its respective distances df.

    Args:
        df (DataFrame): The nucleus's dots df.
        image_name (str): The current image name.
        image_index (int): The current image index.
        embryo_id (int): The current embryo id.
        nucleus_id (int): The current nucleus id.
        dot1_description (str): The description of the first dot type to compare.
        dot2_description (str): The description of the second dot type to compare.
        distance_mode (str): The dot-pair matching algorithm ("hungarian" or "legacy").
        scales_dict (dict): The per-axis pixel-to-micron scales.
        distance_threshold (float): The distance (in microns) to use as overlap threshold.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The nucleus's dot-pair distances df.
    """
    # getting current group dot1/dot2 dfs
    df1 = df[df['description'] == dot1_description]
    df2 = df[df['description'] == dot2_description]

    # getting dot counts
    df1_len = len(df1)
    df2_len = len(df2)

    # getting validity bools
    df1_valid = df1_len > 0
    df2_valid = df2_len > 0
    both_valid = (df1_valid and df2_valid)

    # checking if each df contains at least one dot
    if not both_valid:

        # returning empty dataframe
        return DataFrame()

    # getting current dot1/dot2 coords strings
    df1_coords_strs = df1['centroid'].to_list()
    df2_coords_strs = df2['centroid'].to_list()

    # converting data types
    df1_coords = [string_to_coords(coords_str=coords_str) for coords_str in df1_coords_strs]
    df2_coords = [string_to_coords(coords_str=coords_str) for coords_str in df2_coords_strs]

    # converting data types
    df2_coords_arr = array(df2_coords)
    df2_coords_arr = df2_coords_arr.transpose()

    # getting current dot pair count (one pair per dot1 dot in legacy mode,
    # one pair per optimal assignment match in hungarian mode)
    dot_pairs_count = df1_len if distance_mode == 'legacy' else min(df1_len, df2_len)

    # updating progress tracker attributes
    progress_tracker.dot_pairs_num = dot_pairs_count

    # resetting progress tracker attributes
    progress_tracker.current_dot_pair = 0

    # checking distance mode
    if distance_mode == 'legacy':

        # getting current nucleus dot pair dicts (legacy: per-dot nearest neighbor)
        dicts_list = get_legacy_dot_pairs_dicts(df1_coords=df1_coords,
                                                df1_coords_strs=df1_coords_strs,
                                                df2_coords_arr=df2_coords_arr,
                                                image_name=image_name,
                                                image_index=image_index,
                                                embryo_id=embryo_id,
                                                nucleus_id=nucleus_id,
                                                dot1_description=dot1_description,
                                                dot2_description=dot2_description,
                                                scales_dict=scales_dict,
                                                distance_threshold=distance_threshold,
                                                progress_tracker=progress_tracker)

    # if distance mode is hungarian
    else:

        # getting current nucleus dot pair dicts (hungarian: optimal one-to-one assignment)
        dicts_list = get_hungarian_dot_pairs_dicts(df1_coords=df1_coords,
                                                   df1_coords_strs=df1_coords_strs,
                                                   df2_coords_arr=df2_coords_arr,
                                                   df2_coords_strs=df2_coords_strs,
                                                   image_name=image_name,
                                                   image_index=image_index,
                                                   embryo_id=embryo_id,
                                                   nucleus_id=nucleus_id,
                                                   dot1_description=dot1_description,
                                                   dot2_description=dot2_description,
                                                   scales_dict=scales_dict,
                                                   distance_threshold=distance_threshold,
                                                   progress_tracker=progress_tracker)

    # assembling final df from dicts list
    final_df = DataFrame(dicts_list)

    # returning final df
    return final_df


def get_embryo_df(df: DataFrame,
                  image_name: str,
                  image_index: int,
                  embryo_id: int,
                  dot1_description: str,
                  dot2_description: str,
                  distance_mode: str,
                  scales_dict: dict,
                  distance_threshold: float,
                  progress_tracker: ModuleProgressTracker
                  ) -> DataFrame:
    """
    Given an embryos df containing info
    on dot1/dot2 coords, returns
    its respective distances df.

    Args:
        df (DataFrame): The embryo's dots df.
        image_name (str): The current image name.
        image_index (int): The current image index.
        embryo_id (int): The current embryo id.
        dot1_description (str): The description of the first dot type to compare.
        dot2_description (str): The description of the second dot type to compare.
        distance_mode (str): The dot-pair matching algorithm ("hungarian" or "legacy").
        scales_dict (dict): The per-axis pixel-to-micron scales.
        distance_threshold (float): The distance (in microns) to use as overlap threshold.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The embryo's dot-pair distances df.
    """
    # defining placeholder value for dfs list
    dfs_list = []

    # defining group col
    group_col = 'nucleus_id'

    # grouping df
    df_groups = df.groupby(group_col)

    # getting groups num
    groups_num = len(df_groups)

    # updating progress tracker attributes
    progress_tracker.nuclei_num = groups_num

    # resetting progress tracker attributes
    progress_tracker.current_nucleus = 0

    # iterating over df groups
    for df_name, df_group in df_groups:

        # updating progress tracker attributes
        progress_tracker.current_nucleus += 1

        # getting current group info
        nucleus_id = int(df_name)  # noqa

        # getting current nucleus df
        current_df = get_nucleus_df(df=df_group,
                                    image_name=image_name,
                                    image_index=image_index,
                                    embryo_id=embryo_id,
                                    nucleus_id=nucleus_id,
                                    dot1_description=dot1_description,
                                    dot2_description=dot2_description,
                                    distance_mode=distance_mode,
                                    scales_dict=scales_dict,
                                    distance_threshold=distance_threshold,
                                    progress_tracker=progress_tracker)

        # appending current df to dfs list
        dfs_list.append(current_df)

    # concatenating dfs in dfs list
    final_df = concatenate_dfs(dfs_list)

    # returning final df
    return final_df


def get_images_df(df: DataFrame,
                  image_name: str,
                  image_index: int,
                  dot1_description: str,
                  dot2_description: str,
                  distance_mode: str,
                  scales_dict: dict,
                  distance_threshold: float,
                  progress_tracker: ModuleProgressTracker
                  ) -> DataFrame:
    """
    Given an image df containing info
    on dot1/dot2 coords, returns
    its respective distances df.

    Args:
        df (DataFrame): The image's dots df.
        image_name (str): The current image name.
        image_index (int): The current image index.
        dot1_description (str): The description of the first dot type to compare.
        dot2_description (str): The description of the second dot type to compare.
        distance_mode (str): The dot-pair matching algorithm ("hungarian" or "legacy").
        scales_dict (dict): The per-axis pixel-to-micron scales.
        distance_threshold (float): The distance (in microns) to use as overlap threshold.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The image's dot-pair distances df.
    """
    # defining placeholder value for dfs list
    dfs_list = []

    # defining group col
    group_col = 'embryo_id'

    # grouping df
    df_groups = df.groupby(group_col)

    # getting groups num
    groups_num = len(df_groups)

    # updating progress tracker attributes
    progress_tracker.embryos_num = groups_num

    # resetting progress tracker attributes
    progress_tracker.current_embryo = 0

    # iterating over df groups
    for df_name, df_group in df_groups:

        # updating progress tracker attributes
        progress_tracker.current_embryo += 1

        # getting current group info
        embryo_id = int(df_name)  # noqa

        # getting current embryo df
        current_df = get_embryo_df(df=df_group,
                                   image_name=image_name,
                                   image_index=image_index,
                                   embryo_id=embryo_id,
                                   dot1_description=dot1_description,
                                   dot2_description=dot2_description,
                                   distance_mode=distance_mode,
                                   scales_dict=scales_dict,
                                   distance_threshold=distance_threshold,
                                   progress_tracker=progress_tracker)

        # appending current df to dfs list
        dfs_list.append(current_df)

    # concatenating dfs in dfs list
    final_df = concatenate_dfs(dfs_list)

    # returning final df
    return final_df


def generate_dots_distances_df(input_path: str,
                               output_folder: str,
                               dot1_description: str,
                               dot2_description: str,
                               distance_mode: str,
                               scales_dict: str,
                               distance_threshold: float,
                               overwrite_output: bool,
                               progress_tracker: ModuleProgressTracker
                               ) -> None:
    """
    Given a path to a joined dot1/dot2
    df, generates per-image distances dfs.

    Args:
        input_path (str): The path to the joined dots df.
        output_folder (str): The path to the folder to save per-image distances dfs to.
        dot1_description (str): The description of the first dot type to compare.
        dot2_description (str): The description of the second dot type to compare.
        distance_mode (str): The dot-pair matching algorithm ("hungarian" or "legacy").
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        distance_threshold (float): The distance (in microns) to use as overlap threshold.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # loading df
    df = load_df(input_path=input_path)

    # filtering df down to the two dot descriptions being compared
    descriptions = [dot1_description, dot2_description]
    df = df[df['description'].isin(descriptions)]

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
                                         dot1_description=dot1_description,
                                         dot2_description=dot2_description,
                                         distance_mode=distance_mode,
                                         scales_dict=scales_dict,
                                         distance_threshold=distance_threshold,
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

    # getting dot descriptions
    dot1_description = args_dict['dot1_description']
    dot2_description = args_dict['dot2_description']

    # getting distance mode
    distance_mode = args_dict['distance_mode']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting distance threshold
    distance_threshold = args_dict['distance_threshold']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_dots_distances_df function
    generate_dots_distances_df(input_path=input_path,
                               output_folder=output_folder,
                               dot1_description=dot1_description,
                               dot2_description=dot2_description,
                               distance_mode=distance_mode,
                               scales_dict=scales_dict,
                               distance_threshold=distance_threshold,
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
