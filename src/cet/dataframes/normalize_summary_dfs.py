# normalize summary dfs module

print('initializing...')  # noqa

# Code destined to adding embryo age bin
# and normalized cols (age bin rescaled
# intensities for all summary dataframes,
# plus volume and border distance (by
# volume radius) normalized cols for
# nuclei).

######################################################################
# imports

print('importing required libraries...')  # noqa
import re
from pandas import isna
from os.path import join
from pandas import Series
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from cet.dataframes.df_ops import add_cols
from cet.io.files import get_skip_file_bool
from cet.dataframes.df_ops import get_df_values_dict
from cet.dataframes.df_ops import get_grouped_agg_dict
from cet.dataframes.df_ops import get_normalized_value
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.dataframes.df_ops import filter_pandas_performance_warnings
print('all required libraries successfully imported.')  # noqa

# filtering Pandas Performance Warnings
filter_pandas_performance_warnings()

######################################################################
# defining constants

# intensity stats (as named in "<prefix>_<stat>_intensity" cols; see cet.measurements.intensity)
INTENSITY_STATS = ['min',
                   'max',
                   'mean',
                   'no_zero_mean',
                   'sum',
                   'std',
                   'median',
                   'no_zero_median',
                   'mode',
                   'mode_ratio']

# location-like stats, i.e. the ones that shift/scale together with the signal (so an affine rescaling
# makes sense). std, sum, mode and mode_ratio are excluded (mode is an integer-valued, noisy estimate,
# so not worth rescaling); quantiles (q<N>) also qualify
NORMALIZABLE_STATS = ['min',
                      'max',
                      'mean',
                      'no_zero_mean',
                      'median',
                      'no_zero_median']

# stats whose per age bin medians (over embryos) are the ref_lo / ref_hi values used to rescale intensities
REF_LO_STAT = 'q01'
REF_HI_STAT = 'q95'

# embryo gains outside this range are flagged (not clamped)
GAIN_FLAG_MIN = 0.5
GAIN_FLAG_MAX = 2.0

# regex matching "<prefix>_<stat>_intensity" cols (stat being one of INTENSITY_STATS or a quantile like q95)
INTENSITY_STATS_PATTERN = '|'.join(INTENSITY_STATS + [r'q\d+'])
INTENSITY_COL_REGEX = re.compile(rf'(?P<prefix>.+?)_(?P<stat>{INTENSITY_STATS_PATTERN})_intensity')

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
    description = "normalize summary dfs module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # embryos summary df path param
    parser.add_argument('-e', '--embryos-df-path',
                        dest='embryos_df_path',
                        type=str,
                        required=True,
                        help='defines path to embryos summary df [.csv] (saved unchanged, with "_normalized" suffix)')

    # nuclei summary df path param
    parser.add_argument('-n', '--nuclei-df-path',
                        dest='nuclei_df_path',
                        type=str,
                        required=True,
                        help='defines path to nuclei summary df [.csv]')

    # dots summary df path param
    parser.add_argument('-d', '--dots-df-path',
                        dest='dots_df_path',
                        type=str,
                        required=False,
                        default=None,
                        help='defines path to dots summary df [.csv] (optional; saved unchanged, with "_normalized" suffix)')

    # cytoplasm summary df path param
    parser.add_argument('-c', '--cytoplasm-df-path',
                        dest='cytoplasm_df_path',
                        type=str,
                        required=False,
                        default=None,
                        help='defines path to cytoplasm summary df [.csv] (optional; gets an age bin col and is saved with "_normalized" suffix)')

    # min age param
    parser.add_argument('-min', '--min-age',
                        dest='min_age',
                        type=int,
                        required=False,
                        default=1,
                        help='defines embryo age at which the first age bin starts (the first bin spans min age to '
                             'min age + age bin - 1, e.g. 20-69 for a 50 age bin; younger embryos are put in the '
                             'first bin; default: 1)')

    # max age param
    parser.add_argument('-max', '--max-age',
                        dest='max_age',
                        type=int,
                        required=False,
                        default=550,
                        help='defines embryo age at which the last age bin ends (embryos older than max age are '
                             'put in a single "> max age" bin; default: 550)')

    # age bin param
    parser.add_argument('-b', '--age-bin',
                        dest='age_bin',
                        type=int,
                        required=False,
                        default=20,
                        help='defines embryo age bin width (in embryo age units; intensities are rescaled within each bin)')

    # border description param
    parser.add_argument('-bd', '--border-description',
                        dest='border_description',
                        type=str,
                        required=False,
                        default='border',
                        help='defines description of the borders masks the dots distances were computed to (summary cols are named "<prefix>_mean_distance_to_<description>")')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain the normalized dfs [.csv])')

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
            progress_string += f'adding normalized cols...'
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
        cols_num_by_df = get_cols_num_by_df(embryos_df=embryos_df,
                                            nuclei_df=nuclei_df,
                                            dots_df=dots_df,
                                            cytoplasm_df=cytoplasm_df,
                                            border_description=border_description)

        # assembling df name to df dict
        dfs_by_name = {'embryos': embryos_df,
                       'nuclei': nuclei_df,
                       'dots': dots_df,
                       'cytoplasm': cytoplasm_df}

        # getting dict items
        dict_items = dfs_by_name.items()

        # iterating over dict items
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


def get_volume_normalized_cols_to_add(df: DataFrame,
                                      df_name: str
                                      ) -> list:
    """
    Given a summary df, auto-detects the
    volume normalized cols to derive and
    returns them as a list of add_col-style
    col dicts: every "<prefix>_volume" col
    (e.g. pgl_volume) gets a "_normalized"
    col, i.e. col / "volume".
    Only df's col names are read, so a
    names-only df works too.

    Args:
        df (DataFrame): The summary df to detect cols in.
        df_name (str): The df's name (as shown in the progress string).

    Returns:
        list: The normalized cols to add.
    """
    # defining cols to add placeholder
    cols_to_add = []

    # getting df cols set
    df_cols = set(df.columns)

    # iterating over df cols
    for col in df.columns:

        # skipping cols that were already derived
        if col.endswith('_normalized'):

            # skipping
            continue

        # getting col is normalized by volume bool
        col_is_normalized_by_volume = (col.endswith('_volume') and ('volume' in df_cols))

        # checking if col is a volume col (excluding the reference volume col)
        if col_is_normalized_by_volume:

            # assembling current dict
            current_dict = {'df': df,
                            'df_name': df_name,
                            'col_name': f'{col}_normalized',
                            'func': get_normalized_value,
                            'func_kwargs': {'value_col': col,
                                            'reference_col': 'volume'}}

            # appending current dict to cols to add
            cols_to_add.append(current_dict)

    # returning cols to add
    return cols_to_add


