# generate summary dfs module

print('initializing...')  # noqa

# Code destined to generating
# per embryo/nucleus/dot/cytoplasm
# summary dataframes.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from pandas import Series
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from cet.dataframes.df_ops import add_cols
from cet.io.files import get_skip_file_bool
from cet.measurements.labels import get_uid
from cet.dataframes.df_ops import get_df_values_dict
from cet.dataframes.df_ops import get_embryo_ages_dict
from cet.dataframes.df_ops import get_grouped_agg_dict
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
    description = "generate summary dfs module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # embryos df path param
    parser.add_argument('-e', '--embryos-df-path',
                        dest='embryos_df_path',
                        type=str,
                        required=True,
                        help='defines path to joined embryos/pseudoembryos df [.csv]')

    # nuclei df path param
    parser.add_argument('-n', '--nuclei-df-path',
                        dest='nuclei_df_path',
                        type=str,
                        required=True,
                        help='defines path to joined nuclei df [.csv]')

    # dots df path param
    parser.add_argument('-d', '--dots-df-path',
                        dest='dots_df_path',
                        type=str,
                        required=False,
                        default=None,
                        help='defines path to joined dots df [.csv]')

    # cytoplasm df path param
    parser.add_argument('-c', '--cytoplasm-df-path',
                        dest='cytoplasm_df_path',
                        type=str,
                        required=False,
                        default=None,
                        help='defines path to joined cytoplasm df [.csv]')

    # border description param
    parser.add_argument('-bd', '--border-description',
                        dest='border_description',
                        type=str,
                        required=False,
                        default='border',
                        help='defines description of the borders masks the dots distances were computed to (name of the "distance_to_<description>" dots df col)')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain summary dfs [.csv])')

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

        # df
        self.df_name = ''

        # col
        self.cols_num = 0
        self.current_col = 0

        # row
        self.rows_num = 0
        self.current_row = 0

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
            progress_string += f' | cols: {self.cols_num}'
            progress_string += f' | rows: {self.rows_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'adding summary cols...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | df: {self.df_name}'
            progress_string += f' | col: {self.current_col}/{self.cols_num}'
            progress_string += f' | row: {self.current_row}/{self.rows_num}'
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
        # getting df paths
        embryos_df_path = args_dict['embryos_df_path']
        nuclei_df_path = args_dict['nuclei_df_path']
        dots_df_path = args_dict['dots_df_path']
        cytoplasm_df_path = args_dict['cytoplasm_df_path']

        # getting border description
        border_description = args_dict['border_description']

        # loading embryo/nuclei dfs
        embryos_df = load_df(input_path=embryos_df_path)
        nuclei_df = load_df(input_path=nuclei_df_path)

        # defining placeholder value for dots df
        dots_df = DataFrame()

        # checking if dots df is not None
        if dots_df_path:

            # loading dots df
            dots_df = load_df(input_path=dots_df_path)

        # defining placeholder value for cytoplasm df
        cytoplasm_df = DataFrame()

        # checking if cytoplasm df is not None
        if cytoplasm_df_path:

            # loading cytoplasm df
            cytoplasm_df = load_df(input_path=cytoplasm_df_path)

        # getting cols num to add per df
        cols_num_by_df = get_cols_num_by_df(dots_df=dots_df,
                                            cytoplasm_df=cytoplasm_df,
                                            border_description=border_description)

        # assembling df name to df dict
        dfs_by_name = {'embryos': embryos_df,
                       'nuclei': nuclei_df,
                       'dots': dots_df,
                       'cytoplasm': cytoplasm_df}

        # getting dict items
        dict_items = dfs_by_name.items()

        # iterating over dfs
        for df_item in dict_items:

            # getting current df name/df
            df_name, current_df = df_item

            # getting current df's cols/rows num
            current_cols_num = cols_num_by_df[df_name]
            current_rows_num = len(current_df)

            # getting current df's cols/rows range
            current_cols_range = range(current_cols_num)
            current_rows_range = range(current_rows_num)

            # iterating over cols to add
            for _ in current_cols_range:

                # updating progress tracker attributes
                self.cols_num += 1

                # iterating over rows
                for _ in current_rows_range:

                    # updating progress tracker attributes
                    self.rows_num += 1
                    self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | cols: {self.cols_num}'
        totals_string += f' | rows: {self.rows_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_cols_num_by_df(dots_df: DataFrame,
                       cytoplasm_df: DataFrame,
                       border_description: str
                       ) -> dict:
    """
    Given dots/cytoplasm dfs, returns a
    dict with the number of summary cols
    that will be added to each of
    embryos/nuclei/dots/cytoplasm dfs (mirrors
    add_summary_cols' conditional
    structure, i.e. the cols added by
    each add_*_cols function, for
    progress totals only - no columns are read or
    added here, so it's safe to call
    before any of them exist).

    Args:
        dots_df (DataFrame): The joined dots df.
        cytoplasm_df (DataFrame): The joined cytoplasm df (empty if not given).
        border_description (str): The borders masks description the dots distances were computed to.

    Returns:
        dict: A dictionary mapping each of "embryos"/"nuclei"/"dots"/"cytoplasm" to the number of summary cols to add.
    """
    # defining base cols num by df
    cols_num_by_df = {'embryos': 1,
                      'nuclei': 2,
                      'dots': 0,
                      'cytoplasm': 0}

    # getting dots df not empty bool
    dots_df_not_empty = (not dots_df.empty)

    # checking if dots df is not empty
    if dots_df_not_empty:

        # adding dots cols num
        cols_num_by_df['dots'] += 3

    # getting dot descriptions actually present in dots df
    dot_descriptions = get_dot_descriptions(dots_df=dots_df)

    # getting has pgl bool
    has_pgl = ('pgl' in dot_descriptions)

    # checking if dots df has a "pgl" description
    if has_pgl:
        cols_num_by_df['embryos'] += 1
        cols_num_by_df['nuclei'] += 2

    # getting distance col
    distance_col = f'distance_to_{border_description}'

    # getting has border distances bool
    has_border_distances = (distance_col in dots_df.columns)

    # getting nuclei cols num per dot description (distance col is nuclei only)
    nuclei_cols_per_dot_description = (3 if has_border_distances else 2)

    # iterating over dot descriptions
    for _ in dot_descriptions:

        # adding current dot description's cols num
        cols_num_by_df['embryos'] += 2
        cols_num_by_df['nuclei'] += nuclei_cols_per_dot_description

    # checking if cytoplasm df is not empty
    if not cytoplasm_df.empty:

        # adding cytoplasm cols num (embryo uid and embryo age)
        cols_num_by_df['cytoplasm'] += 2

    # returning cols num by df
    return cols_num_by_df


