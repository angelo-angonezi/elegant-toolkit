# system usage module

# Code destined to defining
# system usage related functions.

######################################################################
# imports

from psutil import cpu_percent
from psutil import virtual_memory
from cet.gpu.device import gpu_percent

######################################################################
# functions


def get_cpu_usage() -> int:
    """
    Returns cpu usage in round
    percentage value.

    Returns:
        int: The rounded cpu usage percentage.
    """
    # getting cpu usage
    cpu_usage = cpu_percent()

    # rounding usage
    cpu_usage = round(cpu_usage)

    # returning cpu usage
    return cpu_usage


def get_gpu_usage() -> int:
    """
    Returns gpu usage in round
    percentage value.

    Returns:
        int: The rounded gpu usage percentage.
    """
    # getting gpu usage
    gpu_usage = gpu_percent()

    # rounding usage
    gpu_usage = round(gpu_usage)

    # returning gpu usage
    return gpu_usage


def get_ram_usage() -> int:
    """
    Returns ram usage in round
    percentage value.

    Returns:
        int: The rounded ram usage percentage.
    """
    # getting ram usage
    ram_usage = virtual_memory()

    # converting value to percentage
    ram_usage = ram_usage.percent

    # rounding usage
    ram_usage = round(ram_usage)

    # returning ram usage
    return ram_usage

######################################################################
# end of current module
