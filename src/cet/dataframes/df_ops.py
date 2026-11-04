# df ops module

# Code destined to storing
# shared dataframe operations.

######################################################################
# imports

from pandas import concat
from pandas import Series
from typing import Callable
from pandas import DataFrame
from cet.constants import FOUNDER_CELLS
from cet.progress_tracker.ProgressTracker import ProgressTracker

# pandas warning imports
from warnings import simplefilter
from pandas.errors import PerformanceWarning


def filter_pandas_performance_warnings() -> None:
    """
    Suppresses pandas.errors.PerformanceWarning
    (e.g. DataFrame fragmentation warnings) globally.
    """
    simplefilter(action='ignore', category=PerformanceWarning)


# filtering Pandas Performance Warnings
filter_pandas_performance_warnings()

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
        self.df_name = 'df'

        # col
        self.cols_num = 0
        self.current_col = 0

        # row
        self.rows_num = 0
        self.current_row = 0

######################################################################
# defining auxiliary functions


def get_normalized_value(row_data: Series,
                         value_col: str,
                         reference_col: str
                         ) -> float | None:
    """
    Calculates the normalized value for a given row
    in a dataframe.

    Args:
        row_data (Series): A row from the dataframe.
        value_col (str): The column name containing the value to normalize.
        reference_col (str): The column name containing the reference value to divide by.

    Returns:
        float | None: The normalized value, or None if normalization fails.
    """
    # getting current row info
    current_value = row_data[value_col]
    current_reference = row_data[reference_col]

    # getting current normalized value
    try:
        normalized_value = (current_value / current_reference)
    except TypeError:
        normalized_value = None

    # returning normalized value
    return normalized_value


def get_subtracted_value(row_data: Series,
                         value_col: str,
                         reference_col: str
                         ) -> float | None:
    """
    Calculates the subtracted value (value - subtrahend)
    for a given row in a dataframe.

    Args:
        row_data (Series): A row from the dataframe.
        value_col (str): The column name containing the value to subtract from.
        reference_col (str): The column name containing the reference value to subtract.

    Returns:
        float | None: The subtracted value, or None if subtraction fails.
    """
    # getting current row info
    current_value = row_data[value_col]
    current_reference = row_data[reference_col]

    # getting current subtracted value
    try:
        subtracted_value = (current_value - current_reference)
    except TypeError:
        subtracted_value = None

    # returning subtracted value
    return subtracted_value


def get_normalizer(values: Series) -> float:
    """
    Calculates the normalizer value (mean)
    for a series of values.

    Args:
        values (Series): A pandas Series containing the values to normalize.

    Returns:
        float: The mean of the provided values.
    """
    # getting values normalizer
    normalizer = values.mean()

    # returning normalizer
    return normalizer


def get_grouped_agg_dict(df: DataFrame,
                         group_col: str,
                         agg: str,
                         value_col: str | None = None
                         ) -> dict:
    """
    Groups a dataframe by a column and aggregates values
    into a dictionary.

    Args:
        df (DataFrame): The input dataframe to group.
        group_col (str): The column name to group by.
        agg (str): The aggregation function name. Examples: 'size', 'sum', 'mean', 'count'.
        value_col (str | None): The column to aggregate over. If None, aggregates the entire group.

    Returns:
        dict: A dictionary mapping each group key to its aggregated value.
    """
    # grouping df by given col
    grouped_df = df.groupby(group_col)

    # narrowing grouped df down to value col, if one was given
    group_target = (grouped_df[value_col] if value_col else grouped_df)

    # getting aggregation function
    agg_func = getattr(group_target, agg)

    # assembling grouped agg dict
    grouped_agg_dict = agg_func().to_dict()

    # returning grouped agg dict
    return grouped_agg_dict


def get_embryo_ages_dict(df: DataFrame) -> dict:
    """
    Extracts embryo ages (nuclei count per embryo)
    dict from a dataframe.

    Args:
        df (DataFrame): A dataframe containing an 'embryo_uid' column.

    Returns:
        dict: A dictionary mapping each embryo UID to its age (nuclei count at that timepoint).
    """
    # assembling embryo ages dict (one nuclei count per embryo uid)
    embryo_ages_dict = get_grouped_agg_dict(df=df,
                                            group_col='embryo_uid',
                                            agg='size')

    # returning embryo ages dict
    return embryo_ages_dict