def get_embryo_uid_dict(embryos_df: DataFrame) -> dict:
    """
    Given embryos df, returns a dict
    mapping each embryo crop name to
    its embryo uid.

    Args:
        embryos_df (DataFrame): The joined embryos df.

    Returns:
        dict: A dictionary mapping each embryo crop name to its embryo uid.
    """
    # dropping duplicate crop names, keeping first match
    unique_embryos_df = embryos_df.drop_duplicates(subset='crop_name',
                                                   keep='first')

    # assembling crop name to embryo uid dict
    embryo_uid_dict = get_df_values_dict(df=unique_embryos_df,
                                         key_col='crop_name',
                                         value_col='uid')

    # returning embryo uid dict
    return embryo_uid_dict


def get_embryo_uid(row_data: Series,
                   embryo_uid_dict: dict
                   ) -> str:
    """
    Given a nuclei/dots/cytoplasm df
    row, and respective embryo uid
    dict, returns embryo uid.

    Args:
        row_data (Series): The nuclei/dots/cytoplasm df row to extract from.
        embryo_uid_dict (dict): A dictionary mapping each embryo crop name to its embryo uid.

    Returns:
        str: The row's embryo uid.
    """
    # getting current row info
    image_name = row_data['image_name']

    # getting embryo uid
    embryo_uid = embryo_uid_dict[image_name]

    # returning embryo uid
    return embryo_uid


def get_embryo_age(row_data: Series,
                   embryo_ages_dict: dict
                   ) -> int:
    """
    Given an embryo df row, and
    respective embryo ages dict (see
    cet.dataframes.df_ops.
    get_embryo_ages_dict), returns
    embryo age (0 if the embryo has
    no detected nuclei).

    Args:
        row_data (Series): The embryo df row to extract from.
        embryo_ages_dict (dict): A dictionary mapping each embryo uid to its age.

    Returns:
        int: The row's embryo age.
    """
    # getting current row info
    embryo_uid = row_data['uid']

    # getting current embryo age
    embryo_age = embryo_ages_dict.get(embryo_uid, 0)

    # returning embryo age
    return embryo_age


def get_embryo_uid_age(row_data: Series,
                       embryo_ages_dict: dict
                       ) -> int:
    """
    Given a nuclei/dots df row, and
    respective embryo ages dict (see
    cet.dataframes.df_ops.
    get_embryo_ages_dict), returns
    embryo age (0 if the embryo has
    no detected nuclei).

    Args:
        row_data (Series): The nuclei/dots df row to extract from.
        embryo_ages_dict (dict): A dictionary mapping each embryo uid to its age.

    Returns:
        int: The row's embryo age.
    """
    # getting current row info
    embryo_uid = row_data['embryo_uid']

    # getting current embryo age
    embryo_age = embryo_ages_dict.get(embryo_uid, 0)

    # returning embryo age
    return embryo_age


def get_nucleus_uid(row_data: Series) -> str:
    """
    Given a dots df row,
    returns nucleus uid.

    Args:
        row_data (Series): The dots df row to extract from.

    Returns:
        str: The row's nucleus uid.
    """
    # defining nucleus description
    nucleus_description = 'nuc'

    # getting current row info
    image_index = row_data['image_index']
    nucleus_id = row_data['nucleus_id']

    # getting nucleus uid
    nucleus_uid = get_uid(image_index=image_index,
                          description=nucleus_description,
                          object_id=nucleus_id)

    # returning nucleus uid
    return nucleus_uid


def get_dot_uid_col(description: str) -> str:
    """
    Given an object description ('emb'/
    'nuc'), returns the respective
    dots df col holding that object's
    uid.

    Args:
        description (str): The object description ("emb" or "nuc").

    Returns:
        str: The dots df column holding that object's uid.
    """
    # defining embryo description
    embryo_description = 'emb'

    # getting description is embryo bool
    description_is_embryo = (description == embryo_description)

    # getting dot uid col
    dot_uid_col = ('embryo_uid' if description_is_embryo else 'nucleus_uid')

    # returning dot uid col
    return dot_uid_col