def get_distance_normalized_cols_to_add(df: DataFrame,
                                        df_name: str,
                                        border_description: str
                                        ) -> list:
    """
    Given a summary df, auto-detects the
    distance normalized cols to derive and
    returns them as a list of add_col-style
    col dicts: every
    "<prefix>_distance_to_<border_description>"
    col (e.g. h3k9_mean_distance_to_border)
    gets a "_normalized" col, i.e. col /
    "volume_radius".
    Only df's col names are read, so a
    names-only df works too.

    Args:
        df (DataFrame): The summary df to detect cols in.
        df_name (str): The df's name (as shown in the progress string).
        border_description (str): The borders masks description the dots distances were computed to.

    Returns:
        list: The normalized cols to add.
    """
    # defining cols to add placeholder
    cols_to_add = []

    # getting df cols set
    df_cols = set(df.columns)

    # getting distance col suffix
    distance_suffix = f'_distance_to_{border_description}'

    # iterating over df cols
    for col in df.columns:

        # skipping cols that were already derived
        if col.endswith('_normalized'):

            # skipping
            continue

        # getting col is normalized by volume radius bool
        col_is_normalized_by_volume_radius = (col.endswith(distance_suffix) and ('volume_radius' in df_cols))

        # checking if col is a border distance col
        if col_is_normalized_by_volume_radius:

            # assembling current dict
            current_dict = {'df': df,
                            'df_name': df_name,
                            'col_name': f'{col}_normalized',
                            'func': get_normalized_value,
                            'func_kwargs': {'value_col': col,
                                            'reference_col': 'volume_radius'}}

            # appending current dict to cols to add
            cols_to_add.append(current_dict)

    # returning cols to add
    return cols_to_add


def get_volume_normalized_cols_num(nuclei_df: DataFrame) -> int:
    """
    Given nuclei summary df (before any
    normalized col was added), returns the
    number of volume normalized cols that
    will be added to it. Only col names are
    read, so it's safe to call before any
    col exists.

    Args:
        nuclei_df (DataFrame): The nuclei summary df.

    Returns:
        int: The number of volume normalized cols to add to nuclei df.
    """
    # getting normalized cols to add
    cols_to_add = get_volume_normalized_cols_to_add(df=nuclei_df,
                                                    df_name='nuclei')

    # getting normalized cols num
    normalized_cols_num = len(cols_to_add)

    # returning normalized cols num
    return normalized_cols_num


def get_distance_normalized_cols_num(nuclei_df: DataFrame,
                                     border_description: str
                                     ) -> int:
    """
    Given nuclei summary df (before any
    normalized col was added), returns the
    number of border distance normalized
    cols that will be added to it. Only col
    names are read, so it's safe to call
    before any col exists.

    Args:
        nuclei_df (DataFrame): The nuclei summary df.
        border_description (str): The borders masks description the dots distances were computed to.

    Returns:
        int: The number of distance normalized cols to add to nuclei df.
    """
    # getting normalized cols to add
    cols_to_add = get_distance_normalized_cols_to_add(df=nuclei_df,
                                                      df_name='nuclei',
                                                      border_description=border_description)

    # getting normalized cols num
    normalized_cols_num = len(cols_to_add)

    # returning normalized cols num
    return normalized_cols_num


def get_intensity_cols_dict(df: DataFrame) -> dict:
    """
    Given a summary df, returns a dict
    mapping each marker prefix (h3k9, dapi
    etc) to its list of intensity cols that
    can be rescaled, i.e. the
    "<prefix>_<stat>_intensity" cols whose
    stat is location-like (see
    NORMALIZABLE_STATS, plus quantiles).
    Background and already derived cols are
    excluded. Only col names are read, so a
    names-only df works too.

    Args:
        df (DataFrame): The summary df.

    Returns:
        dict: A dictionary mapping each marker prefix to its intensity cols.
    """
    # defining intensity cols dict placeholder
    intensity_cols_dict = {}

    # iterating over df cols
    for col in df.columns:

        # checking if col is an intensity col
        intensity_match = INTENSITY_COL_REGEX.fullmatch(col)

        # skipping non-intensity cols and background cols
        if (not intensity_match) or ('background' in col):

            # skipping
            continue

        # getting current prefix/stat
        prefix = intensity_match.group('prefix')
        stat = intensity_match.group('stat')

        # getting stat is normalizable bool (location-like stats and quantiles)
        stat_is_normalizable = (stat in NORMALIZABLE_STATS) or re.fullmatch(r'q\d+', stat)

        # skipping stats that are not location-like (e.g. std, sum)
        if not stat_is_normalizable:

            # skipping
            continue

        # getting current prefix cols
        prefix_cols = intensity_cols_dict.get(prefix, [])

        # appending current col to prefix cols
        prefix_cols.append(col)

        # assembling current dict
        current_dict = {prefix: prefix_cols}

        # updating intensity cols dict
        intensity_cols_dict.update(current_dict)

    # returning intensity cols dict
    return intensity_cols_dict


def get_rescale_prefixes(df: DataFrame) -> list:
    """
    Given a summary df (the embryos df, which
    holds the embryo and reference values),
    returns the marker prefixes that can be
    rescaled by embryo age bin, i.e. those
    having both the REF_LO_STAT and
    REF_HI_STAT intensity cols. Only col
    names are read, so a names-only df works
    too.

    Args:
        df (DataFrame): The summary df.

    Returns:
        list: The marker prefixes to rescale.
    """
    # getting df cols set
    df_cols = set(df.columns)

    # getting intensity cols dict
    intensity_cols_dict = get_intensity_cols_dict(df=df)

    # defining rescale prefixes placeholder
    rescale_prefixes = []

    # iterating over marker prefixes
    for prefix in intensity_cols_dict:

        # getting lo/hi cols
        lo_col = f'{prefix}_{REF_LO_STAT}_intensity'
        hi_col = f'{prefix}_{REF_HI_STAT}_intensity'

        # checking if both lo/hi cols are present
        if (lo_col in df_cols) and (hi_col in df_cols):

            # appending current prefix to rescale prefixes
            rescale_prefixes.append(prefix)

    # returning rescale prefixes
    return rescale_prefixes


def get_df_rescale_prefixes(df: DataFrame,
                            rescale_prefixes: list
                            ) -> list:
    """
    Given a summary df and the marker
    prefixes that can be rescaled (see
    get_rescale_prefixes), returns the ones
    that also have intensity cols in given df
    (an empty df has none). Only col names
    are read, so a names-only df works too.

    Args:
        df (DataFrame): The summary df.
        rescale_prefixes (list): The marker prefixes that can be rescaled.

    Returns:
        list: The marker prefixes to rescale in given df.
    """
    # getting intensity cols dict
    intensity_cols_dict = get_intensity_cols_dict(df=df)

    # defining df rescale prefixes placeholder
    df_rescale_prefixes = []

    # iterating over rescale prefixes
    for prefix in rescale_prefixes:

        # checking if df has intensity cols for current prefix
        if prefix in intensity_cols_dict:

            # appending current prefix to df rescale prefixes
            df_rescale_prefixes.append(prefix)

    # returning df rescale prefixes
    return df_rescale_prefixes