def get_df_values_dict(df: DataFrame,
                       key_col: str,
                       value_col: str
                       ) -> dict:
    """
    Converts dataframe columns into a
    key-value dictionary.

    Args:
        df (DataFrame): The input dataframe.
        key_col (str): The column name to use as dictionary keys.
        value_col (str): The column name to use as dictionary values.

    Returns:
        dict: A dictionary mapping keys to values extracted from the specified columns.
    """
    # getting key/value cols
    key_col_items = df[key_col]
    value_col_items = df[value_col]

    # converting data types
    key_col_items = key_col_items.to_list()
    value_col_items = value_col_items.to_list()

    # getting key/value zip
    key_value_zip = zip(key_col_items, value_col_items)

    # assembling df values dict
    df_values_dict = dict(key_value_zip)

    # returning df values dict
    return df_values_dict


def check_cols_in_df(df: DataFrame,
                     cols: list | str,
                     df_description: str = 'input df',
                     hint: str | None = None
                     ) -> None:
    """
    Given a df and a col name (or a list of
    col names), raises a descriptive error
    listing the missing cols and the df's
    available cols if any of them is missing.

    Args:
        df (DataFrame): The df to check.
        cols (list | str): The required col name(s).
        df_description (str): A short description of the df (used in the error message).
        hint (str | None): An optional extra line to append to the error message.

    Returns:
        None.

    Raises:
        Exception: If any required col is missing from the df.
    """
    # checking if a single col name was given
    if isinstance(cols, str):

        # converting to a list
        cols = [cols]

    # getting missing cols
    missing_cols = [col for col in cols if col not in df.columns]

    # checking if any col is missing
    if missing_cols:

        # getting available cols
        available_cols = sorted(df.columns)

        # defining error message
        e_string = f'Invalid column(s) {missing_cols}: not found in {df_description}.\n'
        e_string += f'Available columns are: {available_cols}\n'

        # checking if a hint was given
        if hint is not None:

            # adding hint to error message
            e_string += f'({hint})\n'

        # completing error message
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)


def add_col(df: DataFrame,
            col_name: str,
            func: Callable,
            func_kwargs: dict | None = None,
            df_name: str | None = None,
            progress_tracker: ModuleProgressTracker | None = None
            ) -> None:
    """
    Adds a new column to a dataframe using a provided function.

    Args:
        df (DataFrame): The dataframe to modify (modified in-place).
        col_name (str): The name of the new column to add.
        func (Callable): A function that takes a row (Series) and returns a value.
        func_kwargs (dict | None): Optional keyword arguments to pass to the function.
        df_name (str | None): Optional name of the dataframe for progress tracking.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        None.
    """
    # defining placeholder value for new col
    new_col = []

    # checking if progress tracker is not none
    if progress_tracker:

        # updating progress tracker attributes
        progress_tracker.df_name = df_name

        # getting rows num
        rows_num = len(df)

        # updating progress tracker attributes
        progress_tracker.rows_num = rows_num

        # resetting progress tracker attributes
        progress_tracker.current_row = 0

    # getting df rows
    df_rows = df.iterrows()

    # iterating over df rows
    for row_index, row_data in df_rows:

        # checking if progress tracker is not none
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_iteration += 1
            progress_tracker.current_row += 1

        # checking if func kwargs is not none
        if func_kwargs:

            # getting current row new col value
            current_value = func(row_data=row_data,
                                 **func_kwargs)

        else:

            # getting current row new col value
            current_value = func(row_data=row_data)

        # appending current value to new col
        new_col.append(current_value)

    # adding col to df
    df[col_name] = new_col


def add_cols(col_dicts: list,
             progress_tracker: ModuleProgressTracker | None = None
             ) -> None:
    """
    Given a list of add_col-style col
    dicts, adds each col to its
    respective df, in order, wiring
    in progress tracker (if any).

    Args:
        col_dicts (list): The list of add_col-style col dicts to apply.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        None.
    """
    # iterating over col dicts
    for col_dict in col_dicts:

        # checking if progress tracker is not none
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_col += 1

            # defining progress tracker dict
            progress_tracker_dict = {'progress_tracker': progress_tracker}

            # adding progress tracker to current col dict
            col_dict.update(progress_tracker_dict)

        # adding current col to respective df
        add_col(**col_dict)