def get_dot_counts_dict(dots_df: DataFrame,
                        description: str,
                        dot_description: str
                        ) -> dict:
    """
    Given dots df, an object
    description ('emb'/'nuc') and a
    dot description, returns a dict
    mapping each matching object's
    uid to its dot count.

    Args:
        dots_df (DataFrame): The joined dots df.
        description (str): The object description ("emb" or "nuc").
        dot_description (str): The dot description to filter dots_df by.

    Returns:
        dict: A dictionary mapping each matching object's uid to its dot count.
    """
    # getting dot uid col
    dot_uid_col = get_dot_uid_col(description=description)

    # filtering df by dot description
    current_dots_df = dots_df[dots_df['description'] == dot_description]

    # assembling dot counts dict
    dot_counts_dict = get_grouped_agg_dict(df=current_dots_df,
                                           group_col=dot_uid_col,
                                           agg='size')

    # returning dot counts dict
    return dot_counts_dict


def get_dot_count(row_data: Series,
                  dot_counts_dict: dict
                  ) -> int:
    """
    Given an embryos/nuclei df row,
    and respective dot counts dict,
    returns dot count (0 if no
    matching dots).

    Args:
        row_data (Series): The embryos/nuclei df row to extract from.
        dot_counts_dict (dict): A dictionary mapping each matching object's uid to its dot count.

    Returns:
        int: The row's dot count.
    """
    # getting current row info
    current_object_uid = row_data['uid']

    # getting current dot count
    dot_count = dot_counts_dict.get(current_object_uid, 0)

    # returning dot count
    return dot_count


def get_dot_volumes_dict(dots_df: DataFrame,
                         description: str,
                         dot_description: str
                         ) -> dict:
    """
    Given dots df, an object
    description ('emb'/'nuc') and a
    dot description, returns a dict
    mapping each matching object's
    uid to its total dot volume.

    Args:
        dots_df (DataFrame): The joined dots df.
        description (str): The object description ("emb" or "nuc").
        dot_description (str): The dot description to filter dots_df by.

    Returns:
        dict: A dictionary mapping each matching object's uid to its total dot volume.
    """
    # defining volume col
    volume_col = 'volume'

    # getting dot uid col
    dot_uid_col = get_dot_uid_col(description=description)

    # filtering df by dot description
    current_dots_df = dots_df[dots_df['description'] == dot_description]

    # assembling dot volumes dict
    dot_volumes_dict = get_grouped_agg_dict(df=current_dots_df,
                                            group_col=dot_uid_col,
                                            agg='sum',
                                            value_col=volume_col)

    # returning dot volumes dict
    return dot_volumes_dict


def get_dot_volume(row_data: Series,
                   dot_volumes_dict: dict
                   ) -> float:
    """
    Given an embryos/nuclei df row,
    and respective dot volumes dict,
    returns dot volume (0.0 if no
    matching dots).

    Args:
        row_data (Series): The embryos/nuclei df row to extract from.
        dot_volumes_dict (dict): A dictionary mapping each matching object's uid to its total dot volume.

    Returns:
        float: The row's dot volume.
    """
    # getting current row info
    current_object_uid = row_data['uid']

    # getting current dot volume
    dot_volume = dot_volumes_dict.get(current_object_uid, 0.0)

    # returning dot volume
    return dot_volume


def get_dot_distances_dict(dots_df: DataFrame,
                           description: str,
                           dot_description: str,
                           border_description: str
                           ) -> dict:
    """
    Given dots df, an object
    description ('emb'/'nuc') and a
    dot description, returns a dict
    mapping each matching object's
    uid to its mean dot distance to
    mask.

    Args:
        dots_df (DataFrame): The joined dots df.
        description (str): The object description ("emb" or "nuc").
        dot_description (str): The dot description to filter dots_df by.
        border_description (str): The borders masks description the dots distances were computed to.

    Returns:
        dict: A dictionary mapping each matching object's uid to its mean dot distance to mask.
    """
    # defining distance col
    distance_col = f'distance_to_{border_description}'

    # getting dot uid col
    dot_uid_col = get_dot_uid_col(description=description)

    # filtering df by dot description
    current_dots_df = dots_df[dots_df['description'] == dot_description]

    # assembling dot distances dict
    dot_distances_dict = get_grouped_agg_dict(df=current_dots_df,
                                              group_col=dot_uid_col,
                                              agg='mean',
                                              value_col=distance_col)

    # returning dot distances dict
    return dot_distances_dict


def get_dot_distance_to_mask(row_data: Series,
                             dot_distances_dict: dict
                             ) -> float | None:
    """
    Given an embryos/nuclei df row,
    and respective dot distances
    dict, returns dot distance to
    mask (None if no matching dots).

    Args:
        row_data (Series): The embryos/nuclei df row to extract from.
        dot_distances_dict (dict): A dictionary mapping each matching object's uid to its mean dot distance to mask.

    Returns:
        float | None: The row's dot distance to mask, or None if no matching dots.
    """
    # getting current row info
    current_object_uid = row_data['uid']

    # getting current dot distance
    dots_distance = dot_distances_dict.get(current_object_uid, None)

    # returning dot distance
    return dots_distance


def get_dot_descriptions(dots_df: DataFrame) -> list:
    """
    Given dots df, returns the sorted
    list of dot descriptions actually
    present in it (empty list if
    dots df is empty). Sorted for
    deterministic column order
    across runs, independent of row
    order in the joined df.

    Args:
        dots_df (DataFrame): The joined dots df.

    Returns:
        list: The sorted list of dot descriptions present in dots_df.
    """
    # defining placeholder value for dot descriptions
    dot_descriptions = []

    # getting dots df not empty bool
    dots_df_not_empty = (not dots_df.empty)

    # checking if dots df is empty
    if dots_df_not_empty:

        # getting dots description col
        dots_description_col = dots_df['description']

        # getting dots unique descriptions
        dot_descriptions = dots_description_col.unique()

        # converting data types
        dot_descriptions = dot_descriptions.tolist()

        # sorting list
        dot_descriptions = sorted(dot_descriptions)

    # returning dot descriptions
    return dot_descriptions


