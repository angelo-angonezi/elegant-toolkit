# device module

# Code destined to storing device (GPU)
# related functions.

######################################################################
# imports

import nvidia_smi
from cet.config import GPU

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
else:
    from numpy import ndarray

######################################################################
# defining auxiliary functions


def transfer_to_gpu(arr: ndarray) -> ndarray:
    """
    Given a loaded array, transfers array to
    GPU (converts array to cp.array).

    Args:
        arr (ndarray): The input array to transfer to GPU.

    Returns:
        ndarray: The array converted to a CuPy array on GPU.
    """
    # importing dependencies
    from cupy import asarray  # noqa

    # converting array into cupy array (send to available gpu ram)
    arr = asarray(arr)

    # returning converted array
    return arr


def transfer_from_gpu(arr: ndarray) -> ndarray:
    """
    Given a loaded array, transfers array from
    GPU (converts cp.array to array).

    Args:
        arr (ndarray): The input CuPy array on GPU to transfer.

    Returns:
        ndarray: The array converted to a NumPy array on CPU.
    """
    # importing dependencies
    from cupy import asnumpy  # noqa

    # converting array into numpy array (send to available cpu ram)
    arr = asnumpy(arr)

    # returning converted array
    return arr


def gpu_percent() -> float:
    """
    Returns GPU usage, in percentage,
    in case GPU is available.

    Returns:
        float: GPU memory usage as a percentage (0.0 if GPU unavailable).
    """
    # defining placeholder value for gpu usage
    gpu_usage = 0.0

    # checking if gpu is available
    if GPU:

        # initializing nvidia smi
        nvidia_smi.nvmlInit()

        # getting gpu usage info
        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
        info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        total_mem = info.total
        used_mem = info.used

        # shutting down nvidia smi
        nvidia_smi.nvmlShutdown()

        # converting data types
        total_mem = int(total_mem)
        used_mem = int(used_mem)

        # calculating percentage
        usage_ratio = used_mem / total_mem
        gpu_usage = usage_ratio * 100

    # returning gpu usage
    return gpu_usage

######################################################################
# end of current module
