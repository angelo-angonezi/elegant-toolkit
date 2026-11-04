# mesh measurements module

# Code destined to storing mesh
# measurements related operations.

######################################################################
# imports

from cet.config import GPU
from mcubes import marching_cubes
from scipy.spatial import ConvexHull
from cet.gpu.device import transfer_to_gpu
from cet.gpu.device import transfer_from_gpu

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import pad
    from cupy import ones
    from cupy import array
    from cupy import cross
    from cupy import einsum
    from cupy import ndarray
    from cupy import absolute
    from cupy import concatenate
    from cupy.linalg import norm
    from cupy import sum as arr_sum
    from cupyx.scipy.sparse import coo_matrix
else:
    from numpy import pad
    from numpy import ones
    from numpy import array
    from numpy import cross
    from numpy import einsum
    from numpy import ndarray
    from numpy import absolute
    from numpy import concatenate
    from numpy.linalg import norm
    from numpy import sum as arr_sum
    from scipy.sparse import coo_matrix

######################################################################
# defining auxiliary functions


def get_mesh(mask: ndarray,
             scales_dict: dict | None
             ) -> tuple:
    """
    Returns scaled vertices and faces
    describing an object mesh.

    Args:
        mask (ndarray): The object boolean mask.
        scales_dict (dict | None): Optional scale factors.

    Returns:
        tuple: Vertices and faces (vertices, faces).
    """
    # defining isovalue
    isovalue = 0.5

    # padding image to ensure mesh closure (prevents artifacts of sphericity > 1.0)
    mask = pad(array=mask,
               pad_width=1,
               mode='constant',
               constant_values=0)

    # checking whether image is in gpu ram
    if GPU:

        # transferring array from gpu
        mask = transfer_from_gpu(arr=mask)

    # getting vertices and faces (running marching cubes)
    vertices, faces = marching_cubes(mask, isovalue)

    # shifting vertices back to account for padding offset
    vertices -= 1

    # checking if gpu is available
    if GPU:

        # transferring arrays to gpu
        vertices = transfer_to_gpu(arr=vertices)
        faces = transfer_to_gpu(arr=faces)

    # checking if scales dict is not None
    if scales_dict:

        # getting specific distance weights for each axis
        z_scale = scales_dict['z']
        y_scale = scales_dict['y']
        x_scale = scales_dict['x']

        # scaling distances (applying weights according to scales dict)
        vertices[:, 0] *= z_scale
        vertices[:, 1] *= y_scale
        vertices[:, 2] *= x_scale

    # assembling mesh tuple
    mesh = (vertices, faces)

    # returning object mesh
    return mesh


def build_adjacency(vertices_num: int,
                    faces: ndarray
                    ) -> ndarray:
    """
    Returns sparse adjacency matrix and
    degree vector for an object mesh.

    Args:
        vertices_num (int): Number of vertices.
        faces (ndarray): The mesh faces.

    Returns:
        ndarray: Adjacency matrix and degree vector.
    """
    # getting indices
    i = faces[:, 0]
    j = faces[:, 1]
    k = faces[:, 2]

    # defining row/col indices for symmetric adjacency
    row = concatenate([i, j, j, k, k, i])
    col = concatenate([j, i, k, j, i, k])

    # getting rows num
    rows_num = len(row)

    # creating edges/vertices arrays
    edges_arr = ones(rows_num)
    vertices_arr = ones(vertices_num)

    # defining matrix shape
    matrix_shape = (vertices_num, vertices_num)

    # building sparse adjacency matrix
    adjacency_matrix = coo_matrix((edges_arr, (row, col)), shape=matrix_shape)

    # converting data types
    adjacency_matrix = adjacency_matrix.tocsr()

    # getting matrix sum
    adjacency_matrix_sum = (adjacency_matrix @ vertices_arr)

    # converting data types
    adjacency_matrix_arr = array(adjacency_matrix_sum)

    # getting number of neighbors for each vertex
    deg = adjacency_matrix_arr.flatten()

    # avoid division by zero for isolated vertices
    deg[deg == 0] = 1

    # returning adjacency matrix and degree vector
    return adjacency_matrix, deg