def get_rescale_cols_num(df: DataFrame,
                         rescale_prefixes: list
                         ) -> int:
    """
    Given a summary df (before any
    normalized col was added) and the marker
    prefixes that can be rescaled, returns the
    number of age bin rescaling cols that
    will be added to it: for each marker with
    intensity cols in df, ref_lo / ref_hi,
    embryo_lo / embryo_hi, gain, offset and
    gain flag cols, and a rescaled col for
    each intensity col. Only col names are
    read, so it's safe to call before any col
    exists.

    Args:
        df (DataFrame): The summary df.
        rescale_prefixes (list): The marker prefixes that can be rescaled.

    Returns:
        int: The number of rescaling cols to add to given df.
    """
    # getting intensity cols dict
    intensity_cols_dict = get_intensity_cols_dict(df=df)

    # getting df rescale prefixes
    df_rescale_prefixes = get_df_rescale_prefixes(df=df,
                                                  rescale_prefixes=rescale_prefixes)

    # defining rescale cols num
    rescale_cols_num = 0

    # iterating over df rescale prefixes
    for prefix in df_rescale_prefixes:

        # getting prefix intensity cols num
        prefix_cols_num = len(intensity_cols_dict[prefix])

        # adding ref_lo / ref_hi cols, embryo_lo / embryo_hi cols, gain / offset / gain flag cols and rescaled cols
        rescale_cols_num += (7 + prefix_cols_num)

    # returning rescale cols num
    return rescale_cols_num


