# console output module

# Code destined to defining
# console output related functions.

######################################################################
# imports

from sys import argv
from sys import stdout
from cet.config import GPU
from os.path import basename
from os import get_terminal_size
from cet.io.cli import get_channels_dict
from cet.io.cli import sort_channels_dict
from cet.io.formatting import get_number_string

######################################################################
# functions


def get_console_width() -> int:
    """
    Returns current console width.

    Returns:
        int: The current console width.
    """
    # defining placeholder value for width
    width = 50

    # trying to getting console dimensions
    try:

        # updating width
        width, _ = get_terminal_size()

    # handling exception
    except OSError:

        # returning predefined width
        return width

    # returning console width
    return width


def get_module_name() -> str:
    """
    Returns name of the
    python script being run.

    Returns:
        str: The name of the running python script.
    """
    # getting main file
    main_file = argv[0]

    # getting module base name
    base_name = basename(main_file)

    # getting module name (removing extension)
    module_name = base_name.replace('.py', '')

    # returning module name
    return module_name


def print_dict_elements(dict_name: str,
                        a_dict: dict
                        ) -> None:
    """
    Given a dictionary, prints each key
    and value side by side on a new
    line, such as:
    --dict_name--
    key1: value1
    key2: value2

    Args:
        dict_name (str): The name to print above the dict elements.
        a_dict (dict): The dictionary whose elements to print.

    Returns:
        None.
    """
    # defining base name string
    params_string = f'--{dict_name}--'

    # getting dict items
    dict_items = a_dict.items()

    # iterating over dict items
    for dict_item in dict_items:

        # getting params key/value
        param_key, param_value = dict_item

        # checking if param is channels dict
        if param_key == 'channels':

            # checking if channels is not empty
            if param_value:

                # getting channels dict
                channels_dict = get_channels_dict(channels_str=param_value)

                # sorting channels dict by path
                channels_dict = sort_channels_dict(channels_dict=channels_dict)

                # getting channels dict items
                channels_items = channels_dict.items()

                # getting channel dict printable elements
                channels_list = [f'\n{key}@{value}' for key, value in channels_items]

                # updating param value
                param_value = ''.join(channels_list)

        # getting current param string
        current_param_string = f'\n{param_key}: {param_value}'

        # appending current param string to params string
        params_string += current_param_string

    # printing final params string
    print(params_string)


def enter_to_continue(skip: bool = False) -> None:
    """
    If skip param is False,
    waits for user input ("Enter")
    and once press, continues to
    run code.

    Args:
        skip (bool): Whether to skip waiting for user input.

    Returns:
        None.
    """
    # checking skip bool
    if not skip:

        # defining enter_string
        enter_string = f'press "Enter" to continue'

        # waiting for user input
        input(enter_string)

    # returning None
    return None


def print_execution_parameters(params_dict: dict) -> None:
    """
    Given a list of execution
    parameters, prints given
    parameters on console, such as:
    '''
    --Execution parameters--
    input_folder: /home/angelo/Desktop/ml_temp/imgs/
    output_folder: /home/angelo/Desktop/ml_temp/overlays/
    '''

    Args:
        params_dict (dict): The execution parameters to print.

    Returns:
        None.
    """
    # defining dict name
    dict_name = 'Execution parameters'

    # defining spacer string
    spacer_str = ('_' * 50)

    # getting current module name
    module_name = get_module_name()

    # defining placeholder value for print dict
    print_dict = {}

    # getting module dict
    module_dict = {'module': module_name}

    # getting gpu dict
    gpu_dict = {'gpu_available': GPU}

    # updating params_dict
    print_dict.update(module_dict)
    print_dict.update(params_dict)
    print_dict.update(gpu_dict)

    # printing spacer
    print(spacer_str)

    # printing dict elements
    print_dict_elements(dict_name=dict_name,
                        a_dict=print_dict)

    # printing spacer
    print(spacer_str)


def flush_string(string: str,
                 margin: int = 2,
                 space_string: str = ' '
                 ) -> None:
    """
    Given a string, writes and
    flushes it in the console using
    sys library, and resets cursor
    to the start of the line (writes
    N backspaces at the end of line,
    where N = len(string)).

    Args:
        string (str): The string to write and flush.
        margin (int): The margin to discount from the console width.
        space_string (str): The character to use as the spacer.

    Returns:
        None.
    """
    # getting console width
    console_width = get_console_width()

    # getting string length
    string_len = len(string)

    # getting size difference
    width_diff = console_width - string_len

    # discounting margin from width diff to avoid console overflow
    width_diff -= margin

    # getting spacer
    empty_space = space_string * width_diff

    # updating string
    string += empty_space

    # getting updated string length
    string_len = len(string)

    # creating backspace line
    backspace_line = '\b' * string_len

    # writing string
    stdout.write(string)

    # flushing console
    stdout.flush()

    # resetting cursor to start of the line
    stdout.write(backspace_line)


def print_totals(totals_string: str,
                 progress_string: str
                 ) -> None:
    """
    Prints iterations totals.

    Args:
        totals_string (str): The totals string to print.
        progress_string (str): The current progress string, used to clear the console.

    Returns:
        None.
    """
    # clearing console
    clear_progress(progress_string=progress_string)

    # printing totals string
    print(totals_string)


def clear_progress(progress_string: str) -> None:
    """
    Writes empty space to cover current
    progress string's size in console.

    Args:
        progress_string (str): The current progress string, whose size defines the space to clear.

    Returns:
        None.
    """
    # getting current progress string length
    string_len = len(progress_string)

    # creating empty line
    empty_line = ' ' * string_len

    # creating backspace line
    backspace_line = '\b' * string_len

    # writing string
    stdout.write(empty_line)

    # flushing console
    stdout.flush()

    # resetting cursor to start of the line
    stdout.write(backspace_line)


def get_percentage_string(percentage: int) -> str:
    """
    Given a value in percentage,
    returns value as a string,
    adding '%' to the right side.

    Args:
        percentage (int): The percentage value to convert.

    Returns:
        str: The formatted percentage string.
    """
    # updating value to be in range of 2 digits
    percentage_str = get_number_string(num=percentage,
                                       digits=2)

    # assembling percentage string
    percentage_string = f'{percentage_str}%'

    # checking if percentage is 100%
    if percentage == 100:

        # updating percentage string
        percentage_string = '100%'

    # returning percentage string
    return percentage_string

######################################################################
# end of current module