def get_dot_cols(embryos_df: DataFrame,
                 nuclei_df: DataFrame,
                 dots_df: DataFrame,
                 dot_description: str,
                 border_description: str
                 ) -> list:
    """
    Given embryos/nuclei/dots joined
    dfs (dots df already containing
    embryo_uid/nucleus_uid cols) and
    a single dot description, returns
    that dot's count/volume/distance
    cols to add (embryos + nuclei),
    with lookup dicts pre-built.

    Args:
        embryos_df (DataFrame): The joined embryos df.
        nuclei_df (DataFrame): The joined nuclei df.
        dots_df (DataFrame): The joined dots df.
        dot_description (str): The dot description to build cols for.
        border_description (str): The borders masks description the dots distances were computed to.

    Returns:
        list: The dot description's count/volume/distance cols to add.
    """
    # building count/volume/distance dicts
    embryo_dot_counts_dict = get_dot_counts_dict(dots_df=dots_df, description='emb', dot_description=dot_description)
    nuclei_dot_counts_dict = get_dot_counts_dict(dots_df=dots_df, description='nuc', dot_description=dot_description)
    embryo_dot_volumes_dict = get_dot_volumes_dict(dots_df=dots_df, description='emb', dot_description=dot_description)
    nuclei_dot_volumes_dict = get_dot_volumes_dict(dots_df=dots_df, description='nuc', dot_description=dot_description)

    # getting distance col
    distance_col = f'distance_to_{border_description}'

    # getting has border distances bool
    has_border_distances = (distance_col in dots_df.columns)

    # assembling current dot cols to add list
    dot_cols = [

        # dot count (embryos)
        {'df': embryos_df,
         'df_name': 'embryos',
         'col_name': f'{dot_description}_count',
         'func': get_dot_count,
         'func_kwargs': {'dot_counts_dict': embryo_dot_counts_dict}},

        # dot count (nuclei)
        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': f'{dot_description}_count',
         'func': get_dot_count,
         'func_kwargs': {'dot_counts_dict': nuclei_dot_counts_dict}},

        # dot volume (embryos)
        {'df': embryos_df,
         'df_name': 'embryos',
         'col_name': f'{dot_description}_volume',
         'func': get_dot_volume,
         'func_kwargs': {'dot_volumes_dict': embryo_dot_volumes_dict}},

        # dot volume (nuclei)
        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': f'{dot_description}_volume',
         'func': get_dot_volume,
         'func_kwargs': {'dot_volumes_dict': nuclei_dot_volumes_dict}}

    ]

    # adding dot distance cols if dots df has border distances
    if has_border_distances:

        # building distance dict
        nuclei_dot_distances_dict = get_dot_distances_dict(dots_df=dots_df,
                                                           description='nuc',
                                                           dot_description=dot_description,
                                                           border_description=border_description)

        # assembling dot distance cols
        dot_distance_cols = [

            # dot distance (nuclei)
            {'df': nuclei_df,
             'df_name': 'nuclei',
             'col_name': f'{dot_description}_mean_distance_to_{border_description}',
             'func': get_dot_distance_to_mask,
             'func_kwargs': {'dot_distances_dict': nuclei_dot_distances_dict}}

        ]

        # appending dot distance cols
        dot_cols.extend(dot_distance_cols)

    # returning current dot cols
    return dot_cols


def get_pcell_dict(nuclei_df: DataFrame,
                   embryo_ages_dict: dict,
                   volume_threshold: float = 0.05,
                   age_threshold: int = 100
                   ) -> dict:
    """
    Given nuclei df (already containing
    "pgl_volume"/"embryo_uid"/"uid" cols)
    and respective embryo ages dict,
    returns a dict mapping each pcell
    nucleus's uid to True - picking, per
    embryo, the single highest-pgl_volume
    nucleus (pre-germline-division embryos,
    age <= age_threshold) or the top 2
    (post-division embryos, age >
    age_threshold), among nuclei whose
    pgl_volume clears volume_threshold.

    Args:
        nuclei_df (DataFrame): The joined nuclei df.
        embryo_ages_dict (dict): A dictionary mapping each embryo uid to its age.
        volume_threshold (float): The "pgl_volume" threshold a nucleus must clear to be a pcell candidate.
        age_threshold (int): The embryo age above which 2 (instead of 1) nuclei are picked per embryo.

    Returns:
        dict: A dictionary mapping each pcell nucleus's uid to True.
    """
    # filtering out nuclei with no meaningful pgl signal
    candidates_df = nuclei_df[nuclei_df['pgl_volume'] > volume_threshold]

    # defining placeholder value for pcell dict
    pcell_dict = {}

    # defining group col
    group_col = 'embryo_uid'

    # grouping df
    df_groups = candidates_df.groupby(group_col)

    # iterating over embryo groups
    for embryo_uid, embryo_group in df_groups:

        # getting current embryo age
        embryo_age = embryo_ages_dict.get(embryo_uid, 0)

        # getting current top nuclei num
        top_nuclei_num = (2 if (embryo_age > age_threshold) else 1)

        # getting current embryo's top pgl_volume nuclei
        top_nuclei_df = embryo_group.nlargest(top_nuclei_num, 'pgl_volume')

        # getting current uids
        current_uids = top_nuclei_df['uid']

        # iterating over uids
        for uid in current_uids:

            # assembling current dict
            current_dict = {uid: True}

            # updating pcell dict
            pcell_dict.update(current_dict)

    # returning pcell dict
    return pcell_dict