def get_cols_num_by_df(embryos_df: DataFrame,
                       nuclei_df: DataFrame,
                       dots_df: DataFrame,
                       cytoplasm_df: DataFrame,
                       border_description: str
                       ) -> dict:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs, returns a dict with the number of
    normalized cols that will be added to
    each of embryos/nuclei/dots/cytoplasm
    dfs (mirrors add_normalized_cols'
    conditional structure, for progress
    totals only - no columns are added
    here, so it's safe to call before any
    of them exist).

    Args:
        embryos_df (DataFrame): The embryos summary df.
        nuclei_df (DataFrame): The nuclei summary df.
        dots_df (DataFrame): The dots summary df (empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (empty if not given).
        border_description (str): The borders masks description the dots distances were computed to.

    Returns:
        dict: A dictionary mapping each of "embryos"/"nuclei"/"dots"/"cytoplasm" to the number of normalized cols to add.
    """
    # defining base cols num by df (embryo age bin col)
    cols_num_by_df = {'embryos': 1,
                      'nuclei': 1,
                      'dots': 0,
                      'cytoplasm': 0}

    # checking if dots df is not empty
    if not dots_df.empty:

        # adding dots cols num
        cols_num_by_df['dots'] += 1

    # checking if cytoplasm df is not empty
    if not cytoplasm_df.empty:

        # adding cytoplasm cols num
        cols_num_by_df['cytoplasm'] += 1

    # getting volume normalized cols num (nuclei)
    cols_num_by_df['nuclei'] += get_volume_normalized_cols_num(nuclei_df=nuclei_df)

    # getting distance normalized cols num (nuclei)
    cols_num_by_df['nuclei'] += get_distance_normalized_cols_num(nuclei_df=nuclei_df,
                                                                 border_description=border_description)

    # getting rescale prefixes (from embryos df)
    rescale_prefixes = get_rescale_prefixes(df=embryos_df)

    # assembling df name to df dict
    dfs_by_name = {'embryos': embryos_df,
                   'nuclei': nuclei_df,
                   'dots': dots_df,
                   'cytoplasm': cytoplasm_df}

    # getting dict items
    dict_items = dfs_by_name.items()

    # iterating over dict items
    for df_item in dict_items:

        # getting current df name/df
        df_name, current_df = df_item

        # adding current df's rescaling cols num (an empty placeholder df has no intensity cols, so it adds none)
        cols_num_by_df[df_name] += get_rescale_cols_num(df=current_df,
                                                        rescale_prefixes=rescale_prefixes)

    # returning cols num by df
    return cols_num_by_df


def get_age_bin_index(embryo_age: float,
                      age_bin: int,
                      first_bin_end: int
                      ) -> int:
    """
    Given an embryo age, an age bin width
    and the age at which the first bin ends,
    returns the 0-based age bin index (ages
    equal to a bin's end belong to that bin;
    younger ages belong to the first bin).

    Args:
        embryo_age (float): The embryo age.
        age_bin (int): The age bin width.
        first_bin_end (int): The age at which the first age bin ends.

    Returns:
        int: The 0-based age bin index.
    """
    # getting age beyond first bin end
    excess_age = (int(embryo_age) - first_bin_end)

    # checking if age is within first bin
    if excess_age <= 0:

        # returning first bin index
        return 0

    # getting bin index (ceil division)
    bin_index = ((excess_age + age_bin - 1) // age_bin)

    # returning bin index
    return bin_index


def get_embryo_age_bins_dict(embryos_df: DataFrame,
                             min_age: int,
                             max_age: int,
                             age_bin: int
                             ) -> dict:
    """
    Given embryos summary df (already
    containing an "embryo_age" col), returns
    a dict mapping each embryo uid to its
    0-based age bin index.
    The first bin spans min age to min age
    + age bin - 1 (e.g. min age 20 -> bin 0
    is 20-69, bin 1 is 70-119); younger
    embryos are put in it. Embryos older
    than max age get a single extra bin,
    i.e. the one after the bin that
    contains max age.

    Args:
        embryos_df (DataFrame): The embryos summary df.
        min_age (int): The embryo age at which the first age bin starts.
        max_age (int): The embryo age at which the last age bin ends.
        age_bin (int): The age bin width.

    Returns:
        dict: A dictionary mapping each embryo uid to its age bin index.
    """
    # getting age at which the first bin ends
    first_bin_end = (min_age + age_bin - 1)

    # getting max age bin index
    max_bin_index = get_age_bin_index(embryo_age=max_age,
                                      age_bin=age_bin,
                                      first_bin_end=first_bin_end)

    # getting embryo ages dict
    embryo_ages_dict = get_df_values_dict(df=embryos_df,
                                          key_col='uid',
                                          value_col='embryo_age')

    # defining embryo age bins dict placeholder
    embryo_age_bins_dict = {}

    # getting dict items
    dict_items = embryo_ages_dict.items()

    # iterating over dict items
    for embryo_item in dict_items:

        # getting current embryo uid/age
        embryo_uid, embryo_age = embryo_item

        # getting current age bin index
        age_bin_index = get_age_bin_index(embryo_age=embryo_age,
                                          age_bin=age_bin,
                                          first_bin_end=first_bin_end)

        # checking if embryo is older than max age
        if embryo_age > max_age:

            # getting overflow bin index (the one after the bin that contains max age)
            age_bin_index = (max_bin_index + 1)

        # assembling current dict
        current_dict = {embryo_uid: age_bin_index}

        # updating embryo age bins dict
        embryo_age_bins_dict.update(current_dict)

    # returning embryo age bins dict
    return embryo_age_bins_dict


def get_embryo_age_bin(row_data: Series,
                       embryo_age_bins_dict: dict
                       ) -> int | None:
    """
    Given an embryos df row, returns the
    age bin index of the embryo.

    Args:
        row_data (Series): The embryos df row to extract from.
        embryo_age_bins_dict (dict): A dictionary mapping each embryo uid to its age bin index.

    Returns:
        int | None: The age bin index, or None if embryo is not in dict.
    """
    # getting current row info
    embryo_uid = row_data['uid']

    # getting current age bin index
    age_bin_index = embryo_age_bins_dict.get(embryo_uid)

    # returning age bin index
    return age_bin_index


def get_embryo_uid_age_bin(row_data: Series,
                           embryo_age_bins_dict: dict
                           ) -> int | None:
    """
    Given a nuclei/dots/cytoplasm df row,
    returns the age bin index of the row's
    embryo.

    Args:
        row_data (Series): The nuclei/dots/cytoplasm df row to extract from.
        embryo_age_bins_dict (dict): A dictionary mapping each embryo uid to its age bin index.

    Returns:
        int | None: The age bin index, or None if embryo is not in dict.
    """
    # getting current row info
    embryo_uid = row_data['embryo_uid']

    # getting current age bin index
    age_bin_index = embryo_age_bins_dict.get(embryo_uid)

    # returning age bin index
    return age_bin_index


def add_volume_normalized_cols(nuclei_df: DataFrame,
                               progress_tracker: ModuleProgressTracker
                               ) -> None:
    """
    Given nuclei summary df, adds its
    volume normalized cols (see
    get_volume_normalized_cols_to_add).

    Args:
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting normalized cols (nuclei)
    normalized_cols = get_volume_normalized_cols_to_add(df=nuclei_df,
                                                        df_name='nuclei')

    # adding normalized cols (nuclei)
    add_cols(col_dicts=normalized_cols,
             progress_tracker=progress_tracker)


def add_distance_normalized_cols(nuclei_df: DataFrame,
                                 border_description: str,
                                 progress_tracker: ModuleProgressTracker
                                 ) -> None:
    """
    Given nuclei summary df, adds its
    border distance normalized cols (see
    get_distance_normalized_cols_to_add).

    Args:
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        border_description (str): The borders masks description the dots distances were computed to.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting normalized cols (nuclei)
    normalized_cols = get_distance_normalized_cols_to_add(df=nuclei_df,
                                                          df_name='nuclei',
                                                          border_description=border_description)

    # adding normalized cols (nuclei)
    add_cols(col_dicts=normalized_cols,
             progress_tracker=progress_tracker)


def get_rescale_dicts(embryos_df: DataFrame,
                      prefix: str
                      ) -> dict:
    """
    Given embryos summary df (already
    containing an "embryo_age_bin" col) and a
    marker prefix, returns a dict with:
    - "ref_lo" / "ref_hi": dicts mapping each
      age bin index to the median, over the
      embryos in the bin, of their
      REF_LO_STAT / REF_HI_STAT intensity;
    - "embryo_lo" / "embryo_hi": dicts mapping
      each embryo uid to its own REF_LO_STAT /
      REF_HI_STAT intensity.

    Args:
        embryos_df (DataFrame): The embryos summary df.
        prefix (str): The marker prefix.

    Returns:
        dict: A dictionary with the "ref_lo", "ref_hi", "embryo_lo" and "embryo_hi" dicts.
    """
    # getting current lo/hi intensity cols
    lo_col = f'{prefix}_{REF_LO_STAT}_intensity'
    hi_col = f'{prefix}_{REF_HI_STAT}_intensity'

    # getting current age bin medians (over embryos) dicts
    ref_lo_dict = get_grouped_agg_dict(df=embryos_df,
                                       group_col='embryo_age_bin',
                                       agg='median',
                                       value_col=lo_col)
    ref_hi_dict = get_grouped_agg_dict(df=embryos_df,
                                       group_col='embryo_age_bin',
                                       agg='median',
                                       value_col=hi_col)

    # getting current embryo lo/hi dicts
    embryo_lo_dict = get_df_values_dict(df=embryos_df,
                                        key_col='uid',
                                        value_col=lo_col)
    embryo_hi_dict = get_df_values_dict(df=embryos_df,
                                        key_col='uid',
                                        value_col=hi_col)

    # assembling rescale dicts
    rescale_dicts = {'ref_lo': ref_lo_dict,
                     'ref_hi': ref_hi_dict,
                     'embryo_lo': embryo_lo_dict,
                     'embryo_hi': embryo_hi_dict}

    # returning rescale dicts
    return rescale_dicts


def get_rescale_dicts_by_prefix(embryos_df: DataFrame,
                                rescale_prefixes: list
                                ) -> dict:
    """
    Given embryos summary df (already
    containing an "embryo_age_bin" col) and the
    marker prefixes to rescale, returns a dict
    mapping each prefix to its rescale dicts
    (see get_rescale_dicts). These are
    computed once and shared by all dfs.

    Args:
        embryos_df (DataFrame): The embryos summary df.
        rescale_prefixes (list): The marker prefixes to rescale.

    Returns:
        dict: A dictionary mapping each marker prefix to its rescale dicts.
    """
    # defining rescale dicts by prefix placeholder
    rescale_dicts_by_prefix = {}

    # iterating over markers
    for prefix in rescale_prefixes:

        # getting current rescale dicts
        rescale_dicts = get_rescale_dicts(embryos_df=embryos_df,
                                          prefix=prefix)

        # assembling current dict
        current_dict = {prefix: rescale_dicts}

        # updating rescale dicts by prefix
        rescale_dicts_by_prefix.update(current_dict)

    # returning rescale dicts by prefix
    return rescale_dicts_by_prefix


def get_age_bin_ref_value(row_data: Series,
                          age_bin_refs_dict: dict
                          ) -> float | None:
    """
    Given a df row (already containing an
    "embryo_age_bin" col), returns the
    reference value (ref_lo or ref_hi,
    depending on dict) of the row's age bin.

    Args:
        row_data (Series): The df row to extract from.
        age_bin_refs_dict (dict): A dictionary mapping each age bin index to its reference value.

    Returns:
        float | None: The age bin reference value, or None if age bin is not in dict.
    """
    # getting current row info
    age_bin_index = row_data['embryo_age_bin']

    # getting current reference value
    ref_value = age_bin_refs_dict.get(age_bin_index)

    # returning reference value
    return ref_value


def get_embryo_value(row_data: Series,
                     embryo_values_dict: dict
                     ) -> float | None:
    """
    Given an embryos df row, returns the
    value (from given dict) of the embryo.

    Args:
        row_data (Series): The embryos df row to extract from.
        embryo_values_dict (dict): A dictionary mapping each embryo uid to its value.

    Returns:
        float | None: The embryo value, or None if embryo is not in dict.
    """
    # getting current row info
    embryo_uid = row_data['uid']

    # getting current embryo value
    embryo_value = embryo_values_dict.get(embryo_uid)

    # returning embryo value
    return embryo_value


def get_embryo_uid_value(row_data: Series,
                         embryo_values_dict: dict
                         ) -> float | None:
    """
    Given a nuclei/dots/cytoplasm df row,
    returns the value (from given dict) of
    the row's embryo.

    Args:
        row_data (Series): The nuclei/dots/cytoplasm df row to extract from.
        embryo_values_dict (dict): A dictionary mapping each embryo uid to its value.

    Returns:
        float | None: The embryo value, or None if embryo is not in dict.
    """
    # getting current row info
    embryo_uid = row_data['embryo_uid']

    # getting current embryo value
    embryo_value = embryo_values_dict.get(embryo_uid)

    # returning embryo value
    return embryo_value


def get_rescale_ref_cols(df: DataFrame,
                         df_name: str,
                         rescale_prefixes: list,
                         rescale_dicts_by_prefix: dict
                         ) -> list:
    """
    Given a summary df (already containing an
    "embryo_age_bin" col), its name, the marker
    prefixes to rescale in it and the rescale
    dicts by prefix, returns the add_col-style
    col dicts that add, for each marker:
    - "<prefix>_ref_lo" and "<prefix>_ref_hi"
      cols, i.e. the reference values of the
      row's age bin;
    - "<prefix>_embryo_lo" and
      "<prefix>_embryo_hi" cols, i.e. the
      values of the row's embryo (found by
      embryo uid: "uid" in the embryos df,
      "embryo_uid" in the other dfs).

    Args:
        df (DataFrame): The summary df.
        df_name (str): The df's name (as shown in the progress string).
        rescale_prefixes (list): The marker prefixes to rescale in df.
        rescale_dicts_by_prefix (dict): A dictionary mapping each marker prefix to its rescale dicts.

    Returns:
        list: The ref / embryo lo/hi cols to add.
    """
    # getting df is embryos df bool
    df_is_embryos = (df_name == 'embryos')

    # getting embryo value function (embryos df is linked by "uid", the other dfs by "embryo_uid")
    embryo_value_func = (get_embryo_value if df_is_embryos else get_embryo_uid_value)

    # defining ref cols placeholder
    ref_cols = []

    # iterating over markers
    for prefix in rescale_prefixes:

        # getting current rescale dicts
        rescale_dicts = rescale_dicts_by_prefix[prefix]

        # assembling current col dicts
        current_cols = [

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_ref_lo',
             'func': get_age_bin_ref_value,
             'func_kwargs': {'age_bin_refs_dict': rescale_dicts['ref_lo']}},

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_ref_hi',
             'func': get_age_bin_ref_value,
             'func_kwargs': {'age_bin_refs_dict': rescale_dicts['ref_hi']}},

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_embryo_lo',
             'func': embryo_value_func,
             'func_kwargs': {'embryo_values_dict': rescale_dicts['embryo_lo']}},

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_embryo_hi',
             'func': embryo_value_func,
             'func_kwargs': {'embryo_values_dict': rescale_dicts['embryo_hi']}}

        ]

        # appending current cols to ref cols
        ref_cols.extend(current_cols)

    # returning ref cols
    return ref_cols


def get_embryo_gain(row_data: Series,
                    embryo_lo_col: str,
                    embryo_hi_col: str,
                    ref_lo_col: str,
                    ref_hi_col: str
                    ) -> float | None:
    """
    Given a df row, returns the gain of the
    row's embryo affine map, i.e.
    (ref_hi - ref_lo) / (embryo_hi - embryo_lo).
    Returns None if any value is missing, or
    if the embryo range or the reference
    range is not positive (flat embryo).

    Args:
        row_data (Series): The df row to extract from.
        embryo_lo_col (str): The col containing the embryo's q01.
        embryo_hi_col (str): The col containing the embryo's q95.
        ref_lo_col (str): The col containing the age bin ref_lo value.
        ref_hi_col (str): The col containing the age bin ref_hi value.

    Returns:
        float | None: The embryo gain, or None if it can't be defined.
    """
    # getting current row info
    embryo_lo = row_data[embryo_lo_col]
    embryo_hi = row_data[embryo_hi_col]
    ref_lo = row_data[ref_lo_col]
    ref_hi = row_data[ref_hi_col]

    # checking if any value is missing
    if isna(embryo_lo) or isna(embryo_hi) or isna(ref_lo) or isna(ref_hi):

        # returning None
        return None

    # getting embryo/reference ranges
    embryo_range = (embryo_hi - embryo_lo)
    ref_range = (ref_hi - ref_lo)

    # checking if any range is not positive
    if (embryo_range <= 0) or (ref_range <= 0):

        # returning None
        return None

    # getting embryo gain
    embryo_gain = (ref_range / embryo_range)

    # returning embryo gain
    return embryo_gain


def get_embryo_offset(row_data: Series,
                      embryo_lo_col: str,
                      gain_col: str,
                      ref_lo_col: str
                      ) -> float | None:
    """
    Given a df row, returns the offset of
    the row's embryo affine map, i.e.
    ref_lo - embryo_lo * gain (so
    embryo_lo maps to ref_lo). Returns None
    if gain is missing.

    Args:
        row_data (Series): The df row to extract from.
        embryo_lo_col (str): The col containing the embryo's q01.
        gain_col (str): The col containing the embryo gain.
        ref_lo_col (str): The col containing the age bin ref_lo value.

    Returns:
        float | None: The embryo offset, or None if it can't be defined.
    """
    # getting current row info
    embryo_lo = row_data[embryo_lo_col]
    gain = row_data[gain_col]
    ref_lo = row_data[ref_lo_col]

    # checking if any value is missing
    if isna(embryo_lo) or isna(gain) or isna(ref_lo):

        # returning None
        return None

    # getting embryo offset
    embryo_offset = (ref_lo - (embryo_lo * gain))

    # returning embryo offset
    return embryo_offset


def get_gain_flag(row_data: Series,
                  gain_col: str
                  ) -> bool:
    """
    Given a df row, returns whether its
    embryo gain is flagged, i.e. missing
    or outside GAIN_FLAG_MIN-GAIN_FLAG_MAX.

    Args:
        row_data (Series): The df row to extract from.
        gain_col (str): The col containing the embryo gain.

    Returns:
        bool: True if gain is missing or out of range.
    """
    # getting current row info
    gain = row_data[gain_col]

    # getting gain is flagged bool
    gain_is_flagged = (isna(gain) or (gain < GAIN_FLAG_MIN) or (gain > GAIN_FLAG_MAX))

    # returning gain is flagged bool
    return bool(gain_is_flagged)


def get_rescale_affine_cols(df: DataFrame,
                            df_name: str,
                            rescale_prefixes: list
                            ) -> list:
    """
    Given a summary df (already containing the
    ref / embryo lo/hi cols), its name and the
    marker prefixes to rescale in it, returns
    the add_col-style col dicts that add, for
    each marker, the per embryo affine map that
    sends embryo_lo to ref_lo and embryo_hi to
    ref_hi:
    - "<prefix>_gain", i.e. (ref_hi - ref_lo) /
      (embryo_hi - embryo_lo);
    - "<prefix>_offset", i.e. ref_lo -
      embryo_lo * gain;
    - "<prefix>_gain_flag" (gain missing or
      outside GAIN_FLAG_MIN-GAIN_FLAG_MAX; gain
      is flagged, not clamped).

    Args:
        df (DataFrame): The summary df.
        df_name (str): The df's name (as shown in the progress string).
        rescale_prefixes (list): The marker prefixes to rescale in df.

    Returns:
        list: The gain / offset / gain flag cols to add.
    """
    # defining affine cols placeholder
    affine_cols = []

    # iterating over markers
    for prefix in rescale_prefixes:

        # assembling current col dicts (executed in order, so later cols can use earlier ones)
        current_cols = [

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_gain',
             'func': get_embryo_gain,
             'func_kwargs': {'embryo_lo_col': f'{prefix}_embryo_lo',
                             'embryo_hi_col': f'{prefix}_embryo_hi',
                             'ref_lo_col': f'{prefix}_ref_lo',
                             'ref_hi_col': f'{prefix}_ref_hi'}},

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_offset',
             'func': get_embryo_offset,
             'func_kwargs': {'embryo_lo_col': f'{prefix}_embryo_lo',
                             'gain_col': f'{prefix}_gain',
                             'ref_lo_col': f'{prefix}_ref_lo'}},

            {'df': df,
             'df_name': df_name,
             'col_name': f'{prefix}_gain_flag',
             'func': get_gain_flag,
             'func_kwargs': {'gain_col': f'{prefix}_gain'}}

        ]

        # appending current cols to affine cols
        affine_cols.extend(current_cols)

    # returning affine cols
    return affine_cols


def get_affine_value(row_data: Series,
                     value_col: str,
                     gain_col: str,
                     offset_col: str
                     ) -> float | None:
    """
    Given a df row, returns its value mapped
    by its embryo's affine map, i.e.
    gain * value + offset. Returns None if
    gain or offset is missing.

    Args:
        row_data (Series): The df row to extract from.
        value_col (str): The col containing the value to rescale.
        gain_col (str): The col containing the embryo gain.
        offset_col (str): The col containing the embryo offset.

    Returns:
        float | None: The rescaled value, or None if rescaling fails.
    """
    # getting current row info
    current_value = row_data[value_col]
    gain = row_data[gain_col]
    offset = row_data[offset_col]

    # checking if gain or offset is missing
    if isna(gain) or isna(offset):

        # returning None
        return None

    # getting rescaled value
    rescaled_value = ((gain * current_value) + offset)

    # returning rescaled value
    return rescaled_value


def get_rescaled_cols(df: DataFrame,
                      df_name: str,
                      rescale_prefixes: list
                      ) -> list:
    """
    Given a summary df (already containing the
    gain / offset cols), its name and the marker
    prefixes to rescale in it, returns the
    add_col-style col dicts that add, for each
    intensity col of those markers, a
    "<col>_rescaled" col, i.e. gain * col +
    offset. The same map is applied to every
    row of an embryo, so the variability
    between its rows is kept, while embryos
    within a same age bin become comparable.

    Args:
        df (DataFrame): The summary df.
        df_name (str): The df's name (as shown in the progress string).
        rescale_prefixes (list): The marker prefixes to rescale in df.

    Returns:
        list: The rescaled cols to add.
    """
    # getting intensity cols dict
    intensity_cols_dict = get_intensity_cols_dict(df=df)

    # defining rescaled cols placeholder
    rescaled_cols = []

    # iterating over markers
    for prefix in rescale_prefixes:

        # iterating over current marker intensity cols
        for intensity_col in intensity_cols_dict[prefix]:

            # assembling current dict
            current_dict = {'df': df,
                            'df_name': df_name,
                            'col_name': f'{intensity_col}_rescaled',
                            'func': get_affine_value,
                            'func_kwargs': {'value_col': intensity_col,
                                            'gain_col': f'{prefix}_gain',
                                            'offset_col': f'{prefix}_offset'}}

            # appending current dict to rescaled cols
            rescaled_cols.append(current_dict)

    # returning rescaled cols
    return rescaled_cols


def get_dfs_by_name(embryos_df: DataFrame,
                    nuclei_df: DataFrame,
                    dots_df: DataFrame,
                    cytoplasm_df: DataFrame
                    ) -> dict:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs, returns a dict mapping
    each df name to its df (in the order
    cols are added).

    Args:
        embryos_df (DataFrame): The embryos summary df.
        nuclei_df (DataFrame): The nuclei summary df.
        dots_df (DataFrame): The dots summary df (empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (empty if not given).

    Returns:
        dict: A dictionary mapping each of "embryos"/"nuclei"/"dots"/"cytoplasm" to its df.
    """
    # assembling df name to df dict
    dfs_by_name = {'embryos': embryos_df,
                   'nuclei': nuclei_df,
                   'dots': dots_df,
                   'cytoplasm': cytoplasm_df}

    # returning df name to df dict
    return dfs_by_name


