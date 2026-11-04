# check gpu module

# Code destined to checking gpu availability.
# Required for conditional imports based on
# gpu availability.

######################################################################
# imports

# avoiding cupy warning if no gpu was found
from warnings import filterwarnings
filterwarnings(action="ignore",
               message="CUDA path could not be detected",
               category=UserWarning,
               module="cupy._environment")

from torch import device

######################################################################
# defining auxiliary functions


def cupy_gpu_is_available() -> bool:
    """
    Checks if GPU is available and visible
    to CuPy.

    Returns:
        bool: True if GPU is available to CuPy, False otherwise.
    """
    # trying to get bool
    try:

        # importing dependencies
        from cupy.cuda import is_available

        # updating gpu availability bool
        gpu_available = is_available()

    except Exception as _:  # noqa

        # updating gpu availability bool
        gpu_available = False

    # returning gpu availability bool
    return gpu_available


def pytorch_gpu_is_available() -> bool:
    """
    Checks if GPU is available and visible
    to PyTorch.

    Returns:
        bool: True if GPU is available to PyTorch, False otherwise.
    """
    # trying to get bool
    try:

        # importing dependencies
        from torch.cuda import is_available

        # updating gpu availability bool
        gpu_available = is_available()

    except Exception as _:  # noqa

        # updating gpu availability bool
        gpu_available = False

    # returning gpu availability bool
    return gpu_available


def gpu_is_available() -> bool:
    """
    Checks if GPU is available to both
    CuPy and PyTorch.

    Returns:
        bool: True if GPU is available to both frameworks, False otherwise.
    """
    # getting gpu availability bools
    cupy_gpu_available = cupy_gpu_is_available()
    pytorch_gpu_available = pytorch_gpu_is_available()

    # getting both gpu availability bool
    gpu_available = (cupy_gpu_available and pytorch_gpu_available)

    # returning both gpu availability bool
    return gpu_available


def get_torch_device() -> device:
    """
    Returns the appropriate PyTorch device
    based on GPU availability.

    Returns:
        device: A PyTorch device object set to 'cuda' if GPU is available, 'cpu' otherwise.
    """
    # defining placeholder for torch device
    torch_device = device('cpu')

    # getting gpu availability bools
    pytorch_gpu_available = pytorch_gpu_is_available()

    # checking if gpu is available
    if pytorch_gpu_available:

        # updating torch device
        torch_device = device('cuda')

    # returning torch device
    return torch_device


def get_gpu_name() -> str:
    """
    Returns the name of the available GPU device.

    Returns:
        str: GPU device name, or 'No GPU found.' if no GPU is available.
    """
    # defining placeholder for gpu name
    gpu_name = 'No GPU found.'

    # trying to get name
    try:

        # importing dependencies
        from torch.cuda import get_device_name

        # updating name
        gpu_name = get_device_name(0)

    # handling exception
    except Exception as _:  # noqa

        # returning gpu name
        return gpu_name

    # returning gpu name
    return gpu_name


def print_gpu_availability() -> None:
    """
    Checks and prints GPU availability
    for CuPy and PyTorch.

    Returns:
        None.
    """
    # printing execution message
    print('checking GPU availability...')

    # defining spacer string
    spacer_str = ('#' * 30)

    # getting gpu availability bools
    cupy_gpu_available = cupy_gpu_is_available()
    pytorch_gpu_available = pytorch_gpu_is_available()
    gpu_available = gpu_is_available()
    gpu_name = get_gpu_name()

    # assembling gpu availability string
    f_string = f'CuPy GPU available: {cupy_gpu_available}\n'
    f_string += f'PyTorch GPU available: {pytorch_gpu_available}\n'
    f_string += f'GPU available: {gpu_available}\n'
    f_string += f'Available GPU: {gpu_name}'

    # printing gpu availability string
    print(spacer_str)
    print(f_string)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # running print_gpu_availability function
    print_gpu_availability()

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