def get_pcell_bool(row_data: Series,
                   pcell_dict: dict
                   ) -> bool:
    """
    Given a nuclei df row, and
    respective pcell dict, returns
    pcell bool (False if the row's
    uid is not in the dict).

    Args:
        row_data (Series): The nuclei df row to extract from.
        pcell_dict (dict): A dictionary mapping each pcell nucleus's uid to True.

    Returns:
        bool: Whether the row is a pcell.
    """
    # getting current row info
    current_uid = row_data['uid']

    # getting current pcell bool
    pcell_bool = pcell_dict.get(current_uid, False)

    # returning pcell bool
    return pcell_bool


def get_contains_pcell_dict(nuclei_df: DataFrame) -> dict:
    """
    Given nuclei df (already
    containing a "pcell" col),
    returns a dict mapping each
    embryo uid to whether any of its
    nuclei is a pcell.

    Args:
        nuclei_df (DataFrame): The joined nuclei df, already containing a "pcell" col.

    Returns:
        dict: A dictionary mapping each embryo uid to whether it contains a pcell.
    """
    # assembling contains pcell dict
    contains_pcell_dict = get_grouped_agg_dict(df=nuclei_df,
                                               group_col='embryo_uid',
                                               agg='any',
                                               value_col='pcell')

    # returning contains pcell dict
    return contains_pcell_dict


def get_contains_pcell_bool(row_data: Series,
                            contains_pcell_dict: dict
                            ) -> bool:
    """
    Given an embryo df row, and
    respective contains pcell dict,
    returns contains pcell bool
    (False if the embryo has no
    nuclei).

    Args:
        row_data (Series): The embryo df row to extract from.
        contains_pcell_dict (dict): A dictionary mapping each embryo uid to whether it contains a pcell.

    Returns:
        bool: Whether the row's embryo contains a pcell.
    """
    # getting current row info
    embryo_uid = row_data['uid']

    # getting contains pcell bool
    contains_pcell = contains_pcell_dict.get(embryo_uid, False)

    # returning contains pcell bool
    return contains_pcell


def get_embryo_contains_pcell_dict(embryos_df: DataFrame) -> dict:
    """
    Given embryos df (already
    containing a "contains_pcell"
    col), returns a dict mapping
    each embryo uid to its contains
    pcell bool.

    Args:
        embryos_df (DataFrame): The joined embryos df, already containing a "contains_pcell" col.

    Returns:
        dict: A dictionary mapping each embryo uid to its contains pcell bool.
    """
    # assembling embryo contains pcell dict
    embryo_contains_pcell_dict = get_df_values_dict(df=embryos_df,
                                                    key_col='uid',
                                                    value_col='contains_pcell')

    # returning embryo contains pcell dict
    return embryo_contains_pcell_dict


def get_embryo_contains_pcell_bool(row_data: Series,
                                   embryo_contains_pcell_dict: dict
                                   ) -> bool:
    """
    Given a nuclei df row, and
    respective embryo uid to
    contains pcell dict, returns
    embryo contains pcell bool.

    Args:
        row_data (Series): The nuclei df row to extract from.
        embryo_contains_pcell_dict (dict): A dictionary mapping each embryo uid to its contains pcell bool.

    Returns:
        bool: Whether the row's embryo contains a pcell.
    """
    # getting current row info
    embryo_uid = row_data['embryo_uid']

    # getting current embryo contains pcell bool
    current_contains_pcell_bool = embryo_contains_pcell_dict.get(embryo_uid, False)

    # returning current embryo contains pcell bool
    return current_contains_pcell_bool


def add_embryo_id_cols(nuclei_df: DataFrame,
                       dots_df: DataFrame,
                       cytoplasm_df: DataFrame,
                       embryo_uid_dict: dict,
                       progress_tracker: ModuleProgressTracker
                       ) -> None:
    """
    Given nuclei/dots/cytoplasm joined
    dfs and an embryo uid dict, adds the
    "embryo_uid" col to nuclei, and to
    dots/cytoplasm if not empty.

    Args:
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        dots_df (DataFrame): The joined dots df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The joined cytoplasm df (modified in-place; empty if not given).
        embryo_uid_dict (dict): A dictionary mapping each embryo crop name to its embryo uid.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting dots/cytoplasm dfs not empty bools
    dots_df_not_empty = (not dots_df.empty)
    cytoplasm_df_not_empty = (not cytoplasm_df.empty)

    # defining embryo uid cols (nuclei)
    embryo_id_cols = [

        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': 'embryo_uid',
         'func': get_embryo_uid,
         'func_kwargs': {'embryo_uid_dict': embryo_uid_dict}}

    ]

    # checking if dots df is not empty
    if dots_df_not_empty:

        # defining embryo uid col (dots)
        dots_embryo_id_cols = [

            {'df': dots_df,
             'df_name': 'dots',
             'col_name': 'embryo_uid',
             'func': get_embryo_uid,
             'func_kwargs': {'embryo_uid_dict': embryo_uid_dict}}

        ]

        # appending dots embryo uid col
        embryo_id_cols.extend(dots_embryo_id_cols)

    # checking if cytoplasm df is not empty
    if cytoplasm_df_not_empty:

        # defining embryo uid col (cytoplasm)
        cytoplasm_embryo_id_cols = [

            {'df': cytoplasm_df,
             'df_name': 'cytoplasm',
             'col_name': 'embryo_uid',
             'func': get_embryo_uid,
             'func_kwargs': {'embryo_uid_dict': embryo_uid_dict}}

        ]

        # appending cytoplasm embryo uid col
        embryo_id_cols.extend(cytoplasm_embryo_id_cols)

    # adding embryo uid cols
    add_cols(col_dicts=embryo_id_cols,
             progress_tracker=progress_tracker)


def add_nucleus_id_cols(dots_df: DataFrame,
                        progress_tracker: ModuleProgressTracker
                        ) -> None:
    """
    Given dots joined df, adds the
    "nucleus_uid" col to it (does
    nothing if dots df is empty).

    Args:
        dots_df (DataFrame): The joined dots df (modified in-place; empty if not given).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting dots df not empty bool
    dots_df_not_empty = (not dots_df.empty)

    # checking if dots df is empty
    if not dots_df_not_empty:

        # returning
        return None

    # defining nucleus uid cols (dots)
    nucleus_id_cols = [

        {'df': dots_df,
         'df_name': 'dots',
         'col_name': 'nucleus_uid',
         'func': get_nucleus_uid}

    ]

    # adding nucleus uid cols
    add_cols(col_dicts=nucleus_id_cols,
             progress_tracker=progress_tracker)


