# morphology measurements module

# Code destined to storing morphology
# measurements related operations.

######################################################################
# imports

from math import pi
from cet.config import GPU
from cet.measurements.mesh import get_mesh_centroid
from cet.measurements.distance import get_scaled_distances

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
    from cupy import count_nonzero
    from cupy import min as arr_min
    from cupy import max as arr_max
else:
    from numpy import ndarray
    from numpy import count_nonzero
    from numpy import min as arr_min
    from numpy import max as arr_max

######################################################################
# defining auxiliary functions


def get_pixel_volume(mask: ndarray) -> int:
    """
    Returns the object volume in pixels
    from a boolean mask.

    Args:
        mask (ndarray): The object boolean mask.

    Returns:
        int: The volume in pixels.
    """
    # getting voxel count (pixel volume)
    object_volume = count_nonzero(mask)

    # returning object volume
    return object_volume


def get_radius_ratio(vertices: ndarray,
                     triangles: tuple,
                     tetrahedron_volumes: ndarray,
                     polyhedron_volume: float
                     ) -> float:
    """
    Returns radius ratio (min/max radial distance
    from centroid to mesh vertices).

    Args:
        vertices (ndarray): The mesh vertices.
        triangles (tuple): The triangle vertices.
        tetrahedron_volumes (ndarray): The tetrahedron volumes.
        polyhedron_volume (float): The polyhedron volume.

    Returns:
        float: The radius ratio.
    """
    # transposing coords
    vertices = vertices.transpose()

    # getting mesh centroid
    centroid = get_mesh_centroid(triangles=triangles,
                                 tetrahedron_volumes=tetrahedron_volumes,
                                 polyhedron_volume=polyhedron_volume)

    # getting radial distances
    radial_distances = get_scaled_distances(coords_a=centroid,
                                            coords_b=vertices)

    # getting min/max radius
    min_radius = arr_min(radial_distances)
    max_radius = arr_max(radial_distances)

    # extracting values from array
    min_radius = min_radius.item()
    max_radius = max_radius.item()

    # getting radius ratio
    radius_ratio = min_radius / max_radius

    # returning radius ratio
    return radius_ratio


def get_area_vol_ratio(volume: float,
                       surface_area: float
                       ) -> float:
    """
    Returns the surface area to volume
    ratio.

    Args:
        volume (float): The object volume.
        surface_area (float): The surface area.

    Returns:
        float: The surface area to volume ratio.
    """
    # calculating area vol ratio
    area_vol_ratio = surface_area / volume

    # returning area vol ratio
    return area_vol_ratio


def get_sphericity(volume: float,
                   surface_area: float
                   ) -> float:
    """
    Returns the sphericity of an object.

    Args:
        volume (float): The object volume.
        surface_area (float): The surface area.

    Returns:
        float: The sphericity value.
    """
    # getting numerator
    numerator = (pi ** (1 / 3)) * ((6 * volume) ** (2 / 3))

    # calculating sphericity
    sphericity = numerator / surface_area

    # returning sphericity
    return sphericity


def get_solidity(volume: float,
                 convex_hull_volume: float
                 ) -> float:
    """
    Returns the solidity of an object
    (0-1 range, 1 = perfectly convex).

    Args:
        volume (float): The object volume.
        convex_hull_volume (float): The convex hull volume.

    Returns:
        float: The solidity value.
    """
    # calculating solidity
    solidity = volume / convex_hull_volume

    # returning solidity
    return solidity


def get_bounding_volume(boundaries: tuple) -> int:
    """
    Returns the bounding volume of an
    object.

    Args:
        boundaries (tuple): The object boundaries.

    Returns:
        int: The bounding volume.
    """
    # extracting coords from boundaries
    z_min, z_max, y_min, y_max, x_min, x_max = boundaries

    # correcting indices
    z_max += 1
    y_max += 1
    x_max += 1

    # getting axes lengths
    z_len = z_max - z_min
    y_len = y_max - y_min
    x_len = x_max - x_min

    # getting bounding volume
    volume = z_len * y_len * x_len

    # returning bounding volume
    return volume


def get_sphere_volume(diameter: float) -> float:
    """
    Returns the approximate volume of a
    spherical object from its diameter.

    Args:
        diameter (float): The cell diameter in pixels.

    Returns:
        float: The approximate volume assuming spherical shape.
    """
    # getting current object radius
    radius = (diameter / 2)

    # getting current object (spherical) volume
    volume = ((4 / 3) * pi * (radius ** 3))

    # returning current object volume
    return volume


def get_volume_radius(volume: float) -> float:
    """
    Returns the radius of a sphere with
    the same volume as the object.

    Args:
        volume (float): The object volume.

    Returns:
        float: The equivalent sphere radius.
    """
    # calculating volume radius
    radius = (((3 * volume) / (4 * pi)) ** (1 / 3))

    # returning volume radius
    return radius

######################################################################
# end of current module
