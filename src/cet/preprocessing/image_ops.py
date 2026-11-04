# image ops module

# Code destined to storing
# shared image operations.

######################################################################
# imports

from cet.config import GPU
from math import log1p as float_log1p
from cet.constants import BIT_DEPTH_MAX_DICT

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import full
    from cupy import clip
    from cupy import floor
    from cupy import log1p
    from cupy import expm1
    from cupy import unique
    from cupy import ndarray
    from cupy import min as arr_min
    from cupy import max as arr_max
else:
    from numpy import full
    from numpy import clip
    from numpy import floor
    from numpy import log1p
    from numpy import expm1
    from numpy import unique
    from numpy import ndarray
    from numpy import min as arr_min
    from numpy import max as arr_max

######################################################################
# defining auxiliary functions


def get_optimized_dtype(image: ndarray) -> str:
    """
    Given a loaded mask, returns the
    "most optimized" dtype for it, e.g.:
    image with 138 unique pixel values ->
    8-bit; image with 2856 unique pixel
    values -> 16-bit; image with 83482
    unique pixel values -> 32-bit.

    Args:
        image (ndarray): The loaded mask to check.

    Returns:
        str: The most optimized dtype for the image.

    Raises:
        Exception: If the object count exceeds 32-bit depth.
    """
    # defining placeholder value for optimized dtype (starting from smallest possible)
    optimized_dtype = 'uint8'

    # getting current image unique ids (including zero/background!!!)
    unique_values = unique(image)

    # getting current image object count (unique ids - including zero/background!!!)
    object_count = len(unique_values)

    # getting maximum bit depth values
    max_8bit = BIT_DEPTH_MAX_DICT.get('uint8')
    max_16bit = BIT_DEPTH_MAX_DICT.get('uint16')
    max_32bit = BIT_DEPTH_MAX_DICT.get('uint32')

    # checking if object count exceeds 8-bit depth
    if object_count > max_8bit:

        # updating optimized dtype
        optimized_dtype = 'uint16'

    # checking if object count exceeds 16-bit depth
    elif object_count > max_16bit:

        # updating optimized dtype
        optimized_dtype = 'uint32'

    # checking if object count exceeds 32-bit depth
    elif object_count > max_32bit:

        # defining error message
        e_string = f'Invalid bit-depth "{object_count}".\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # returning optimized dtype
    return optimized_dtype


def remove_bg(image: ndarray,
              reference_value: int | float
              ) -> ndarray:
    """
    Given an image, removes background
    based on given reference value.

    Args:
        image (ndarray): The image to remove background from.
        reference_value (int | float): The reference value to subtract from image.

    Returns:
        ndarray: The background-removed image.
    """
    # subtracting reference value from image
    image = (image - reference_value)

    # returning processed image
    return image


def rescale_by_reference(image: ndarray,
                         reference_value: int | float
                         ) -> ndarray:
    """
    Given an image, rescales it
    based on given reference value.

    Args:
        image (ndarray): The image to rescale.
        reference_value (int | float): The reference value to rescale image by.

    Returns:
        ndarray: The rescaled image.
    """
    pass


def normalize_by_reference(image: ndarray,
                           reference_value: int | float
                           ) -> ndarray:
    """
    Given an image, normalizes it
    based on given reference value.

    Args:
        image (ndarray): The image to normalize.
        reference_value (int | float): The reference value to normalize image by.

    Returns:
        ndarray: The normalized image.
    """
    pass


def rescale_image(image: ndarray,
                  max_value: int,
                  input_range: tuple | None = None
                  ) -> ndarray:
    """
    Given an image, rescales image
    to fit given max value. By default,
    the image's own min/max are mapped
    to 0/max value; if an input range
    is given, that fixed (low, high)
    range is mapped instead (values
    outside it are clipped first), so
    that rescaled values are comparable
    across images.

    Args:
        image (ndarray): The image to rescale.
        max_value (int): The maximum value to rescale image to.
        input_range (tuple | None): Optional fixed (low, high) intensity range to map to 0/max value.

    Returns:
        ndarray: The rescaled image.
    """
    # converting data types
    image = image.astype('float32')

    # checking whether no fixed input range was given
    if input_range is None:

        # getting image min/max
        image_min = arr_min(image)
        image_max = arr_max(image)

    # if a fixed input range was given
    else:

        # getting fixed min/max
        image_min, image_max = input_range

        # clipping image to fixed range
        image = clip(image,
                     image_min,
                     image_max)

    # rescaling image
    numerator = (image - image_min)
    denominator = (image_max - image_min)
    image = (numerator / denominator)
    image *= max_value

    # rounding values
    image = floor(image)

    # getting optimized bit-depth (dtype)
    optimized_dtype = get_optimized_dtype(image=image)

    # optimizing bit-depth
    image = image.astype(optimized_dtype)

    # returning rescaled image
    return image


def get_normalizer_array(image: ndarray,
                         dtype: str
                         ) -> ndarray:
    """
    Given an image, returns its
    normalizer array, based on image
    dtype.

    Args:
        image (ndarray): The image to build a normalizer array for.
        dtype (str): The dtype whose maximum bit depth value fills the normalizer array.

    Returns:
        ndarray: The normalizer array.
    """
    # getting image shape
    image_shape = image.shape

    # getting current dtype maximum bit depth value
    dtype_max = BIT_DEPTH_MAX_DICT.get(dtype)

    # getting normalizer array
    normalizer_arr = full(shape=image_shape, fill_value=dtype_max)

    # returning normalizer array
    return normalizer_arr