def laplacian_smooth(vertices: ndarray,
                     faces: ndarray,
                     iterations: int = 1,
                     alpha: float = 0.1
                     ) -> ndarray:
    """
    Returns smoothed vertices using Laplacian
    smoothing algorithm.

    Args:
        vertices (ndarray): The mesh vertices.
        faces (ndarray): The mesh faces.
        iterations (int): Number of iterations. Defaults to 1.
        alpha (float): Smoothing factor. Defaults to 0.1.

    Returns:
        ndarray: The smoothed vertices.
    """
    # defining placeholder value for vertices
    vertices = vertices.copy()

    # getting number of vertices
    vertices_num = len(vertices)

    # building adjacency matrix and degree vector
    adjacency_matrix, deg = build_adjacency(vertices_num=vertices_num,
                                            faces=faces)

    # getting iterations range
    iterations_range = range(iterations)

    # iterating over range
    for _ in iterations_range:

        # getting sum of neighbor vertices
        neighbor_sum = (adjacency_matrix @ vertices)

        # calculating mean position of neighboring vertices
        neighbor_mean = (neighbor_sum / deg[:, None])

        # getting current diff
        current_diff = (neighbor_mean - vertices)

        # getting current sum
        current_sum = (current_diff * alpha)

        # update vertex positions using Laplacian rule
        vertices += current_sum

    # returning updated vertices
    return vertices


def taubin_smooth(vertices: ndarray,
                  faces: ndarray,
                  iterations: int = 50,
                  lamb: float = 0.5,
                  mu: float = -0.53
                  ) -> ndarray:
    """
    Returns smoothed vertices using Taubin
    smoothing algorithm.

    Args:
        vertices (ndarray): The mesh vertices.
        faces (ndarray): The mesh faces.
        iterations (int): Number of iterations. Defaults to 50.
        lamb (float): Lambda parameter. Defaults to 0.5.
        mu (float): Mu parameter. Defaults to -0.53.

    Returns:
        ndarray: The smoothed vertices.
    """
    # defining placeholder value for vertices
    vertices = vertices.copy()

    # getting number of vertices
    vertices_num = len(vertices)

    # building adjacency matrix and degree vector once
    adjacency_matrix, deg = build_adjacency(vertices_num=vertices_num,
                                            faces=faces)

    # getting iterations range
    iterations_range = range(iterations)

    # iterating over range
    for _ in iterations_range:

        # applying shrink pass (lambda)
        neighbor_mean = (adjacency_matrix @ vertices) / deg[:, None]
        vertices += lamb * (neighbor_mean - vertices)

        # applying inflate pass (mu)
        neighbor_mean = (adjacency_matrix @ vertices) / deg[:, None]
        vertices += mu * (neighbor_mean - vertices)

    # returning updated vertices
    return vertices


def get_mesh_triangles(vertices: ndarray,
                       faces: ndarray
                       ) -> tuple:
    """
    Returns the triangle vertices
    for an object mesh.

    Args:
        vertices (ndarray): The mesh vertices.
        faces (ndarray): The mesh faces.

    Returns:
        tuple: Triangle vertices (v0, v1, v2).
    """
    # transposing faces
    faces = faces.transpose()

    # getting triangle vertices
    v0 = vertices[faces[0]]
    v1 = vertices[faces[1]]
    v2 = vertices[faces[2]]

    # assembling final tuple
    triangles = (v0, v1, v2)

    # returning final tuple
    return triangles


def get_tetrahedron_volumes(triangles: tuple) -> ndarray:
    """
    Returns tetrahedron volumes for
    an object mesh.

    Args:
        triangles (tuple): The triangle vertices.

    Returns:
        ndarray: The tetrahedron volumes.
    """
    # extracting values from tuple
    v0, v1, v2 = triangles

    # getting cross product
    cross_product = cross(v1, v2)

    # defining subscripts
    subscripts = 'ij,ij->i'

    # calculating scalar triple product
    volumes = einsum(subscripts, v0, cross_product)

    # returning volumes
    return volumes