def add_age_bin_cols(embryos_df: DataFrame,
                     nuclei_df: DataFrame,
                     dots_df: DataFrame,
                     cytoplasm_df: DataFrame,
                     embryo_age_bins_dict: dict,
                     progress_tracker: ModuleProgressTracker
                     ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs and an embryo age bins
    dict, adds the "embryo_age_bin" col
    to embryos and nuclei, and to
    dots/cytoplasm if not empty.

    Args:
        embryos_df (DataFrame): The embryos summary df (modified in-place).
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        dots_df (DataFrame): The dots summary df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (modified in-place; empty if not given).
        embryo_age_bins_dict (dict): A dictionary mapping each embryo uid to its age bin index.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting dots/cytoplasm dfs not empty bools
    dots_df_not_empty = (not dots_df.empty)
    cytoplasm_df_not_empty = (not cytoplasm_df.empty)

    # defining age bin cols (embryos + nuclei)
    age_bin_cols = [

        {'df': embryos_df,
         'df_name': 'embryos',
         'col_name': 'embryo_age_bin',
         'func': get_embryo_age_bin,
         'func_kwargs': {'embryo_age_bins_dict': embryo_age_bins_dict}},

        {'df': nuclei_df,
         'df_name': 'nuclei',
         'col_name': 'embryo_age_bin',
         'func': get_embryo_uid_age_bin,
         'func_kwargs': {'embryo_age_bins_dict': embryo_age_bins_dict}}

    ]

    # checking if dots df is not empty
    if dots_df_not_empty:

        # defining dots age bin cols
        dots_age_bin_cols = [

            {'df': dots_df,
             'df_name': 'dots',
             'col_name': 'embryo_age_bin',
             'func': get_embryo_uid_age_bin,
             'func_kwargs': {'embryo_age_bins_dict': embryo_age_bins_dict}}

        ]

        # appending dots age bin cols
        age_bin_cols.extend(dots_age_bin_cols)

    # checking if cytoplasm df is not empty
    if cytoplasm_df_not_empty:

        # defining cytoplasm age bin cols
        cytoplasm_age_bin_cols = [

            {'df': cytoplasm_df,
             'df_name': 'cytoplasm',
             'col_name': 'embryo_age_bin',
             'func': get_embryo_uid_age_bin,
             'func_kwargs': {'embryo_age_bins_dict': embryo_age_bins_dict}}

        ]

        # appending cytoplasm age bin cols
        age_bin_cols.extend(cytoplasm_age_bin_cols)

    # adding embryo age bin cols (embryos + nuclei + dots + cytoplasm)
    add_cols(col_dicts=age_bin_cols,
             progress_tracker=progress_tracker)


def add_rescale_ref_cols(embryos_df: DataFrame,
                         nuclei_df: DataFrame,
                         dots_df: DataFrame,
                         cytoplasm_df: DataFrame,
                         rescale_prefixes: list,
                         rescale_dicts_by_prefix: dict,
                         progress_tracker: ModuleProgressTracker
                         ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs (already containing an
    "embryo_age_bin" col), the marker
    prefixes to rescale and their rescale
    dicts, adds the ref / embryo lo/hi
    cols to every df (see
    get_rescale_ref_cols).

    Args:
        embryos_df (DataFrame): The embryos summary df (modified in-place).
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        dots_df (DataFrame): The dots summary df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (modified in-place; empty if not given).
        rescale_prefixes (list): The marker prefixes that can be rescaled.
        rescale_dicts_by_prefix (dict): A dictionary mapping each marker prefix to its rescale dicts.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting df name to df dict
    dfs_by_name = get_dfs_by_name(embryos_df=embryos_df,
                                  nuclei_df=nuclei_df,
                                  dots_df=dots_df,
                                  cytoplasm_df=cytoplasm_df)

    # defining ref cols placeholder
    ref_cols = []

    # getting dict items
    dict_items = dfs_by_name.items()

    # iterating over dict items
    for df_item in dict_items:

        # getting current df name/df
        df_name, current_df = df_item

        # getting current df's rescale prefixes (an empty placeholder df has none)
        df_rescale_prefixes = get_df_rescale_prefixes(df=current_df,
                                                      rescale_prefixes=rescale_prefixes)

        # getting current df's ref / embryo lo/hi cols
        current_ref_cols = get_rescale_ref_cols(df=current_df,
                                                df_name=df_name,
                                                rescale_prefixes=df_rescale_prefixes,
                                                rescale_dicts_by_prefix=rescale_dicts_by_prefix)

        # appending current df's cols
        ref_cols.extend(current_ref_cols)

    # adding ref / embryo lo/hi cols (embryos + nuclei + dots + cytoplasm)
    add_cols(col_dicts=ref_cols,
             progress_tracker=progress_tracker)


def add_rescale_affine_cols(embryos_df: DataFrame,
                            nuclei_df: DataFrame,
                            dots_df: DataFrame,
                            cytoplasm_df: DataFrame,
                            rescale_prefixes: list,
                            progress_tracker: ModuleProgressTracker
                            ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs (already containing the ref /
    embryo lo/hi cols) and the marker prefixes
    to rescale, adds the gain / offset / gain
    flag cols to every df (see
    get_rescale_affine_cols).

    Args:
        embryos_df (DataFrame): The embryos summary df (modified in-place).
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        dots_df (DataFrame): The dots summary df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (modified in-place; empty if not given).
        rescale_prefixes (list): The marker prefixes that can be rescaled.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting df name to df dict
    dfs_by_name = get_dfs_by_name(embryos_df=embryos_df,
                                  nuclei_df=nuclei_df,
                                  dots_df=dots_df,
                                  cytoplasm_df=cytoplasm_df)

    # defining affine cols placeholder
    affine_cols = []

    # getting dict items
    dict_items = dfs_by_name.items()

    # iterating over dict items
    for df_item in dict_items:

        # getting current df name/df
        df_name, current_df = df_item

        # getting current df's rescale prefixes (an empty placeholder df has none)
        df_rescale_prefixes = get_df_rescale_prefixes(df=current_df,
                                                      rescale_prefixes=rescale_prefixes)

        # getting current df's gain / offset / gain flag cols
        current_affine_cols = get_rescale_affine_cols(df=current_df,
                                                      df_name=df_name,
                                                      rescale_prefixes=df_rescale_prefixes)

        # appending current df's cols
        affine_cols.extend(current_affine_cols)

    # adding gain / offset / gain flag cols (embryos + nuclei + dots + cytoplasm)
    add_cols(col_dicts=affine_cols,
             progress_tracker=progress_tracker)


def add_rescaled_cols(embryos_df: DataFrame,
                      nuclei_df: DataFrame,
                      dots_df: DataFrame,
                      cytoplasm_df: DataFrame,
                      rescale_prefixes: list,
                      progress_tracker: ModuleProgressTracker
                      ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs (already containing the
    gain / offset cols) and the marker
    prefixes to rescale, adds the rescaled
    intensity cols to every df (see
    get_rescaled_cols).

    Args:
        embryos_df (DataFrame): The embryos summary df (modified in-place).
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        dots_df (DataFrame): The dots summary df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (modified in-place; empty if not given).
        rescale_prefixes (list): The marker prefixes that can be rescaled.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting df name to df dict
    dfs_by_name = get_dfs_by_name(embryos_df=embryos_df,
                                  nuclei_df=nuclei_df,
                                  dots_df=dots_df,
                                  cytoplasm_df=cytoplasm_df)

    # defining rescaled cols placeholder
    rescaled_cols = []

    # getting dict items
    dict_items = dfs_by_name.items()

    # iterating over dict items
    for df_item in dict_items:

        # getting current df name/df
        df_name, current_df = df_item

        # getting current df's rescale prefixes (an empty placeholder df has none)
        df_rescale_prefixes = get_df_rescale_prefixes(df=current_df,
                                                      rescale_prefixes=rescale_prefixes)

        # getting current df's rescaled cols
        current_rescaled_cols = get_rescaled_cols(df=current_df,
                                                  df_name=df_name,
                                                  rescale_prefixes=df_rescale_prefixes)

        # appending current df's cols
        rescaled_cols.extend(current_rescaled_cols)

    # adding rescaled cols (embryos + nuclei + dots + cytoplasm)
    add_cols(col_dicts=rescaled_cols,
             progress_tracker=progress_tracker)


def add_rescale_cols(embryos_df: DataFrame,
                     nuclei_df: DataFrame,
                     dots_df: DataFrame,
                     cytoplasm_df: DataFrame,
                     progress_tracker: ModuleProgressTracker
                     ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs (already containing an
    "embryo_age_bin" col), adds the age bin
    rescaling cols, in dependency order (ref /
    embryo lo/hi, gain / offset / gain flag,
    rescaled intensities). Ref and embryo
    lo/hi values are computed once, from the
    embryos df, and shared by all dfs.

    Args:
        embryos_df (DataFrame): The embryos summary df (modified in-place).
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        dots_df (DataFrame): The dots summary df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (modified in-place; empty if not given).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting rescale prefixes (from embryos df)
    rescale_prefixes = get_rescale_prefixes(df=embryos_df)

    # getting rescale dicts by prefix (shared between all dfs add_col calls)
    rescale_dicts_by_prefix = get_rescale_dicts_by_prefix(embryos_df=embryos_df,
                                                          rescale_prefixes=rescale_prefixes)

    # adding ref / embryo lo/hi cols (embryos + nuclei + dots + cytoplasm)
    add_rescale_ref_cols(embryos_df=embryos_df,
                         nuclei_df=nuclei_df,
                         dots_df=dots_df,
                         cytoplasm_df=cytoplasm_df,
                         rescale_prefixes=rescale_prefixes,
                         rescale_dicts_by_prefix=rescale_dicts_by_prefix,
                         progress_tracker=progress_tracker)

    # adding gain / offset / gain flag cols (embryos + nuclei + dots + cytoplasm)
    add_rescale_affine_cols(embryos_df=embryos_df,
                            nuclei_df=nuclei_df,
                            dots_df=dots_df,
                            cytoplasm_df=cytoplasm_df,
                            rescale_prefixes=rescale_prefixes,
                            progress_tracker=progress_tracker)

    # adding rescaled cols (embryos + nuclei + dots + cytoplasm)
    add_rescaled_cols(embryos_df=embryos_df,
                      nuclei_df=nuclei_df,
                      dots_df=dots_df,
                      cytoplasm_df=cytoplasm_df,
                      rescale_prefixes=rescale_prefixes,
                      progress_tracker=progress_tracker)


def add_normalized_cols(embryos_df: DataFrame,
                        nuclei_df: DataFrame,
                        dots_df: DataFrame,
                        cytoplasm_df: DataFrame,
                        min_age: int,
                        max_age: int,
                        age_bin: int,
                        border_description: str,
                        progress_tracker: ModuleProgressTracker
                        ) -> None:
    """
    Given embryos/nuclei/dots/cytoplasm
    summary dfs, adds normalized columns
    (embryo age bin, embryo age bin rescaled
    intensities, and nuclei volume and border
    distance normalized), in dependency order
    (each column group is added by its own
    function). All dfs (dots and cytoplasm
    only if given) get the age bin col, the
    ref / embryo lo/hi cols, the gain /
    offset / gain flag cols and the rescaled
    intensity cols.

    Args:
        embryos_df (DataFrame): The embryos summary df (modified in-place).
        nuclei_df (DataFrame): The nuclei summary df (modified in-place).
        dots_df (DataFrame): The dots summary df (modified in-place; empty if not given).
        cytoplasm_df (DataFrame): The cytoplasm summary df (modified in-place; empty if not given).
        min_age (int): The embryo age at which the first age bin starts.
        max_age (int): The embryo age at which the last age bin ends.
        age_bin (int): The embryo age bin width.
        border_description (str): The borders masks description the dots distances were computed to.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting embryo age bins dict (shared between all dfs add_col calls)
    embryo_age_bins_dict = get_embryo_age_bins_dict(embryos_df=embryos_df,
                                                    min_age=min_age,
                                                    max_age=max_age,
                                                    age_bin=age_bin)

    # adding embryo age bin cols (embryos + nuclei + dots + cytoplasm)
    add_age_bin_cols(embryos_df=embryos_df,
                     nuclei_df=nuclei_df,
                     dots_df=dots_df,
                     cytoplasm_df=cytoplasm_df,
                     embryo_age_bins_dict=embryo_age_bins_dict,
                     progress_tracker=progress_tracker)

    # adding volume normalized cols (nuclei)
    add_volume_normalized_cols(nuclei_df=nuclei_df,
                               progress_tracker=progress_tracker)

    # adding border distance normalized cols (nuclei)
    add_distance_normalized_cols(nuclei_df=nuclei_df,
                                 border_description=border_description,
                                 progress_tracker=progress_tracker)

    # adding age bin rescaling cols (embryos + nuclei + dots + cytoplasm)
    add_rescale_cols(embryos_df=embryos_df,
                     nuclei_df=nuclei_df,
                     dots_df=dots_df,
                     cytoplasm_df=cytoplasm_df,
                     progress_tracker=progress_tracker)


def normalize_summary_dfs(embryos_df_path: str,
                          nuclei_df_path: str,
                          dots_df_path: str,
                          cytoplasm_df_path: str,
                          min_age: int,
                          max_age: int,
                          age_bin: int,
                          border_description: str,
                          output_folder: str,
                          overwrite_output: bool,
                          progress_tracker: ModuleProgressTracker
                          ) -> None:
    """
    Given the embryos/nuclei summary dfs
    (and, optionally, the dots/cytoplasm
    summary dfs), adds normalized cols to
    every df (embryo age bin and embryo age
    bin rescaled intensities; nuclei also get
    volume and border distance normalized cols)
    and saves all dfs to given folder, each
    with a "_normalized" suffix before
    ".csv" (so they can share a folder with
    the non-normalized summary dfs).

    Args:
        embryos_df_path (str): The path to the embryos summary df.
        nuclei_df_path (str): The path to the nuclei summary df.
        dots_df_path (str): The path to the dots summary df, or None to skip dots.
        cytoplasm_df_path (str): The path to the cytoplasm summary df, or None to skip cytoplasm.
        min_age (int): The embryo age at which the first age bin starts.
        max_age (int): The embryo age at which the last age bin ends.
        age_bin (int): The embryo age bin width.
        border_description (str): The borders masks description the dots distances were computed to.
        output_folder (str): The path to the folder to save the normalized summary dfs to.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # defining save names/paths
    embryos_save_name = 'embryos_summary_df_normalized.csv'
    embryos_save_path = join(output_folder,
                             embryos_save_name)
    nuclei_save_name = 'nuclei_summary_df_normalized.csv'
    nuclei_save_path = join(output_folder,
                            nuclei_save_name)
    dots_save_name = 'dots_summary_df_normalized.csv'
    dots_save_path = join(output_folder,
                          dots_save_name)
    cytoplasm_save_name = 'cytoplasm_summary_df_normalized.csv'
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

    # loading embryos/nuclei dfs
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

    # adding normalized cols
    add_normalized_cols(embryos_df=embryos_df,
                        nuclei_df=nuclei_df,
                        dots_df=dots_df,
                        cytoplasm_df=cytoplasm_df,
                        min_age=min_age,
                        max_age=max_age,
                        age_bin=age_bin,
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

    # getting min age
    min_age = args_dict['min_age']

    # getting max age
    max_age = args_dict['max_age']

    # getting age bin
    age_bin = args_dict['age_bin']

    # getting border description
    border_description = args_dict['border_description']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running normalize_summary_dfs function
    normalize_summary_dfs(embryos_df_path=embryos_df_path,
                          nuclei_df_path=nuclei_df_path,
                          dots_df_path=dots_df_path,
                          cytoplasm_df_path=cytoplasm_df_path,
                          min_age=min_age,
                          max_age=max_age,
                          age_bin=age_bin,
                          border_description=border_description,
                          output_folder=output_folder,
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
