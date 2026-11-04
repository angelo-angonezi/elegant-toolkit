# join dfs module

print('initializing...')  # noqa

# Code destined to joining
# multiple dataframes into
# single file.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from pandas.errors import EmptyDataError
from cet.io.files import get_skip_file_bool
from cet.io.files import get_files_in_folder
from cet.dataframes.df_ops import concatenate_dfs
from cet.dataframes.df_ops import add_constant_col
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
    description = "join dfs module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing input files [.csv]')

    # output path param
    parser.add_argument('-o', '--output-path',
                        dest='output_path',
                        type=str,
                        required=True,
                        help='defines path to output file [.csv]')

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

        # file
        self.files_num = 0
        self.current_file = 0

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
            progress_string += f' | files: {self.files_num}'
            progress_string += f' | rows: {self.rows_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'joining dfs...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | file: {self.current_file}/{self.files_num}'
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
        # getting input folder
        input_folder = args_dict['input_folder']

        # getting files in input folder
        files = get_files_in_folder(input_folder=input_folder,
                                    extension='.csv')

        # iterating over files
        for file_name in files:

            # updating progress tracker attributes
            self.files_num += 1

            # getting current file path
            current_path = join(input_folder,
                                file_name)

            # trying to load current df
            try:

                # loading current df
                current_df = load_df(input_path=current_path)

            except EmptyDataError:
                current_df = DataFrame()

            # getting df rows num/range
            df_rows_num = len(current_df)
            df_rows_range = range(df_rows_num)

            # iterating over df rows
            for _ in df_rows_range:

                # updating progress tracker attributes
                self.rows_num += 1
                self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | files: {self.files_num}'
        totals_string += f' | rows: {self.rows_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def join_dfs(input_folder: str,
             output_path: str,
             overwrite_output: bool,
             progress_tracker: ModuleProgressTracker
             ) -> None:
    """
    Given a path to a folder containing
    .csv files, reads data and joins them
    into single output path.

    Args:
        input_folder (str): Path to folder containing input CSV files.
        output_path (str): Path to output file.
        overwrite_output (bool): Whether to overwrite existing output file.
        progress_tracker (ModuleProgressTracker): Progress tracker instance.

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

    # getting files in input folder
    files = get_files_in_folder(input_folder=input_folder,
                                extension='.csv')

    # defining placeholder value for dfs list
    dfs_list = []

    # iterating over files in input folder
    for file_name in files:

        # updating progress tracker attributes
        progress_tracker.current_file += 1

        # getting current file input paths
        current_input_path = join(input_folder,
                                  file_name)

        # trying to read current df
        try:

            # reading current df
            current_df = load_df(input_path=current_input_path)

            # adding source file name col
            add_constant_col(df=current_df,
                             col_name='source_file',
                             value=file_name,
                             df_name=file_name,
                             progress_tracker=progress_tracker)

        # handling empty df
        except EmptyDataError:

            # defining placeholder value for current df
            current_df = DataFrame()

        # appending current df to dfs list
        dfs_list.append(current_df)

    # concatenating dfs in dfs list
    final_df = concatenate_dfs(dfs_list)

    # saving df
    save_df(save_path=output_path,
            df=final_df)


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

    # getting output path
    output_path = args_dict['output_path']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running join_dfs function
    join_dfs(input_folder=input_folder,
             output_path=output_path,
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
