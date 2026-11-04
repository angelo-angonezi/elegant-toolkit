 # cli io module

# Code destined to storing command
# line related functions.

######################################################################
# imports

import sys
from time import time
from os.path import join
from subprocess import run
from datetime import datetime
from cet.constants import SPACER_STR
from cet.constants import SKIP_ENTER_FLAG
from cet.io.formatting import get_time_str
from cet.constants import OVERWRITE_OUTPUT_FLAG
from cet.pipelines.modules import filter_df_module

######################################################################
# defining auxiliary functions


def get_channels_dict(channels_str: str | None) -> dict:
    """
    Given a string representing a dictionary
    of channels (channel_name@channel_path),
    returns string converted to dictionary.

    Args:
        channels_str (str | None): A string containing channel definitions in 'name@path' format separated by commas, or None for an empty dictionary.

    Returns:
        dict: A dictionary with channel names as keys and channel paths as values.
    """
    # defining placeholder for channels dict
    channels_dict = {}

    # getting channels is none bool
    channels_is_none = (channels_str is None)

    # checking if channels str is empty
    if channels_is_none:

        # returning empty dict
        return channels_dict

    # splitting channels string
    channels_split = channels_str.split(',')  # noqa

    # iterating over channels split
    for channel_split in channels_split:

        # splitting current string into key:value
        current_split = channel_split.split('@')  #  had to use this instead of ":"
                                                  #  because ":" is commonly found in drive paths

        # getting current key/value
        key, value = current_split

        # assembling current dict
        current_dict = {key: value}

        # updating channels dict
        channels_dict.update(current_dict)

    # returning channels dict
    return channels_dict


def sort_channels_dict(channels_dict: dict) -> dict:
    """
    Given a channels dict (as returned by get_channels_dict),
    returns it sorted by path (value), so that repeated paths
    end up adjacent - allows single-slot image caches downstream
    to catch non-consecutive repeats without loading the same
    image twice.

    Args:
        channels_dict (dict): A dictionary with channel names as keys and channel paths as values.

    Returns:
        dict: The channels dict, sorted by path (value).
    """
    # sorting channels dict items by path (value)
    sorted_items = sorted(channels_dict.items(),
                          key=lambda item: item[1])

    # defining placeholder for sorted channels dict
    sorted_channels_dict = {}

    # iterating over sorted items
    for channel_item in sorted_items:

        # getting current channel key/path
        key, value = channel_item

        # assembling current dict
        current_dict = {key: value}

        # updating sorted channels dict
        sorted_channels_dict.update(current_dict)

    # returning sorted channels dict
    return sorted_channels_dict


def get_scales_dict(scales_str: str) -> dict:
    """
    Given a string representing a dictionary
    of distance scales (x=x_scale),
    returns string converted to dictionary.

    Args:
        scales_str (str): A string containing scale definitions in 'key=value' format separated by commas.

    Returns:
        dict: A dictionary with scale keys as strings and scale values as floats.
    """
    # defining placeholder for scales dict
    scales_dict = {}

    # splitting scales string
    scales_split = scales_str.split(',')

    # iterating over scales split
    for scale_split in scales_split:

        # splitting current string into key:value
        current_split = scale_split.split('=')

        # getting current key/value
        key, value = current_split

        # converting data types
        key = str(key)
        value = float(value)

        # assembling current dict
        current_dict = {key: value}

        # updating scales dict
        scales_dict.update(current_dict)

    # returning scales dict
    return scales_dict


def get_distances_list(distances: str) -> list:
    """
    Given a distances string, returns
    distances as list of integers.

    Args:
        distances (str): A string containing distance values separated by commas.

    Returns:
        list: A sorted list of integer distances.
    """
    # defining placeholder value for distances list
    distances_list = []

    # splitting distances string
    distances_split = distances.split(',')

    # iterating over distances split
    for distance in distances_split:

        # converting distance to integer
        distance = int(distance)

        # appending current distance to distances list
        distances_list.append(distance)

    # sorting list
    distances_list = sorted(distances_list)

    # returning distances list
    return distances_list


def get_group_cols_list(group_cols: str) -> list:
    """
    Given a string of format "str1,str2,str3",
    returns a list of format ['str1', 'str2', 'str3'].

    Args:
        group_cols (str): A string containing column names separated by commas.

    Returns:
        list: A sorted list of column names.
    """
    # defining placeholder value for cols list
    cols_list = []

    # splitting stratification col string
    cols_split = group_cols.split(',')

    # iterating over cols split
    for col in cols_split:

        # appending current distance to distances list
        cols_list.append(col)

    # sorting list
    cols_list = sorted(cols_list)

    # returning cols list
    return cols_list