def add_embryo_age_cols(embryos_df: DataFrame,
                        nuclei_df: DataFrame,
                        dots_df: DataFrame,
                        cytoplasm_df: DataFrame,
                        embryo_ages_dict: dict,
                        progress_tracker: ModuleProgressTracker
                        ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    joined dfs (nuclei/dots/cytoplasm
    already containing an "embryo_uid"
    col) and an embryo ages dict, adds the
    "embryo_age" col to embryos and nuclei,
    and to dots/cytoplasm if not empty.

    Args:
        embryos_df (DataFrame): The joined embryos df (modified in-place).
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        dots_df (DataFrame): The joined dots df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The joined cytoplasm df (modified in-place; empty if not given).
        embryo_ages_dict (dict): A dictionary mapping each embryo uid to its age.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting dots/cytoplasm dfs not empty bools
    dots_df_not_empty = (not dots_df.empty)
    cytoplasm_df_not_empty = (not cytoplasm_df.empty)

    # defining age cols (embryos + nuclei)
    age_cols = [

        {'df': embryos_df,
         'df_name': 'embryos',
         'col_name': 'embryo_age',
         'func': get_embryo_age,
         'func_kwargs': {'embryo_ages_dict': embryo_ages_dict}},

        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': 'embryo_age',
         'func': get_embryo_uid_age,
         'func_kwargs': {'embryo_ages_dict': embryo_ages_dict}}

    ]

    # checking if dots df is not empty
    if dots_df_not_empty:

        # defining age cols (dots)
        dots_age_cols = [

            {'df': dots_df,
             'df_name': 'dots',
             'col_name': 'embryo_age',
             'func': get_embryo_uid_age,
             'func_kwargs': {'embryo_ages_dict': embryo_ages_dict}}

        ]

        # appending dots age cols
        age_cols.extend(dots_age_cols)

    # checking if cytoplasm df is not empty
    if cytoplasm_df_not_empty:

        # defining age cols (cytoplasm)
        cytoplasm_age_cols = [

            {'df': cytoplasm_df,
             'df_name': 'cytoplasm',
             'col_name': 'embryo_age',
             'func': get_embryo_uid_age,
             'func_kwargs': {'embryo_ages_dict': embryo_ages_dict}}

        ]

        # appending cytoplasm age cols
        age_cols.extend(cytoplasm_age_cols)

    # adding embryo age cols
    add_cols(col_dicts=age_cols,
             progress_tracker=progress_tracker)


def add_dot_cols(embryos_df: DataFrame,
                 nuclei_df: DataFrame,
                 dots_df: DataFrame,
                 border_description: str,
                 progress_tracker: ModuleProgressTracker
                 ) -> None:
    """
    Given embryos/nuclei/dots joined dfs
    (dots df already containing
    embryo_uid/nucleus_uid cols), adds
    each dot description's
    count/volume/distance cols to
    embryos and nuclei.

    Args:
        embryos_df (DataFrame): The joined embryos df (modified in-place).
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        dots_df (DataFrame): The joined dots df (empty if not given).
        border_description (str): The borders masks description the dots distances were computed to.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting dot descriptions actually present in dots df
    dot_descriptions = get_dot_descriptions(dots_df=dots_df)

    # iterating over dot descriptions
    for dot_description in dot_descriptions:

        # getting current dot cols
        dot_cols = get_dot_cols(embryos_df=embryos_df,
                                nuclei_df=nuclei_df,
                                dots_df=dots_df,
                                dot_description=dot_description,
                                border_description=border_description)

        # adding current dot cols
        add_cols(col_dicts=dot_cols,
                 progress_tracker=progress_tracker)


def add_pcell_cols(nuclei_df: DataFrame,
                   embryo_ages_dict: dict,
                   progress_tracker: ModuleProgressTracker
                   ) -> None:
    """
    Given nuclei joined df (already
    containing "pgl_volume"/"embryo_uid"
    cols) and an embryo ages dict, adds
    the "pcell" col to it.

    Args:
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        embryo_ages_dict (dict): A dictionary mapping each embryo uid to its age.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting pcell dict
    pcell_dict = get_pcell_dict(nuclei_df=nuclei_df,
                                embryo_ages_dict=embryo_ages_dict)

    # defining pcell cols
    pcell_cols = [

        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': 'pcell',
         'func': get_pcell_bool,
         'func_kwargs': {'pcell_dict': pcell_dict}}

    ]

    # adding pcell bool col (nuclei)
    add_cols(col_dicts=pcell_cols,
             progress_tracker=progress_tracker)


