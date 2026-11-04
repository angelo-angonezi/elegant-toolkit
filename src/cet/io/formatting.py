 # formatting io module

# Code destined to storing
# stdout formatting related functions.

######################################################################
# imports

from typing import Sized
from cet.constants import ONE_KB
from cet.constants import ONE_MB
from cet.constants import ONE_GB
from cet.constants import ONE_TB

######################################################################
# defining auxiliary functions


def get_time_str(time_in_seconds: int) -> str:
    """
    Given a time in seconds, returns time in
    adequate format (seconds, minutes or hours).

    Args:
        time_in_seconds (int): Time duration in seconds.

    Returns:
        str: A formatted time string with appropriate unit (e.g., '30s', '5m', '2h').
    """
    # checking whether seconds > 60
    if time_in_seconds >= 60:

        # converting time to minutes
        time_in_minutes = time_in_seconds / 60

        # checking whether minutes > 60
        if time_in_minutes >= 60:

            # converting time to hours
            time_in_hours = time_in_minutes / 60

            # defining time string based on hours
            defined_time = round(time_in_hours)
            time_string = f'{defined_time}h'

        else:

            # defining time string based on minutes
            defined_time = round(time_in_minutes)
            time_string = f'{defined_time}m'

    else:

        # defining time string based on seconds
        defined_time = round(time_in_seconds)
        time_string = f'{defined_time}s'

    # returning time string
    return time_string


def get_number_string(num: int | float,
                      digits: int = 2
                      ) -> str:
    """
    Given a number, returns formatted
    number string - zero-padded to digits
    length if num is an int, or rounded
    to digits decimal places if num is
    a float.

    Args:
        num (int | float): The number to format.
        digits (int, optional): Number of digits for zero-padding (if int) or decimal places (if float). Defaults to 2.

    Returns:
        str: A formatted number string.
    """
    # getting is int bool
    num_is_int = isinstance(num, int)

    # checking if number is int
    if num_is_int:

        # formating number string
        number_string = f'{num:0{digits}d}'

    else:

        # formating number string
        number_string = f'{num:4.{digits}f}'

    # returning formatted number string
    return number_string


def get_size_str(size_in_bytes: int) -> str:
    """
    Given a file/folder size in bytes,
    returns a string in human readable
    format.

    Args:
        size_in_bytes (int): File or folder size in bytes.

    Returns:
        str: A human-readable size string (e.g., '50 mb', '2 gb').
    """
    # defining placeholder value for unit str/normalizer
    unit_str = 'bytes'
    normalizer = 1

    # checking if size in bytes exceeds a terabyte
    if size_in_bytes >= ONE_TB:

        # updating unit str/normalizer
        unit_str = 'tb'
        normalizer *= ONE_TB

    # checking if size in bytes exceeds a gigabyte
    elif size_in_bytes >= ONE_GB:

        # updating unit str/normalizer
        unit_str = 'gb'
        normalizer *= ONE_GB

    # checking if size in bytes exceeds a megabyte
    elif size_in_bytes >= ONE_MB:

        # updating unit str/normalizer
        unit_str = 'mb'
        normalizer *= ONE_MB

    # checking if size in bytes exceeds a kilobyte
    elif size_in_bytes >= ONE_KB:

        # updating unit str/normalizer
        unit_str = 'kb'
        normalizer *= ONE_KB

    # getting adjusted size
    adjusted_size = size_in_bytes / normalizer

    # rounding value
    adjusted_size = round(adjusted_size)

    # assembling size str
    size_str = f'{adjusted_size} {unit_str}'

    # returning size str
    return size_str


def get_digits_num(items_list: Sized) -> int:
    """
    Given a list of elements, returns
    digits num to be used alongside
    get_number_string as string format
    option.

    Args:
        items_list (Sized): A sized collection (e.g., list, tuple) whose length determines the number of digits.

    Returns:
        int: The number of digits needed to represent the length of the list.
    """
    # getting items num
    items_num = len(items_list)

    # getting items num str
    items_num_str = str(items_num)

    # getting items num str len (digits num)
    digits_num = len(items_num_str)

    # returning digits num
    return digits_num

######################################################################
# end of current module