def assemble_command(module: str,
                     args: dict,
                     flags: list | None = None,
                     ) -> list:
    """
    Given a module and respective args,
    returns subprocess.run compatible
    command.

    Args:
        module (str): The module name to run as a subprocess.
        args (dict): A dictionary of command-line arguments where keys are argument flags and values are argument values. Values can be lists for repeatable flags.
        flags (list | None, optional): Additional flags to append to the command. Defaults to None.

    Returns:
        list: A list of strings suitable for subprocess.run, containing the Python executable, module name, and all arguments.
    """
    # getting python executable (inside conda env)
    python_executable = sys.executable

    # defining base command
    command = [python_executable, '-m', module]

    # getting dict items
    dict_items = args.items()

    # iterating over dict items
    for dict_item in dict_items:

        # getting current dict elements
        arg_key, arg_value = dict_item

        # getting current arg value is list bool (repeatable flag, e.g. one "-dd" per dot description)
        arg_value_is_list = isinstance(arg_value, list)

        # checking whether current arg value is a list
        if arg_value_is_list:

            # iterating over each value, repeating the flag for every item
            for arg_value_item in arg_value:
                command.append(arg_key)
                command.append(str(arg_value_item))

        else:

            # converting data types
            arg_value = str(arg_value)

            # appending current arg to command
            command.append(arg_key)
            command.append(arg_value)

    # checking whether extra flags where passed
    if flags:

        # adding extra flags to command
        command.extend(flags)

    # returning command
    return command


def check_wavelength_set(channel_str: str,
                         channel_wavelengths: dict
                         ) -> None:
    """
    Given a channel key and a dict of channel wavelengths,
    raises a descriptive error if the channel has no
    wavelength set (required to deconvolve it).

    Args:
        channel_str (str): Channel key (e.g., 'ch0').
        channel_wavelengths (dict): Dictionary mapping channel keys to wavelengths (None if not set).

    Raises:
        Exception: If the channel has no wavelength set.
    """
    # getting current wavelength
    current_wavelength = channel_wavelengths[channel_str]

    # checking whether current channel wavelength is set
    if current_wavelength is None:

        # defining error message
        e_string = f'Channel {channel_str} has no wavelength set, but deconvolution is enabled for it.\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)


def assemble_filter_commands(df_path: str,
                             filters: dict[str, str]
                             ) -> list:
    """
    Given a df path and a dict of filters (column -> condition),
    assembles one filter_df command per filter, filtering the
    df in place.

    Args:
        df_path (str): Path to the df [.csv] to filter in place.
        filters (dict[str, str]): Dictionary mapping column names to filter conditions.

    Returns:
        list: A list of commands (one per filter), each suitable for subprocess.run.
    """
    # initializing commands list
    filter_commands = []

    # getting dict items
    dict_items = filters.items()

    # looping through filters
    for filter_item in dict_items:

        # getting current column/condition
        column, condition = filter_item

        # assembling current filter command
        current_command = assemble_command(module=filter_df_module,
                                           args={'-i': df_path,
                                                 '-cn': column,
                                                 '-co': condition,
                                                 '-o': df_path},
                                           flags=['-ow'])
        filter_commands.append(current_command)

    # returning filter commands
    return filter_commands


def assemble_measurements_str(channels_folder: str,
                              channel_names: dict,
                              measurements_dict: dict,
                              masks_folder: str | None = None
                              ) -> str:
    """
    Given a channels folder, a dict of channel
    names, and a dict of measurements per
    channel/mask key, returns assembled
    measurements string (masks folder required
    only if any key refers to a mask).

    Args:
        channels_folder (str): Path to the channels folder.
        channel_names (dict): Dictionary mapping channel keys to channel names.
        measurements_dict (dict): Dictionary where keys are channel/mask keys and values are lists of measurements to extract from each.
        masks_folder (str | None, optional): Path to masks folder, required if any key in measurements_dict refers to a mask. Defaults to None.

    Returns:
        str: A comma-separated string of measurements in format 'channel_name#measurement@folder_path'.

    Raises:
        Exception: If a key refers to a mask but masks_folder is None, or to a channel with no name set.
    """
    # defining placeholder value for measurements list
    measurements_list = []

    # getting dict items
    dict_items = measurements_dict.items()

    # iterating over dict items
    for measurement_item in dict_items:

        # getting current key/value
        channel_key, measurements = measurement_item

        # getting channel name
        channel_name = channel_names[channel_key]

        # checking whether channel has a name (unused channels are None)
        if channel_name is None:

            # defining error message
            e_string = f'Channel {channel_key} has measurements but no name set.\n'
            e_string += f'Please, check and try again.'

            # quitting
            raise Exception(e_string)

        # getting key is channel/mask bools
        key_is_channel = (channel_key.startswith('ch'))

        # checking whether current key is channel
        if key_is_channel:

            # getting current folder
            current_folder = join(channels_folder,
                                  channel_key)

        else:  # key is mask

            # checking if masks folder is valid
            if masks_folder is not None:

                # getting current folder
                current_folder = join(masks_folder,
                                      channel_key)

            else:

                # defining error message
                e_string = f'Invalid path for masks folder {masks_folder}.'  # noqa
                e_string += f'Please, check and try again.'

                # quitting
                raise Exception(e_string)

        # iterating over measurements
        for measurement in measurements:

            # assembling current measurement str
            measurement_str = f'{channel_name}#{measurement}@{current_folder}'

            # appending current measurement str to measurements list
            measurements_list.append(measurement_str)

    # assembling measurements string
    measurements_str = ','.join(measurements_list)

    # returning measurements string
    return measurements_str