def add_contains_pcell_cols(embryos_df: DataFrame,
                            nuclei_df: DataFrame,
                            progress_tracker: ModuleProgressTracker
                            ) -> None:
    """
    Given embryos/nuclei joined dfs
    (nuclei already containing a "pcell"
    col), adds the "contains_pcell" col
    to embryos.

    Args:
        embryos_df (DataFrame): The joined embryos df (modified in-place).
        nuclei_df (DataFrame): The joined nuclei df, already containing a "pcell" col.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting contains pcell dict
    contains_pcell_dict = get_contains_pcell_dict(nuclei_df=nuclei_df)

    # defining contains pcell cols
    contains_pcell_cols = [

        {'df': embryos_df,
         'df_name': 'embryos',
         'col_name': 'contains_pcell',
         'func': get_contains_pcell_bool,
         'func_kwargs': {'contains_pcell_dict': contains_pcell_dict}}

    ]

    # adding contains pcell bool col (embryos)
    add_cols(col_dicts=contains_pcell_cols,
             progress_tracker=progress_tracker)


def add_embryo_contains_pcell_cols(embryos_df: DataFrame,
                                   nuclei_df: DataFrame,
                                   progress_tracker: ModuleProgressTracker
                                   ) -> None:
    """
    Given embryos/nuclei joined dfs
    (embryos already containing a
    "contains_pcell" col), adds the
    "embryo_contains_pcell" col to
    nuclei.

    Args:
        embryos_df (DataFrame): The joined embryos df, already containing a "contains_pcell" col.
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting embryo contains pcell dict
    embryo_contains_pcell_dict = get_embryo_contains_pcell_dict(embryos_df=embryos_df)

    # defining embryo contains pcell cols
    embryo_contains_pcell_cols = [

        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': 'embryo_contains_pcell',
         'func': get_embryo_contains_pcell_bool,
         'func_kwargs': {'embryo_contains_pcell_dict': embryo_contains_pcell_dict}}

    ]

    # adding embryo contains pcell bool col (nuclei)
    add_cols(col_dicts=embryo_contains_pcell_cols,
             progress_tracker=progress_tracker)


