# distance measurements module

# Code destined to storing distance
# measurements related operations.

######################################################################
# imports

from cet.config import GPU

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
    from cupy import asarray
    from cupy import argwhere
    from cupy import min as arr_min
else:
    from numpy import ndarray
    from numpy import asarray
    from numpy import argwhere
    from numpy import min as arr_min

######################################################################
# defining auxiliary functions


def get_distance_type(distance: float,
                      distance_threshold: float
                      ) -> str:
    """
    Returns the distance type based on
    threshold comparison.

    Args:
        distance (float): The distance value.
        distance_threshold (float): The threshold value.

    Returns:
        str: The distance type.
    """
    # defining placeholder value for distance type
    distance_type = 'no_overlap'

    # checking thresholds
    if distance <= distance_threshold:

        # updating distance type
        distance_type = 'overlap'

    # returning distance type
    return distance_type


def get_scaled_distances(coords_a: tuple | ndarray,
                         coords_b: tuple | ndarray,
                         scales_dict: dict | None = None
                         ) -> float | ndarray:
    """
    Returns scaled distance(s) between
    two sets of coordinates.

    Args:
        coords_a (tuple | ndarray): First coordinate point or array.
        coords_b (tuple | ndarray): Second coordinate point or array.
        scales_dict (dict | None): Optional scale factors.

    Returns:
        float | ndarray: The scaled distance(s).
    """
    # converting coords to arrays (normalizes single-point tuples and coordinate arrays alike)
    coords_a = asarray(coords_a, dtype='float32')
    coords_b = asarray(coords_b, dtype='float32')

    # extracting values from coords
    a_z, a_y, a_x = coords_a
    b_z, b_y, b_x = coords_b

    # getting current distances
    z_diff = (a_z - b_z)
    y_diff = (a_y - b_y)
    x_diff = (a_x - b_x)

    # checking if scales dict is not None
    if scales_dict:

        # getting specific distance weights for each axis
        z_scale = scales_dict['z']
        y_scale = scales_dict['y']
        x_scale = scales_dict['x']

        # scaling distances (applying weights according to scales dict)
        z_diff *= z_scale
        y_diff *= y_scale
        x_diff *= x_scale

    # squaring distances
    z_diff = (z_diff ** 2)
    y_diff = (y_diff ** 2)
    x_diff = (x_diff ** 2)

    # getting squared distances sum
    distances_sum = (z_diff + y_diff + x_diff)

    # getting square root of squared distances sum
    scaled_distances = (distances_sum ** 0.5)

    # returning scaled distances
    return scaled_distances


def get_shortest_distance(coord: tuple,
                          coords: ndarray,
                          scales_dict: dict | None = None
                          ) -> tuple:
    """
    Returns the shortest distance and
    its coordinates.

    Args:
        coord (tuple): The reference coordinate.
        coords (ndarray): Array of coordinate points.
        scales_dict (dict | None): Optional scale factors.

    Returns:
        tuple: Shortest distance and its coordinate.
    """
    # getting radial distances (calculates all distances between dot coord and other coords)
    radial_distances = get_scaled_distances(coords_a=coord,
                                            coords_b=coords,
                                            scales_dict=scales_dict)

    # getting min radial distance
    shortest_distance = arr_min(radial_distances)

    # finding min coordinate index
    min_index = argwhere(radial_distances == shortest_distance)

    # getting min distance lamina coords
    z_min_coord = coords[0][min_index][0]
    y_min_coord = coords[1][min_index][0]
    x_min_coord = coords[2][min_index][0]

    # extracting values from array
    z_min_coord = z_min_coord.item()
    y_min_coord = y_min_coord.item()
    x_min_coord = x_min_coord.item()

    # assembling shortest distance coord tuple
    shortest_coord = (z_min_coord, y_min_coord, x_min_coord)

    # assembling final tuple
    final_tuple = (shortest_distance, shortest_coord)

    # returning final tuple
    return final_tuple

######################################################################
# end of current module