def run_command(command: list,
                simulate: bool
                ) -> int:
    """
    Given a command as a list, uses current
    os to run command, returning exit code
    as output.

    Args:
        command (list): A list of command arguments to execute via subprocess.run.
        simulate (bool): If True, prints the command instead of executing it.

    Returns:
        int: The exit code returned by the subprocess, or 0 if simulate is True.
    """
    # defining placeholder value for exit code
    exit_code = 0

    # checking simulate bool
    if simulate:

        # getting current command string
        command_str = (' '.join(command))

        # printing the command
        print(command_str)

    else:

        # running command
        result = run(command)

        # getting exit code
        exit_code = result.returncode

    # returning exit code
    return exit_code


def command_spacer(command_index: int,
                   commands_num: int,
                   spacer_str: str
                   ) -> None:
    """
    Given a command index and total
    commands num, prints spacer string.

    Args:
        command_index (int): The current command index (1-based).
        commands_num (int): The total number of commands.
        spacer_str (str): The spacer string to print before and after the command message.

    Returns:
        None
    """
    # defining command spacer str
    s_string = f'###### COMMAND {command_index} OF {commands_num} ######'

    # printing strings
    print(spacer_str)
    print(s_string)
    print(spacer_str)


def assemble_run_summary_table(rows_list: list) -> str:
    """
    Given a list of run summary rows (each a
    dict with 'command', 'start_time', 'end_time'
    and 'run_time' keys), returns an ASCII table
    string with those columns.

    Args:
        rows_list (list): A list of dicts, each with 'command', 'start_time', 'end_time' and 'run_time' string values.

    Returns:
        str: An ASCII table string with a header row, a separator row, and one row per command.
    """
    # defining columns list
    columns_list = ['command', 'start_time', 'end_time', 'run_time']

    # defining placeholder for column widths dict
    widths_dict = {}

    # iterating over columns
    for column in columns_list:

        # getting current column's cell strings (header included)
        cell_strs = [column] + [str(row[column]) for row in rows_list]

        # getting current column's max width
        column_width = max(len(cell_str) for cell_str in cell_strs)

        # updating widths dict
        widths_dict[column] = column_width

    # defining row line assembly function
    def assemble_row_line(cells_dict: dict) -> str:

        # getting current padded cells list
        padded_cells = [str(cells_dict[column]).ljust(widths_dict[column])
                        for column in columns_list]

        # assembling row line
        row_line = '| ' + ' | '.join(padded_cells) + ' |'

        # returning row line
        return row_line

    # assembling header dict (column name as its own value)
    header_dict = {column: column for column in columns_list}

    # assembling header/separator lines
    header_line = assemble_row_line(cells_dict=header_dict)
    separator_line = '+-' + '-+-'.join('-' * widths_dict[column] for column in columns_list) + '-+'

    # assembling table lines list
    table_lines = [separator_line, header_line, separator_line]

    # iterating over rows
    for row in rows_list:

        # appending current row line to table lines
        table_lines.append(assemble_row_line(cells_dict=row))

    # closing table
    table_lines.append(separator_line)

    # assembling table string
    table_str = '\n'.join(table_lines)

    # returning table string
    return table_str


