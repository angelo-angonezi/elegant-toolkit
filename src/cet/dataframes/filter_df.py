# filter df module

print('initializing...')  # noqa

# Code destined to filtering
# dataframe based on condition.

######################################################################
# imports

print('importing required libraries...')  # noqa
from argparse import ArgumentParser
from cet.io.dataframes import load_df
from cet.io.dataframes import save_df
from cet.io.files import get_skip_file_bool
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
    description = "filter df module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input path param
    parser.add_argument('-i', '--input-path',
                        dest='input_path',
                        type=str,
                        required=True,
                        help='defines path to input file [.csv]')

    # output path param
    parser.add_argument('-o', '--output-path',
                        dest='output_path',
                        type=str,
                        required=True,
                        help='defines path to output file [.csv]')

    # column name param
    parser.add_argument('-cn', '--column-name',
                        dest='column_name',
                        type=str,
                        required=True,
                        help='defines column name to apply conditional')

    # condition param
    parser.add_argument('-co', '--condition',
                        dest='condition',
                        type=str,
                        required=True,
                        help='defines filtering condition to be applied')

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
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'filtering df...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | iteration: {self.current_iteration}/{self.iterations_num}'
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
        # updating progress tracker attributes (single filter per run)
        self.iterations_num += 1

        # sleeping
        self.wait(0.05)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def filter_df(input_path: str,
              output_path: str,
              column_name: str,
              condition: str,
              overwrite_output: bool,
              progress_tracker: ModuleProgressTracker
              ) -> None:
    """
    Given a path to a file, a column name
    and a filtering condition, saves
    filtered df to given output path.

    Args:
        input_path (str): Path to input file.
        output_path (str): Path to output file.
        column_name (str): Name of column to filter on.
        condition (str): Filtering condition to apply to column.
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
        progress_tracker.current_iteration += 1
        progress_tracker.skipped_iterations += 1

        # skipping
        return None

    # loading df
    df = load_df(input_path=input_path)

    # assembling filter string
    filter_string = f'df["{column_name}"] {condition}'

    # getting filter col
    filter_col = eval(filter_string)

    # filtering df
    filtered_df = df[filter_col]

    # updating progress tracker attributes
    progress_tracker.current_iteration += 1

    # saving df
    save_df(save_path=output_path,
            df=filtered_df)

    # getting original and removed rows counts
    original_df_rows_num = len(df)
    filtered_df_rows_num = len(filtered_df)
    filtered_rows_num = (original_df_rows_num - filtered_df_rows_num)

    # defining filter summary string
    f_string = f'Original df rows num: {original_df_rows_num}\n'
    f_string += f'Filtered df rows num: {filtered_df_rows_num}\n'
    f_string += f'Filtered rows num: {filtered_rows_num}'

    # updating progress tracker attributes
    progress_tracker.end_string = f'{f_string}\n{progress_tracker.end_string}'


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

    # getting output path
    output_path = args_dict['output_path']

    # getting column name
    column_name = args_dict['column_name']

    # getting condition
    condition = args_dict['condition']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running filter_df function
    filter_df(input_path=input_path,
              output_path=output_path,
              column_name=column_name,
              condition=condition,
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
