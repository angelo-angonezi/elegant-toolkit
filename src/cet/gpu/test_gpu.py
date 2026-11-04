# test gpu module

print('initializing...')  # noqa

# Code destined to testing gpu.

######################################################################
# imports

# avoiding cupy warning if no gpu was found
from warnings import filterwarnings
filterwarnings(action="ignore",
               message="CUDA path could not be detected",
               category=UserWarning,
               module="cupy._environment")

import cupy
import torch
from torch import randn as torch_randn
from cupy import matmul as cupy_matmul
from torch import matmul as torch_matmul
from cupy.random import randn as cupy_randn

######################################################################
# defining auxiliary functions


def test_cupy_gpu() -> None:
    """
    Runs simple matmul to test
    if cupy is using gpu.

    Returns:
        None.
    """
    # getting package version
    cupy_version = cupy.__version__

    # printing package version
    f_string = f'CuPy version: {cupy_version}'
    print(f_string)

    # defining matrix size
    size = 10000

    # attempting matmul
    try:

        # creating random matrices
        a = cupy_randn(size, size)
        b = cupy_randn(size, size)

        # running matrix multiplication
        _ = cupy_matmul(a, b)

        # printing execution message
        print('CuPy matmul successful!')

    # handling exception
    except Exception as e:

        # printing error message
        e_string = f'CuPy matmul failed!\n'
        e_string += f'Error: {e}'
        print(e_string)


def test_pytorch_gpu() -> None:
    """
    Runs simple matmul to test
    if pytorch is using gpu.

    Returns:
        None.
    """
    # getting package version
    pytorch_version = torch.__version__

    # printing package version
    f_string = f'PyTorch version: {pytorch_version}'
    print(f_string)

    # defining matrix size
    size = 10000

    # attempting matmul
    try:

        # creating random matrices
        a = torch_randn(size, size, device='cuda')
        b = torch_randn(size, size, device='cuda')

        # running matrix multiplication
        _ = torch_matmul(a, b)

        # printing execution message
        print('PyTorch matmul successful!')

    # handling exception
    except Exception as e:

        # printing error message
        e_string = f'PyTorch matmul failed!\n'
        e_string += f'Error: {e}'
        print(e_string)


def test_gpu() -> None:
    """
    Tests available GPUs and prints
    package-specific results.

    Returns:
        None.
    """
    # printing execution message
    print('testing GPU...')

    # defining spacer string
    spacer_str = ('#' * 30)

    # testing cupy gpu
    print(spacer_str)
    print('testing CuPy...')
    test_cupy_gpu()

    # testing pytorch gpu
    print(spacer_str)
    print('testing PyTorch...')
    test_pytorch_gpu()

######################################################################
# defining main function


def main() -> None:
    """
    Runs main code.
    """
    # running test_gpu function
    test_gpu()

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