def save_run_summary(rows_list: list,
                     log_folder: str,
                     run_start_dt: datetime
                     ) -> None:
    """
    Given a list of run summary rows, a log folder
    and the run's start datetime, assembles the run
    summary ASCII table and saves it to log folder,
    as "run_summary-{date}-{time}.txt".

    Args:
        rows_list (list): A list of dicts, each with 'command', 'start_time', 'end_time' and 'run_time' string values.
        log_folder (str): Path to the folder where the run summary file will be saved.
        run_start_dt (datetime): The datetime at which the run started, used to name the summary file.

    Returns:
        None
    """
    # getting run start str (used in summary file name)
    run_start_str = run_start_dt.strftime('%Y-%m-%d-%H-%M-%S')

    # assembling run summary file name/path
    run_summary_name = f'run_summary-{run_start_str}.txt'
    run_summary_path = join(log_folder, run_summary_name)

    # assembling run summary table string
    run_summary_str = assemble_run_summary_table(rows_list=rows_list)

    # saving run summary file
    with open(run_summary_path, 'w') as run_summary_file:
        run_summary_file.write(run_summary_str)


def run_commands(commands_list: list,
                 skip_enter: bool = False,
                 overwrite_output: bool = False,
                 check_exit: bool = True,
                 simulate: bool = False,
                 log_folder: str | None = None
                 ) -> None:
    """
    Given a list of commands (each command
    itself a list of argv strings),
    runs each command in current os.

    Args:
        commands_list (list): A list of command lists to execute, where each inner list is command arguments for subprocess.run.
        skip_enter (bool, optional): If True, appends SKIP_ENTER_FLAG to each command. Defaults to False.
        overwrite_output (bool, optional): If True, appends OVERWRITE_OUTPUT_FLAG to each command. Defaults to False.
        check_exit (bool, optional): If True, breaks the sequence if any command returns a non-zero exit code. Defaults to True.
        simulate (bool, optional): If True, prints commands instead of executing them. Defaults to False.
        log_folder (str | None, optional): If given, an existing folder to save a "run_summary-{date}-{time}.txt" file to, containing an ASCII table (command/start_time/end_time/run_time) of the run. Defaults to None (no summary saved).

    Returns:
        None
    """
    # getting current time (start time)
    start_time = time()

    # getting current datetime (used to name run summary file)
    run_start_dt = datetime.now()

    # getting commands num
    commands_num = len(commands_list)

    # defining placeholder for current command index
    current_command_index = 0

    # defining placeholder for run summary rows list
    run_summary_rows = []

    # checking whether a log folder was given
    if log_folder is not None:

        # saving (empty) run summary file, so it exists from the start of the run
        save_run_summary(rows_list=run_summary_rows,
                         log_folder=log_folder,
                         run_start_dt=run_start_dt)

    # iterating over commands in commands list
    for command in commands_list:

        # updating current command index
        current_command_index += 1

        # printing spacer
        command_spacer(command_index=current_command_index,
                       commands_num=commands_num,
                       spacer_str=SPACER_STR)

        # checking skip enter toggle
        if skip_enter:

            # appending skip enter flag
            command.append(SKIP_ENTER_FLAG)

        # checking overwrite output toggle
        if overwrite_output:

            # appending overwrite output flag
            command.append(OVERWRITE_OUTPUT_FLAG)

        # getting current command's start time
        command_start_time = time()

        # running current command
        exit_code = run_command(command=command,
                                simulate=simulate)

        # getting current command's end time
        command_end_time = time()

        # getting current command's run time
        command_run_time = command_end_time - command_start_time
        command_run_time = round(command_run_time)

        # getting current command's row (added to run summary table)
        command_row = {'command': ' '.join(command),
                       'start_time': datetime.fromtimestamp(command_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                       'end_time': datetime.fromtimestamp(command_end_time).strftime('%Y-%m-%d %H:%M:%S'),
                       'run_time': get_time_str(time_in_seconds=command_run_time)}

        # appending current command's row to run summary rows list
        run_summary_rows.append(command_row)

        # checking whether a log folder was given
        if log_folder is not None:

            # saving run summary file (progressively populated, so previous
            # commands' timings are kept even if the pipeline breaks later)
            save_run_summary(rows_list=run_summary_rows,
                             log_folder=log_folder,
                             run_start_dt=run_start_dt)

        # checking if exit code needs to be verified
        if check_exit:

            # getting run successful bool
            run_successful = (exit_code == 0)

            # checking exit code
            if not run_successful:

                # assembling error message
                e_string = f'Error while running command "{command}"\n'
                e_string += f'Exiting pipeline.'

                # printing error message
                print(e_string)

                # quitting
                exit()

    # printing spacer
    print(SPACER_STR)

    # getting current time (end time)
    end_time = time()

    # getting elapsed time
    elapsed_time = end_time - start_time
    elapsed_time = round(elapsed_time)

    # getting time string
    time_str = get_time_str(time_in_seconds=elapsed_time)

    # printing execution message
    f_string = f'all {commands_num} commands successfully executed in {time_str}.'
    print(f_string)

######################################################################
# end of current module
