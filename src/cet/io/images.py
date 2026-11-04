# images io module

# Code destined to storing image
# input/output related functions.

######################################################################
# imports

from cet.config import GPU
from tifffile import imread
from tifffile import imwrite
from cet.gpu.device import transfer_to_gpu
from cet.gpu.device import transfer_from_gpu

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
else:
    from numpy import ndarray

######################################################################
# defining auxiliary functions


def load_image(input_path: str) -> ndarray:
    """
    Given a path to an image, returns
    image as numpy/cupy array, according
    to GPU availability.

    Args:
        input_path (str): Path to the image file to load.

    Returns:
        ndarray: The loaded image as a numpy array (CPU) or cupy array (GPU), depending on GPU availability.
    """
    # reading image
    image = imread(input_path)

    # checking whether image should be passed to gpu ram
    if GPU:

        # transferring array to gpu
        image = transfer_to_gpu(arr=image)

    # returning stack
    return image


def save_image(save_path: str,
               image: ndarray
               ) -> None:
    """
    Given an image, saves it
    to given save path.

    Args:
        save_path (str): Path where the image will be saved.
        image (ndarray): The image array (numpy or cupy) to save.

    Returns:
        None
    """
    # checking whether image is in gpu ram
    if GPU:

        # transferring array from gpu
        image = transfer_from_gpu(arr=image)

    # saving image
    imwrite(save_path,
            image)

######################################################################
# end of current module
