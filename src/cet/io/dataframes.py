# dataframes io module

# Code destined to storing dataframe
# input/output related functions.

######################################################################
# imports

from pandas import read_csv
from pandas import DataFrame

######################################################################
# defining auxiliary functions


def load_df(input_path: str,
            dtype: dict | None = None
            ) -> DataFrame:
    """
    Given a path to a dataframe,
    returns loaded df.

    Args:
        input_path (str): Path to the CSV file containing the dataframe to load.
        dtype (dict): Optional dict mapping column name to dtype, forwarded to
            read_csv. Useful to silence DtypeWarning on columns that mix
            strings with empty/NaN values (default: None).

    Returns:
        DataFrame: The loaded pandas DataFrame.
    """
    # reading df
    df = read_csv(filepath_or_buffer=input_path,  # noqa
                  dtype=dtype)

    # returning df
    return df


def save_df(save_path: str,
            df: DataFrame
            ) -> None:
    """
    Given a dataframe, saves it
    to given save path.

    Args:
        save_path (str): Path where the CSV file will be saved.
        df (DataFrame): The pandas DataFrame to save.

    Returns:
        None
    """
    # saving df
    df.to_csv(path_or_buf=save_path,
              index=False)

######################################################################
# end of current module