def add_constant_col(df: DataFrame,
                     col_name: str,
                     value: object,
                     df_name: str | None = None,
                     progress_tracker: ModuleProgressTracker | None = None
                     ) -> None:
    """
    Adds a new column to a dataframe with a constant value.

    Args:
        df (DataFrame): The dataframe to modify (modified in-place).
        col_name (str): The name of the new column to add.
        value (object): The constant value to fill the column with.
        df_name (str | None): Optional name of the dataframe for progress tracking.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        None.
    """
    # defining placeholder value for new col
    new_col = []

    # checking if progress tracker is not none
    if progress_tracker:

        # updating progress tracker attributes
        progress_tracker.df_name = df_name

        # getting rows num
        rows_num = len(df)

        # updating progress tracker attributes
        progress_tracker.rows_num = rows_num

        # resetting progress tracker attributes
        progress_tracker.current_row = 0

    # getting df rows
    df_rows = df.iterrows()

    # iterating over df rows
    for _, _ in df_rows:

        # checking if progress tracker is not none
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_iteration += 1
            progress_tracker.current_row += 1

        # appending constant value to new col
        new_col.append(value)

    # adding col to df
    df[col_name] = new_col


def concatenate_dfs(dfs_list: list) -> DataFrame:
    """
    Concatenates a list of dataframes into
    a single dataframe (with a fresh index),
    or returns an empty dataframe if the
    list is empty.

    Args:
        dfs_list (list): The list of dataframes to concatenate.

    Returns:
        DataFrame: The concatenated dataframe (empty if dfs_list is empty).
    """
    # checking if dfs list is not empty
    if dfs_list:

        # concatenating dfs in dfs list
        final_df = concat(dfs_list,
                          ignore_index=True)

    # if dfs list is empty
    else:

        # defining empty df
        final_df = DataFrame()

    # returning final df
    return final_df


def filter_split(images_df: DataFrame,
                 split: str | None
                 ) -> DataFrame:
    """
    Given an images df and a split name,
    returns only the rows of that split
    (or all rows if split is None).

    Args:
        images_df (DataFrame): The images df to filter.
        split (str | None): The split to keep ("train", "val" or "test"), or None to keep all rows.

    Returns:
        DataFrame: The filtered images df.

    Raises:
        Exception: If the df has no "split" column or no rows of the given split.
    """
    # checking if split is none
    if split is None:

        # returning all rows
        return images_df

    # checking if df has split column
    check_cols_in_df(df=images_df,
                     cols='split',
                     df_description='images df',
                     hint=f'cannot filter by split "{split}": please, use a splits df')

    # filtering df by split
    split_df = images_df[images_df['split'] == split]

    # checking if split has no rows
    if len(split_df) == 0:

        # getting available splits
        available_splits = images_df['split'].unique()
        available_splits = list(available_splits)

        # defining error message
        e_string = f'No images found for split "{split}".\n'
        e_string += f'Available splits: {available_splits}\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # returning filtered df
    return split_df


def get_column_name(label: str) -> str:
    """
    Formats a label string to be used
    as a dataframe column name.

    Args:
        label (str): The label string to format.

    Returns:
        str: The formatted column name (lowercase, with spaces replaced by underscores, colons removed).
    """
    # removing ":"
    col_name = label.replace(':', '')

    # replacing spaces by underscores
    col_name = col_name.replace(' ', '_')

    # lowering string
    col_name = col_name.lower()

    # returning col name
    return col_name


def show_example_row(df: DataFrame,
                     show_types: bool = False
                     ) -> None:
    """
    Prints the first row of a dataframe
    as a formatted dictionary.

    Args:
        df (DataFrame): The input dataframe.
        show_types (bool): Whether to include the type of each value in the output (default: False).

    Returns:
        None.
    """
    # getting first row
    first_row = df.iloc[0]

    # converting data types
    first_row_dict = first_row.to_dict()

    # getting dict items
    dict_items = first_row_dict.items()

    # iterating over dict items
    for dict_item in dict_items:

        # getting current dict elements
        col_name, value = dict_item

        # assembling current col string
        f_string = f'{col_name}: {value}'

        # checking whether to show value type
        if show_types:

            # getting current value type
            value_type = type(value)

            # updating current col string
            f_string += f' ({value_type})'

        # printing current col string
        print(f_string)

######################################################################
# end of current module