def get_polyhedron_volume(tetrahedron_volumes: ndarray) -> float:
    """
    Returns the polyhedron volume from
    tetrahedron volumes.

    Args:
        tetrahedron_volumes (ndarray): The tetrahedron volumes.

    Returns:
        float: The polyhedron volume.
    """
    # calculating polyhedron volume
    polyhedron_volume = arr_sum(tetrahedron_volumes)

    # extracting values from array
    polyhedron_volume = polyhedron_volume.item()

    # returning polyhedron volume
    return polyhedron_volume


def get_mesh_volume(polyhedron_volume: float) -> float:
    """
    Returns the volume of an object mesh
    from its polyhedron volume.

    Args:
        polyhedron_volume (float): The polyhedron volume.

    Returns:
        float: The mesh volume.
    """
    # getting absolute value
    volume = absolute(polyhedron_volume)

    # extracting values from array
    volume = volume.item()

    # calculating mesh volume (tetrahedron)
    volume = (volume / 6)

    # returning volume
    return volume


def get_mesh_surface_area(triangles: tuple) -> float:
    """
    Returns the surface area of an
    object mesh.

    Args:
        triangles (tuple): The triangle vertices.

    Returns:
        float: The surface area.
    """
    # extracting values from tuple
    v0, v1, v2 = triangles

    # getting vertices differences
    diff_1 = (v1 - v0)
    diff_2 = (v2 - v0)

    # calculating cross product
    current_cross = cross(diff_1, diff_2)

    # getting matrix norm
    matrix_norm = norm(current_cross, axis=1)

    # calculating mesh surface area
    surface_area = (matrix_norm / 2)

    # getting total volume
    surface_area = arr_sum(surface_area)

    # extracting values from array
    surface_area = surface_area.item()

    # returning surface area
    return surface_area


def get_mesh_centroid(triangles: tuple,
                      tetrahedron_volumes: ndarray,
                      polyhedron_volume: float
                      ) -> tuple:
    """
    Returns the centroid of an object mesh
    from triangle vertices and volumes.

    Args:
        triangles (tuple): The triangle vertices.
        tetrahedron_volumes (ndarray): The tetrahedron volumes.
        polyhedron_volume (float): The polyhedron volume.

    Returns:
        tuple: The centroid as (cz, cy, cx).
    """
    # extracting values from tuple
    v0, v1, v2 = triangles

    # getting vertices sum
    vertices_sum = (v0 + v1 + v2)

    # getting centroids
    centroids = (vertices_sum / 4)

    # getting weighted centroids
    weighted_centroids = (centroids * tetrahedron_volumes[:, None])

    # getting weighted sum
    weighted_sum = arr_sum(weighted_centroids,
                           axis=0)

    # calculating centroid
    centroid = (weighted_sum / polyhedron_volume)

    # extracting values from array
    cz = centroid[0]
    cy = centroid[1]
    cx = centroid[2]

    # extracting values from array
    cz = cz.item()
    cy = cy.item()
    cx = cx.item()

    # assembling final tuple
    centroid = (cz, cy, cx)

    # returning final tuple
    return centroid


def get_convex_hull_volume(vertices: ndarray) -> float:
    """
    Returns the convex hull volume of
    an object mesh.

    Args:
        vertices (ndarray): The mesh vertices.

    Returns:
        float: The convex hull volume.
    """
    # checking whether vertices are in gpu ram
    if GPU:

        # transferring vertices from gpu (convex hull is a cpu-only operation)
        vertices = transfer_from_gpu(arr=vertices)

    # building convex hull
    convex_hull = ConvexHull(vertices)

    # getting convex hull volume
    convex_hull_volume = convex_hull.volume

    # returning convex hull volume
    return convex_hull_volume

######################################################################
# end of current module