def add_pcell_group_cols(embryos_df: DataFrame,
                         nuclei_df: DataFrame,
                         embryo_ages_dict: dict,
                         progress_tracker: ModuleProgressTracker
                         ) -> None:
    """
    Given embryos/nuclei joined dfs
    (nuclei already containing
    "pgl_volume"/"embryo_uid" cols) and an
    embryo ages dict, adds the pcell
    related cols, in dependency order
    (pcell, contains_pcell,
    embryo_contains_pcell).

    Args:
        embryos_df (DataFrame): The joined embryos df (modified in-place).
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        embryo_ages_dict (dict): A dictionary mapping each embryo uid to its age.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # adding pcell bool col (nuclei)
    add_pcell_cols(nuclei_df=nuclei_df,
                   embryo_ages_dict=embryo_ages_dict,
                   progress_tracker=progress_tracker)

    # adding contains pcell bool col (embryos)
    add_contains_pcell_cols(embryos_df=embryos_df,
                            nuclei_df=nuclei_df,
                            progress_tracker=progress_tracker)

    # adding embryo contains pcell bool col (nuclei)
    add_embryo_contains_pcell_cols(embryos_df=embryos_df,
                                   nuclei_df=nuclei_df,
                                   progress_tracker=progress_tracker)


def add_summary_cols(embryos_df: DataFrame,
                     nuclei_df: DataFrame,
                     dots_df: DataFrame,
                     cytoplasm_df: DataFrame,
                     border_description: str,
                     progress_tracker: ModuleProgressTracker
                     ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    joined dfs, adds summary columns linking
    info between dfs, in dependency
    order (each column group is added
    by its own function).

    Args:
        embryos_df (DataFrame): The joined embryos df (modified in-place).
        nuclei_df (DataFrame): The joined nuclei df (modified in-place).
        dots_df (DataFrame): The joined dots df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The joined cytoplasm df (modified in-place; empty if not given).
        border_description (str): The borders masks description the dots distances were computed to.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting embryo uid dict
    embryo_uid_dict = get_embryo_uid_dict(embryos_df=embryos_df)

    # adding embryo uid cols (nuclei + dots + cytoplasm)
    add_embryo_id_cols(nuclei_df=nuclei_df,
                       dots_df=dots_df,
                       cytoplasm_df=cytoplasm_df,
                       embryo_uid_dict=embryo_uid_dict,
                       progress_tracker=progress_tracker)

    # adding nucleus uid cols (dots)
    add_nucleus_id_cols(dots_df=dots_df,
                        progress_tracker=progress_tracker)

    # getting embryo ages dict
    embryo_ages_dict = get_embryo_ages_dict(df=nuclei_df)

    # adding embryo age cols (embryos + nuclei + dots + cytoplasm)
    add_embryo_age_cols(embryos_df=embryos_df,
                        nuclei_df=nuclei_df,
                        dots_df=dots_df,
                        cytoplasm_df=cytoplasm_df,
                        embryo_ages_dict=embryo_ages_dict,
                        progress_tracker=progress_tracker)

    # adding dot cols (embryos + nuclei)
    add_dot_cols(embryos_df=embryos_df,
                 nuclei_df=nuclei_df,
                 dots_df=dots_df,
                 border_description=border_description,
                 progress_tracker=progress_tracker)

    # getting dot descriptions actually present in dots df
    dot_descriptions = get_dot_descriptions(dots_df=dots_df)

    # getting has pgl bool
    has_pgl = ('pgl' in dot_descriptions)

    # adding pcell cols if dots df has a "pgl" description
    if has_pgl:

        # adding pcell related cols (nuclei + embryos)
        add_pcell_group_cols(embryos_df=embryos_df,
                             nuclei_df=nuclei_df,
                             embryo_ages_dict=embryo_ages_dict,
                             progress_tracker=progress_tracker)


def generate_summary_dfs(embryos_df_path: str,
                         nuclei_df_path: str,
                         dots_df_path: str,
                         cytoplasm_df_path: str,
                         output_folder: str,
                         overwrite_output: bool,
                         border_description: str,
                         progress_tracker: ModuleProgressTracker
                         ) -> None:
    """
    Given embryos/nuclei/dots joined
    dfs (and, optionally, the cytoplasm
    joined df), generates summary dfs as per
    embryo, per nucleus, per dot and per
    cytoplasm, linking info between them
    and saving output to given folder
    (normalization is done afterwards, by
    normalize_summary_dfs).

    Args:
        embryos_df_path (str): The path to the joined embryos/pseudoembryos df.
        nuclei_df_path (str): The path to the joined nuclei df.
        dots_df_path (str): The path to the joined dots df, or None to skip dots.
        cytoplasm_df_path (str): The path to the joined cytoplasm df, or None to skip cytoplasm.
        output_folder (str): The path to the folder to save summary dfs to.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        border_description (str): The borders masks description the dots distances were computed to.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # defining save names/paths
    embryos_save_name = 'embryos_summary_df.csv'
    embryos_save_path = join(output_folder,
                             embryos_save_name)
    nuclei_save_name = 'nuclei_summary_df.csv'
    nuclei_save_path = join(output_folder,
                            nuclei_save_name)
    dots_save_name = 'dots_summary_df.csv'
    dots_save_path = join(output_folder,
                          dots_save_name)
    cytoplasm_save_name = 'cytoplasm_summary_df.csv'
    cytoplasm_save_path = join(output_folder,
                               cytoplasm_save_name)

    # assembling list of applicable output paths
    outputs_to_check = [embryos_save_path,
                        nuclei_save_path]

    # checking if dots df is not None
    if dots_df_path:

        # adding dots output path
        outputs_to_check.append(dots_save_path)

    # checking if cytoplasm df is not None
    if cytoplasm_df_path:

        # adding cytoplasm output path
        outputs_to_check.append(cytoplasm_save_path)

    # getting skip file bools for every applicable output
    skip_bools = [get_skip_file_bool(file_path=output_path,
                                     overwrite_output=overwrite_output)
                  for output_path in outputs_to_check]

    # checking whether every applicable output already exists
    if all(skip_bools):

        # sleeping
        progress_tracker.wait(0.05)

        # updating progress tracker attributes
        progress_tracker.current_iteration += progress_tracker.iterations_num
        progress_tracker.skipped_iterations += progress_tracker.iterations_num

        # skipping
        return None

    # loading embryo/nuclei dfs
    embryos_df = load_df(input_path=embryos_df_path)
    nuclei_df = load_df(input_path=nuclei_df_path)

    # defining placeholder value for dots df
    dots_df = DataFrame()

    # checking if dots df is not None
    if dots_df_path:

        # loading dots df
        dots_df = load_df(input_path=dots_df_path)

    # defining placeholder value for cytoplasm df
    cytoplasm_df = DataFrame()

    # checking if cytoplasm df is not None
    if cytoplasm_df_path:

        # loading cytoplasm df
        cytoplasm_df = load_df(input_path=cytoplasm_df_path)

    # adding summary cols
    add_summary_cols(embryos_df=embryos_df,
                     nuclei_df=nuclei_df,
                     dots_df=dots_df,
                     cytoplasm_df=cytoplasm_df,
                     border_description=border_description,
                     progress_tracker=progress_tracker)

    # saving embryos/nuclei dfs
    save_df(save_path=embryos_save_path,
            df=embryos_df)
    save_df(save_path=nuclei_save_path,
            df=nuclei_df)

    # checking if dots df is not None
    if dots_df_path:

        # saving dots df
        save_df(save_path=dots_save_path,
                df=dots_df)

    # checking if cytoplasm df is not None
    if cytoplasm_df_path:

        # saving cytoplasm df
        save_df(save_path=cytoplasm_save_path,
                df=cytoplasm_df)


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
    # getting embryos df path
    embryos_df_path = args_dict['embryos_df_path']

    # getting nuclei df path
    nuclei_df_path = args_dict['nuclei_df_path']

    # getting dots df path
    dots_df_path = args_dict['dots_df_path']

    # getting cytoplasm df path
    cytoplasm_df_path = args_dict['cytoplasm_df_path']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # getting border description
    border_description = args_dict['border_description']

    # running generate_summary_dfs function
    generate_summary_dfs(embryos_df_path=embryos_df_path,
                         nuclei_df_path=nuclei_df_path,
                         dots_df_path=dots_df_path,
                         cytoplasm_df_path=cytoplasm_df_path,
                         output_folder=output_folder,
                         overwrite_output=overwrite_output,
                         border_description=border_description,
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
