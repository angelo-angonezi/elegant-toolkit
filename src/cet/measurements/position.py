# position measurements module

# Code destined to storing position
# measurements related operations.

######################################################################
# imports

from cet.config import GPU

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import stack
    from cupy import ndarray
    from cupy import argwhere
    from cupy import min as arr_min
    from cupy import max as arr_max
    from cupy import mean as arr_mean
else:
    from numpy import stack
    from numpy import ndarray
    from numpy import argwhere
    from numpy import min as arr_min
    from numpy import max as arr_max
    from numpy import mean as arr_mean

######################################################################
# defining auxiliary functions


def get_round_mean(values: ndarray) -> int:
    """
    Returns the rounded mean value of
    an array.

    Args:
        values (ndarray): The input array.

    Returns:
        int: The rounded mean value.
    """
    # getting array mean
    mean_value = arr_mean(values)

    # extracting value from array
    mean_value = mean_value.item()

    # rounding mean value
    mean_value = round(mean_value)

    # returning round mean value
    return mean_value


def get_pixel_coords(mask: ndarray) -> ndarray:
    """
    Returns object coordinates from a
    single object boolean mask.

    Args:
        mask (ndarray): The object mask.

    Returns:
        ndarray: The object coordinates.
    """
    # getting current object pixel coords
    coords = argwhere(mask)

    # transposing coords
    transposed_coords = coords.transpose()

    # returning transposed coords
    return transposed_coords


def get_pixel_centroid(coords: ndarray) -> tuple:
    """
    Returns the centroid from object
    pixel coordinates.

    Args:
        coords (ndarray): The object coordinates.

    Returns:
        tuple: The centroid as (z, y, x).
    """
    # extracting coords arrays
    zs, ys, xs = coords

    # getting mean coord for each axis
    z_mean = get_round_mean(values=zs)
    y_mean = get_round_mean(values=ys)
    x_mean = get_round_mean(values=xs)

    # assembling final tuple
    object_centroid = (z_mean, y_mean, x_mean)

    # returning final tuple
    return object_centroid


def get_boundaries(coords: ndarray) -> tuple:
    """
    Returns object boundaries from
    pixel coordinates.

    Args:
        coords (ndarray): The object coordinates.

    Returns:
        tuple: Boundaries as (z_min, z_max, y_min, y_max, x_min, x_max).
    """
    # extracting coords arrays
    zs, ys, xs = coords

    # getting min/max coord for each axis
    z_min = arr_min(zs)
    z_max = arr_max(zs)
    y_min = arr_min(ys)
    y_max = arr_max(ys)
    x_min = arr_min(xs)
    x_max = arr_max(xs)

    # extracting values from array
    z_min = z_min.item()
    z_max = z_max.item()
    y_min = y_min.item()
    y_max = y_max.item()
    x_min = x_min.item()
    x_max = x_max.item()

    # converting data types
    z_min = round(z_min)
    z_max = round(z_max)
    y_min = round(y_min)
    y_max = round(y_max)
    x_min = round(x_min)
    x_max = round(x_max)

    # assembling boundaries tuple
    boundaries = (z_min, z_max,
                  y_min, y_max,
                  x_min, x_max)

    # returning boundaries tuple
    return boundaries


def get_boundaries_from_slice(object_slice: tuple) -> tuple:
    """
    Returns object boundaries directly
    from a bounding-box slice tuple
    (e.g. as returned by
    scipy.ndimage.find_objects), avoiding
    a full coordinate min/max scan.

    Args:
        object_slice (tuple): The (z_slice, y_slice, x_slice) bounding-box tuple.

    Returns:
        tuple: Boundaries as (z_min, z_max, y_min, y_max, x_min, x_max).
    """
    # extracting slices from object slice
    z_slice, y_slice, x_slice = object_slice

    # assembling boundaries tuple (slice.stop is exclusive, so max is stop - 1)
    boundaries = (z_slice.start, z_slice.stop - 1,
                  y_slice.start, y_slice.stop - 1,
                  x_slice.start, x_slice.stop - 1)

    # returning boundaries tuple
    return boundaries


def offset_coords(coords: ndarray,
                  offsets: tuple
                  ) -> ndarray:
    """
    Given pixel coordinates local to a
    crop, and the crop's offset within
    the full image, returns the
    coordinates translated to full
    image (global) space.

    Args:
        coords (ndarray): The local (crop-relative) object coordinates.
        offsets (tuple): The crop's (z_offset, y_offset, x_offset) starting position in the full image.

    Returns:
        ndarray: The object coordinates translated to global image space.
    """
    # extracting coords arrays
    zs, ys, xs = coords

    # extracting offsets
    z_offset, y_offset, x_offset = offsets

    # assembling global coords
    global_coords = stack([zs + z_offset, ys + y_offset, xs + x_offset])

    # returning global coords
    return global_coords


def get_bounding_shape(boundaries: tuple) -> tuple:
    """
    Returns the bounding shape from
    object boundaries.

    Args:
        boundaries (tuple): The object boundaries.

    Returns:
        tuple: Shape as (depth, height, width).
    """
    # extracting coords from boundaries
    z_min, z_max, y_min, y_max, x_min, x_max = boundaries

    # getting depth/height/width
    depth = (z_max - z_min)
    height = (y_max - y_min)
    width = (x_max - x_min)

    # assembling bounding shape tuple
    bounding_shape = (depth, height, width)

    # returning bounding shape
    return bounding_shape


def get_centroid_boundaries(coords: tuple,
                            bounding_dims: tuple
                            ) -> tuple:
    """
    Returns boundaries from centroid
    and bounding dimensions.

    Args:
        coords (tuple): The centroid coordinates.
        bounding_dims (tuple): The bounding dimensions.

    Returns:
        tuple: Boundaries as (z_min, z_max, y_min, y_max, x_min, x_max).
    """
    # extracting coords from tuples
    z, y, x = coords
    z_dim, y_dim, x_dim = bounding_dims

    # getting radius from dims
    z_radius = z_dim // 2  # floor division, returns round down to nearest integer
    y_radius = y_dim // 2
    x_radius = x_dim // 2

    # getting min/max coord for each axis
    z_min = z - z_radius
    z_max = z + z_radius
    y_min = y - y_radius
    y_max = y + y_radius
    x_min = x - x_radius
    x_max = x + x_radius

    # assembling boundaries tuple
    boundaries = (z_min, z_max,
                  y_min, y_max,
                  x_min, x_max)

    # returning boundaries tuple
    return boundaries


def string_to_coords(coords_str: str) -> tuple:
    """
    Converts a coords string to a
    tuple of integers.

    Args:
        coords_str (str): The coords string in format "(Z, Y, X)".

    Returns:
        tuple: Coordinates as (z, y, x) integers.
    """
    # assembling coords tuple
    coords = eval(coords_str)

    # returning coords tuple
    return coords


def coords_to_string(coords: tuple) -> str:
    """
    Converts a coords tuple to a
    string representation.

    Args:
        coords (tuple): The coordinates as (z, y, x).

    Returns:
        str: The coords string in format "(Z, Y, X)".
    """
    # assembling coords string
    coords_str = str(coords)

    # returning coords string
    return coords_str

######################################################################
# end of current module
