# intensity measurements module

# Code destined to storing intensity
# measurements related operations.

######################################################################
# imports

from cet.config import GPU

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import argmax
    from cupy import unique
    from cupy import ndarray
    from cupy import quantile
    from cupy import min as arr_min
    from cupy import max as arr_max
    from cupy import sum as arr_sum
    from cupy import std as arr_std
    from cupy import mean as arr_mean
    from cupy import median as arr_median
else:
    from numpy import argmax
    from numpy import unique
    from numpy import ndarray
    from numpy import quantile
    from numpy import min as arr_min
    from numpy import max as arr_max
    from numpy import sum as arr_sum
    from numpy import std as arr_std
    from numpy import mean as arr_mean
    from numpy import median as arr_median

######################################################################
# defining auxiliary functions


def arr_no_zero_mean(values: ndarray) -> float:
    """
    Returns the mean of an array,
    disregarding zero values.

    Args:
        values (ndarray): The input array.

    Returns:
        float: The mean value excluding zeros.
    """
    # defining placeholder value for values mean
    values_mean = 0

    # removing zeros from array
    filtered_values = values[values > 0]

    # getting filtered values count
    filtered_values_num = len(filtered_values)

    # getting list is empty bool
    list_not_empty = (filtered_values_num > 0)

    # checking if there are any filtered values
    if list_not_empty:

        # getting filtered array mean
        values_mean = arr_mean(filtered_values)

    # returning array mean
    return values_mean


def arr_no_zero_median(values: ndarray) -> float:
    """
    Returns the median of an array,
    disregarding zero values.

    Args:
        values (ndarray): The input array.

    Returns:
        float: The median value excluding zeros.
    """
    # defining placeholder value for values mean
    values_mean = 0

    # removing zeros from array
    filtered_values = values[values > 0]

    # getting filtered values count
    filtered_values_num = len(filtered_values)

    # getting list is empty bool
    list_not_empty = (filtered_values_num > 0)

    # checking if there are any filtered values
    if list_not_empty:

        # getting filtered array mean
        values_mean = arr_median(filtered_values)

    # returning array mean
    return values_mean


def arr_mode(values: ndarray) -> int:
    """
    Returns the mode of an array.

    Args:
        values (ndarray): The input array.

    Returns:
        int: The mode value.
    """
    # getting array unique values/counts
    values, counts = unique(values,
                           return_counts=True)

    # getting max count index
    max_index = argmax(counts)

    # getting mode
    values_mode = values[max_index]

    # converting data type
    values_mode = int(values_mode)

    # returning mode
    return values_mode


def arr_mode_ratio(values: ndarray) -> float:
    """
    Returns the mode ratio of an array.

    Args:
        values (ndarray): The input array.

    Returns:
        float: The mode ratio value.
    """
    # getting number of values in array
    values_count = len(values)

    # getting array mode
    values_mode = arr_mode(values=values)

    # filtering array by mode
    filtered_arr = values[values == values_mode]

    # getting mode count
    mode_count = len(filtered_arr)

    # getting mode ratio
    mode_ratio = mode_count / values_count

    # returning mode ratio
    return mode_ratio


def get_measurement(values: ndarray,
                    measurement: str
                    ) -> int | float:
    """
    Returns a specified measurement from
    a series of values.

    Args:
        values (ndarray): The input array.
        measurement (str): The measurement type.

    Returns:
        int | float: The measurement value.

    Raises:
        Exception: If measurement is invalid.
    """
    # assembling measurements dict
    measurement_funcs = {'min': arr_min,
                         'max': arr_max,
                         'mean': arr_mean,
                         'no_zero_mean': arr_no_zero_mean,
                         'sum': arr_sum,
                         'std': arr_std,
                         'median': arr_median,
                         'no_zero_median': arr_no_zero_median,
                         'mode': arr_mode,
                         'mode_ratio': arr_mode_ratio,
                         'q': quantile}

    # getting valid function names
    valid_funcs = measurement_funcs.keys()
    valid_funcs = list(valid_funcs)

    # checking if measurement is quantile
    if measurement.startswith('q') and measurement[1:].isdigit():

        # converting data types
        quantile_percent = int(measurement[1:])

        # rescaling quantile to 0-1
        quantile_percent /= 100

        # dynamically applying function
        measurement_func = lambda x: measurement_funcs['q'](x, quantile_percent)

    else:

        # getting default measurement function
        measurement_func = measurement_funcs.get(measurement)

    # checking if measurement is valid
    if measurement_func is None:

        # defining error message
        e_string = f'Invalid measurement "{measurement}".\n'
        e_string += f'Valid measurements: {valid_funcs}\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # getting measurement value
    measurement_value = measurement_func(values)

    # converting data types
    measurement_value = float(measurement_value)

    # getting measurement int bool
    measurement_is_int = measurement_value.is_integer()

    # checking if value is integer
    if measurement_is_int:

        # converting data types
        measurement_value = int(measurement_value)

    # returning measurement value
    return measurement_value

######################################################################
# end of current module