def get_normalization_bounds(dtype: str,
                             intensity_range: tuple | None = None
                             ) -> tuple:
    """
    Given a dtype and an optional intensity
    range, returns the (low, high) bounds
    used to normalize images (dtype range
    if no intensity range is given).

    Args:
        dtype (str): The dtype whose maximum bit depth value is used when no range is given.
        intensity_range (tuple | None): The fixed (low, high) intensity range, or None to use (0, dtype max).

    Returns:
        tuple: The (low, high) normalization bounds as floats.
    """
    # checking if intensity range was not given
    if intensity_range is None:

        # getting current dtype maximum bit depth value
        dtype_max = BIT_DEPTH_MAX_DICT.get(dtype)

        # defining bounds from dtype range
        low = 0.0
        high = float(dtype_max)

    else:

        # defining bounds from given intensity range
        low, high = intensity_range
        low = float(low)
        high = float(high)

    # assembling bounds tuple
    bounds = (low, high)

    # returning bounds
    return bounds


def normalize_by_bit_depth_max(image: ndarray,
                               dtype: str,
                               reverse: bool = False,
                               intensity_range: tuple | None = None
                               ) -> ndarray:
    """
    Given an image, returns normalized
    image based on maximum bit depth (or
    on the given intensity range, clipping
    values outside of it).

    Args:
        image (ndarray): The image to normalize.
        dtype (str): The dtype whose maximum bit depth value normalizes image.
        reverse (bool): Whether to reverse the normalization instead of applying it.
        intensity_range (tuple | None): The fixed (low, high) intensity range to normalize by, or None to use the dtype range.

    Returns:
        ndarray: The normalized (or reversed) image.
    """
    # getting normalization bounds
    low, high = get_normalization_bounds(dtype=dtype,
                                         intensity_range=intensity_range)

    # converting data types
    image = image.astype('float32')

    # checking reverse toggle
    if reverse:

        # applying normalizer to image
        image = (image * (high - low)) + low

        # converting data types
        image = image.astype(dtype)

    else:

        # checking if an intensity range was given
        if intensity_range is not None:

            # clipping image to intensity range
            image = clip(image, low, high)

        # applying normalizer to image
        image = (image - low) / (high - low)

    # returning normalized image
    return image


def normalize_by_log(image: ndarray,
                     dtype: str,
                     reverse: bool = False,
                     intensity_range: tuple | None = None
                     ) -> ndarray:
    """
    Given an image, returns normalized
    image based on intensities log (and
    on the given intensity range, clipping
    values outside of it).

    Args:
        image (ndarray): The image to normalize.
        dtype (str): The dtype whose maximum bit depth value normalizes image.
        reverse (bool): Whether to reverse the normalization instead of applying it.
        intensity_range (tuple | None): The fixed (low, high) intensity range to normalize by, or None to use the dtype range.

    Returns:
        ndarray: The normalized (or reversed) image.
    """
    # getting normalization bounds
    low, high = get_normalization_bounds(dtype=dtype,
                                         intensity_range=intensity_range)

    # applying log(1 + pixel) to bounds (avoiding GPU since it's just a single int)
    log_low = float_log1p(low)
    log_high = float_log1p(high)

    # converting data types
    image = image.astype('float32')

    # checking reverse toggle
    if reverse:

        # applying normalizer to image
        image = (image * (log_high - log_low)) + log_low

        # applying exp(pixel) - 1 to image (reverses normalization)
        image = expm1(image)

        # converting data types
        image = image.astype(dtype)

    else:

        # checking if an intensity range was given
        if intensity_range is not None:

            # clipping image to intensity range
            image = clip(image, low, high)

        # applying log(1 + pixel) to image (applies normalization)
        image = log1p(image)

        # applying normalizer to image
        image = (image - log_low) / (log_high - log_low)

    # returning normalized image
    return image


def normalize_image(image: ndarray,
                    dtype: str,
                    normalization: str = 'bit_depth_max',
                    reverse: bool = False,
                    intensity_range: tuple | None = None
                    ) -> ndarray:
    """
    Given a loaded image, runs specified
    normalization, returning normalized
    image.

    Args:
        image (ndarray): The image to normalize.
        dtype (str): The dtype whose maximum bit depth value normalizes image.
        normalization (str): The normalization type to use ("bit_depth_max"/"log").
        reverse (bool): Whether to reverse the normalization instead of applying it.
        intensity_range (tuple | None): The fixed (low, high) intensity range to normalize by, or None to use the dtype range.

    Returns:
        ndarray: The normalized (or reversed) image.

    Raises:
        Exception: If normalization is not a recognized normalization type.
    """
    # assembling normalization funcs dict
    normalization_funcs = {'bit_depth_max': normalize_by_bit_depth_max,
                           'log': normalize_by_log}

    # getting valid function names
    valid_funcs = normalization_funcs.keys()
    valid_funcs = list(valid_funcs)

    # getting normalization function
    normalization_func = normalization_funcs.get(normalization)

    # checking if normalization is valid
    if normalization_func is None:

        # defining error message
        e_string = f'Invalid normalization "{normalization}".\n'
        e_string += f'Valid normalizations: {valid_funcs}\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # getting normalized image
    image = normalization_func(image=image,
                               dtype=dtype,
                               reverse=reverse,
                               intensity_range=intensity_range)

    # returning normalized image
    return image

######################################################################
# end of current module
