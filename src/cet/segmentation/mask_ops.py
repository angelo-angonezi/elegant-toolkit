# mask ops module

# Code destined to storing
# shared mask operations.

######################################################################
# imports

from copy import copy
from cet.config import GPU
from cet.measurements.mesh import get_mesh
from cet.measurements.mesh import get_mesh_volume
from cet.measurements.labels import get_object_ids
from cet.measurements.mesh import get_mesh_triangles
from cet.measurements.morphology import get_solidity
from cet.measurements.mesh import get_polyhedron_volume
from cet.measurements.mesh import get_convex_hull_volume
from cet.measurements.mesh import get_tetrahedron_volumes
from cet.measurements.position import get_boundaries_from_slice
from cet.progress_tracker.ProgressTracker import ProgressTracker

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import array
    from cupy import arange
    from cupy import ndarray
    from cupy import meshgrid
    from cupy import zeros_like
    from cupyx.scipy.ndimage import find_objects
    from cupyx.scipy.ndimage import binary_closing
    from cupyx.scipy.ndimage import binary_erosion
    from cupyx.scipy.ndimage import binary_dilation
    from cupyx.scipy.ndimage import binary_fill_holes
else:
    from numpy import array
    from numpy import arange
    from numpy import ndarray
    from numpy import meshgrid
    from numpy import zeros_like
    from scipy.ndimage import find_objects
    from scipy.ndimage import binary_closing
    from scipy.ndimage import binary_erosion
    from scipy.ndimage import binary_dilation
    from scipy.ndimage import binary_fill_holes

######################################################################
# progress tracking related functions


class ModuleProgressTracker(ProgressTracker):
    """
    Defines ModuleProgressTracker class.
    """
    # defining ProgressTracker init
    def __init__(self) -> None:
        """
        Initializes a ModuleProgressTracker
        instance and defines class attributes.
        """
        # inheriting attributes and methods from ProgressTracker
        super().__init__()

        # defining current module specific attributes (all possible attributes for these ops)

        # distance
        self.distances_num = 0
        self.current_distance = 0

        # object
        self.objects_num = 0
        self.current_object = 0

        # operation
        self.current_operation = ''

######################################################################
# defining auxiliary functions


def filter_mask(mask: ndarray,
                object_id: int
                ) -> ndarray:
    """
    Given a mask with multiple ids,
    returns filtered mask containing
    only given id.

    Args:
        mask (ndarray): The mask to filter.
        object_id (int): The object id to keep.

    Returns:
        ndarray: The filtered mask, containing only the given object id.
    """
    # defining placeholder for filtered mask
    filtered_mask = mask.copy()

    # removing pixels different from given id
    filtered_mask[mask != object_id] = 0

    # returning filtered mask
    return filtered_mask


def mask_image(image: ndarray,
               mask: ndarray,
               reverse: bool
               ) -> ndarray:
    """
    Given an image and a binary mask,
    applies mask to image, where
    pixels 1 in mask will be kept and
    pixels 0 discarded. If reverse is
    set to True, does the opposite.

    Args:
        image (ndarray): The image to mask.
        mask (ndarray): The binary mask to apply.
        reverse (bool): Whether to invert which pixels are kept.

    Returns:
        ndarray: The masked image.
    """
    # defining placeholder for masked image
    masked_image = image.copy()

    # checking reverse bool
    if reverse:

        # applying mask to image
        masked_image[mask != 0] = 0  # whatever is inside the mask is removed

    else:

        # applying mask to image
        masked_image[mask == 0] = 0  # whatever is inside the mask is kept

    # returning masked image
    return masked_image


def get_bool_mask(mask: ndarray,
                  object_id: int
                  ) -> ndarray:
    """
    Given a mask, returns bool
    mask matching given object id.

    Args:
        mask (ndarray): The mask to check.
        object_id (int): The object id to match.

    Returns:
        ndarray: The boolean mask matching the given object id.
    """
    # getting bool mask
    bool_mask = (mask == object_id)

    # converting data types
    bool_mask = array(bool_mask)

    # returning bool mask
    return bool_mask


def get_object_slices(mask: ndarray) -> dict:
    """
    Given a mask, returns a dict mapping
    each object id present in the mask to
    its tight bounding-box slice tuple,
    obtained via a single O(image_size)
    pass instead of a full-array scan
    per object.

    Args:
        mask (ndarray): The segmentation mask.

    Returns:
        dict: A dictionary mapping each object id to its (z_slice, y_slice, x_slice) bounding-box tuple.
    """
    # getting bounding box slice per label (index i -> label i+1; None if label absent)
    slices_list = find_objects(mask)

    # defining placeholder value for object slices dict
    object_slices = {}

    # iterating over slices list
    for object_id, object_slice in enumerate(slices_list, start=1):

        # skipping absent labels
        if object_slice is not None:

            # updating object slices dict
            object_slices[object_id] = object_slice

    # returning object slices dict
    return object_slices


def get_image_boundaries_mask(mask: ndarray) -> ndarray:
    """
    Given a 3D mask, returns a boolean
    array of the same shape, with True
    values only at the edges (borders)
    of the volume, and False everywhere
    else.

    Args:
        mask (ndarray): The 3D mask to build a boundaries mask for.

    Returns:
        ndarray: The boolean boundaries mask.
    """
    # defining placeholder value for boundaries mask
    boundaries_mask = zeros_like(mask,
                                 dtype=bool)

    # setting edges to True along depth axis
    boundaries_mask[0, :, :] = True
    boundaries_mask[-1, :, :] = True

    # setting edges to True along height axis
    boundaries_mask[:, 0, :] = True
    boundaries_mask[:, -1, :] = True

    # setting edges to True along width axis
    boundaries_mask[:, :, 0] = True
    boundaries_mask[:, :, -1] = True

    # returning boundaries mask
    return boundaries_mask


def get_border_pixel_count(masks_intersection: ndarray) -> int:
    """
    Given an object/image boundaries
    masks intersection, returns the
    number of object pixels that lie
    on the image border.

    Args:
        masks_intersection (ndarray): The object/image boundaries masks intersection.

    Returns:
        int: The number of object pixels lying on the image border.
    """
    # getting border pixel count
    border_pixel_count = masks_intersection.sum()

    # converting data types
    border_pixel_count = int(border_pixel_count)

    # returning border pixel count
    return border_pixel_count


def get_touches_border_bool(masks_intersection: ndarray) -> bool:
    """
    Given an object/image boundaries
    masks intersection, returns True
    if the object touches the image
    border, and False otherwise.

    Args:
        masks_intersection (ndarray): The object/image boundaries masks intersection.

    Returns:
        bool: True if the object touches the image border, False otherwise.
    """
    # getting touches border bool
    touches_border = masks_intersection.any()

    # converting data types
    touches_border = bool(touches_border)

    # returning touches border bool
    return touches_border


def get_objects_touch_bool(mask_a: ndarray,
                           mask_b: ndarray,
                           touch_margin: int = 1
                           ) -> bool:
    """
    Given two object boolean masks
    (cropped to a shared region),
    returns True if the objects touch
    (or are within touch_margin pixels
    of each other), and False otherwise.

    Args:
        mask_a (ndarray): The first object's boolean mask.
        mask_b (ndarray): The second object's boolean mask.
        touch_margin (int): The pixel margin within which objects are considered touching.

    Returns:
        bool: True if the objects touch (within touch_margin), False otherwise.
    """
    # dilating first mask by touch margin
    dilated_a = binary_dilation(input=mask_a,
                                iterations=touch_margin)

    # getting masks intersection
    masks_intersection = (dilated_a & mask_b)

    # getting objects touch bool
    objects_touch = masks_intersection.any()

    # converting data types
    objects_touch = bool(objects_touch)

    # returning objects touch bool
    return objects_touch


def get_boundaries_close_bool(boundaries_a: tuple,
                              boundaries_b: tuple,
                              margin: int
                              ) -> bool:
    """
    Given two objects boundaries,
    returns True if their (margin-
    padded) bounding boxes overlap on
    all axes, and False otherwise.
    Cheap pre-filter to avoid running
    the more expensive touching test
    on far apart objects.

    Args:
        boundaries_a (tuple): The first object's boundaries.
        boundaries_b (tuple): The second object's boundaries.
        margin (int): The margin (in pixels) to pad each bounding box by.

    Returns:
        bool: True if the padded bounding boxes overlap on all axes, False otherwise.
    """
    # extracting coords from boundaries
    z_min_a, z_max_a, y_min_a, y_max_a, x_min_a, x_max_a = boundaries_a
    z_min_b, z_max_b, y_min_b, y_max_b, x_min_b, x_max_b = boundaries_b

    # checking overlap on each axis (padded by margin)
    z_close = (z_min_a - margin <= z_max_b) and (z_min_b - margin <= z_max_a)
    y_close = (y_min_a - margin <= y_max_b) and (y_min_b - margin <= y_max_a)
    x_close = (x_min_a - margin <= x_max_b) and (x_min_b - margin <= x_max_a)

    # getting boundaries close bool
    boundaries_close = (z_close and y_close and x_close)

    # returning boundaries close bool
    return boundaries_close


def get_group_boundaries(boundaries_dict: dict,
                         group: set
                         ) -> tuple:
    """
    Given a dict of object id to
    boundaries, and a group (set) of
    object ids, returns the union of
    their boundaries.

    Args:
        boundaries_dict (dict): A dictionary mapping each object id to its boundaries.
        group (set): The set of object ids to union boundaries for.

    Returns:
        tuple: The group's union boundaries.
    """
    # getting boundaries for objects in group
    group_boundaries = [boundaries_dict[object_id] for object_id in group]

    # unpacking boundaries columns
    z_mins, z_maxs, y_mins, y_maxs, x_mins, x_maxs = zip(*group_boundaries)

    # assembling union boundaries tuple
    union_boundaries = (min(z_mins), max(z_maxs),
                        min(y_mins), max(y_maxs),
                        min(x_mins), max(x_maxs))

    # returning union boundaries
    return union_boundaries


def get_touching_graph(mask: ndarray,
                       object_ids: list,
                       boundaries_dict: dict,
                       touch_margin: int = 1
                       ) -> dict:
    """
    Given a mask, its object ids and
    respective boundaries, returns an
    adjacency dict mapping each object
    id to the set of object ids it
    directly touches (or is within
    touch_margin pixels of).

    Args:
        mask (ndarray): The segmentation mask.
        object_ids (list): The list of object ids in the mask.
        boundaries_dict (dict): A dictionary mapping each object id to its boundaries.
        touch_margin (int): The pixel margin within which objects are considered touching.

    Returns:
        dict: A dictionary mapping each object id to the set of object ids it touches.
    """
    # defining placeholder for touching graph
    touching_graph = {object_id: set() for object_id in object_ids}

    # getting object ids num
    objects_num = len(object_ids)

    # iterating over object id pairs
    for i in range(objects_num):

        # getting current object id/boundaries
        id_a = object_ids[i]
        boundaries_a = boundaries_dict[id_a]

        # iterating over remaining object ids
        for j in range(i + 1, objects_num):

            # getting current object id/boundaries
            id_b = object_ids[j]
            boundaries_b = boundaries_dict[id_b]

            # checking cheap boundaries proximity pre-filter
            boundaries_close = get_boundaries_close_bool(boundaries_a=boundaries_a,
                                                         boundaries_b=boundaries_b,
                                                         margin=touch_margin)

            # skipping pair if bounding boxes are not even close
            if not boundaries_close:
                continue

            # getting pair union boundaries
            pair_boundaries = get_group_boundaries(boundaries_dict=boundaries_dict,
                                                   group={id_a, id_b})

            # cropping mask to pair union region
            pair_crop = crop_object(image=mask,
                                    boundaries=pair_boundaries,
                                    margin=touch_margin)

            # getting current pair object masks
            mask_a = get_bool_mask(mask=pair_crop, object_id=id_a)
            mask_b = get_bool_mask(mask=pair_crop, object_id=id_b)

            # checking whether objects touch
            objects_touch = get_objects_touch_bool(mask_a=mask_a,
                                                   mask_b=mask_b,
                                                   touch_margin=touch_margin)

            # updating touching graph
            if objects_touch:
                touching_graph[id_a].add(id_b)
                touching_graph[id_b].add(id_a)

    # returning touching graph
    return touching_graph


def get_merge_groups(touching_graph: dict) -> list:
    """
    Given a touching graph (adjacency
    dict), returns a list of merge
    candidate groups (connected
    components with more than one
    object id).

    Args:
        touching_graph (dict): A dictionary mapping each object id to the set of object ids it touches.

    Returns:
        list: The list of merge candidate groups (sets of object ids).
    """
    # defining placeholder for merge groups
    merge_groups = []

    # defining placeholder for visited object ids
    visited = set()

    # iterating over touching graph object ids
    for start_id in touching_graph:

        # skipping already visited object ids
        if start_id in visited:
            continue

        # defining placeholder for current group
        current_group = set()

        # defining placeholder for current queue
        current_queue = [start_id]

        # running breadth first search
        while current_queue:

            # popping current object id from queue
            current_id = current_queue.pop()

            # skipping already grouped object ids
            if current_id in current_group:
                continue

            # updating current group/visited
            current_group.add(current_id)
            visited.add(current_id)

            # getting current object id neighbors
            neighbors = touching_graph[current_id]

            # extending queue with unvisited neighbors
            current_queue.extend(neighbors - current_group)

        # getting current group size
        group_size = len(current_group)

        # checking if current group has more than one object id
        if group_size > 1:

            # appending current group to merge groups
            merge_groups.append(current_group)

    # returning merge groups
    return merge_groups


def get_group_solidity(mask: ndarray,
                       group: set,
                       boundaries_dict: dict,
                       scales_dict: dict,
                       margin: int = 3
                       ) -> tuple:
    """
    Given a mask and a group (set) of
    object ids, returns the solidity
    (mesh volume / convex hull volume)
    and the mesh volume (in cubic
    microns) of the union of these
    objects.

    Args:
        mask (ndarray): The segmentation mask.
        group (set): The set of object ids to compute solidity for.
        boundaries_dict (dict): A dictionary mapping each object id to its boundaries.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        margin (int): The margin (in pixels) to apply when cropping the mask.

    Returns:
        tuple: The group's (solidity, volume) tuple.
    """
    # getting group union boundaries
    group_boundaries = get_group_boundaries(boundaries_dict=boundaries_dict,
                                            group=group)

    # cropping mask to group union region
    group_crop = crop_object(image=mask,
                             boundaries=group_boundaries,
                             margin=margin)

    # defining placeholder for group boolean mask
    group_bool_mask = zeros_like(group_crop, dtype=bool)

    # iterating over group object ids
    for object_id in group:

        # updating group boolean mask
        group_bool_mask |= get_bool_mask(mask=group_crop,
                                         object_id=object_id)

    # getting group mesh
    vertices, faces = get_mesh(mask=group_bool_mask,
                               scales_dict=scales_dict)

    # getting group mesh triangles
    triangles = get_mesh_triangles(vertices=vertices,
                                   faces=faces)

    # getting group mesh tetrahedron volumes
    tetrahedron_volumes = get_tetrahedron_volumes(triangles=triangles)

    # getting group mesh polyhedron volume
    polyhedron_volume = get_polyhedron_volume(tetrahedron_volumes=tetrahedron_volumes)

    # getting group mesh volume
    volume = get_mesh_volume(polyhedron_volume=polyhedron_volume)

    # getting group mesh convex hull volume
    convex_hull_volume = get_convex_hull_volume(vertices=vertices)

    # getting group solidity
    solidity = get_solidity(volume=volume,
                            convex_hull_volume=convex_hull_volume)

    # assembling group metrics tuple
    group_metrics = (solidity, volume)

    # returning group metrics
    return group_metrics


def get_merge_candidates(mask: ndarray,
                         touch_margin: int = 1,
                         progress_tracker: ModuleProgressTracker | None = None
                         ) -> tuple:
    """
    Given a segmentation mask, returns
    its object ids, per-object
    boundaries, and merge candidate
    groups (connected components of
    touching objects with more than
    one member). This is the mesh-free
    (cheap) part of the merge_labels
    pipeline, factored out so exact
    iteration counts can also be
    obtained ahead of time (see
    merge_masks.ModuleProgressTracker).

    Args:
        mask (ndarray): The segmentation mask.
        touch_margin (int): The pixel margin within which objects are considered touching.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        tuple: The (object_ids, boundaries_dict, merge_groups) tuple.
    """
    # getting current mask object ids
    object_ids = get_object_ids(mask=mask)

    # getting current image object count (unique mask ids)
    objects_num = len(object_ids)

    # checking if progress tracker is not None
    if progress_tracker:

        # updating progress tracker attributes
        progress_tracker.objects_num = objects_num

        # resetting progress tracker attributes
        progress_tracker.current_object = 0

    # getting object bounding-box slices (single O(image_size) pass for all objects)
    object_slices = get_object_slices(mask=mask)

    # defining placeholder for boundaries dict
    boundaries_dict = {}

    # iterating over object ids (getting each object boundaries once)
    for object_id in object_ids:

        # checking if progress tracker is not None
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_object += 1
            progress_tracker.current_iteration += 1

        # getting current object boundaries directly from its bounding-box slice (tight, no full-array scan)
        boundaries_dict[object_id] = get_boundaries_from_slice(object_slice=object_slices[object_id])

    # building touching graph
    touching_graph = get_touching_graph(mask=mask,
                                        object_ids=object_ids,
                                        boundaries_dict=boundaries_dict,
                                        touch_margin=touch_margin)

    # getting merge candidate groups
    merge_groups = get_merge_groups(touching_graph=touching_graph)

    # assembling merge candidates tuple
    merge_candidates = (object_ids, boundaries_dict, merge_groups)

    # returning merge candidates
    return merge_candidates


def merge_labels(mask: ndarray,
                 scales_dict: dict,
                 solidity_threshold: float = 0.9,
                 touch_margin: int = 1,
                 expected_volume: float | None = None,
                 max_volume_ratio: float = 1.5,
                 progress_tracker: ModuleProgressTracker | None = None
                 ) -> ndarray:
    """
    Given a segmentation mask, detects
    groups of touching objects, and
    merges each group into a single
    object (using the minimum id in
    the group) if doing so results in
    a solid (convex) shape - the
    signature of an oversegmented
    single object, as opposed to
    multiple genuinely separate
    objects merely touching each other.
    If an expected volume is given,
    groups whose merged volume exceeds
    expected volume * max volume ratio
    are not merged (e.g. a merged volume
    of ~2x expected indicates a wrong merge).

    Args:
        mask (ndarray): The segmentation mask to merge objects in.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        solidity_threshold (float): The minimum solidity above which a group is merged.
        touch_margin (int): The pixel margin within which objects are considered touching.
        expected_volume (float | None): The expected volume (in cubic microns) of a single object (None disables the check).
        max_volume_ratio (float): The maximum merged volume / expected volume ratio allowed for a merge.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        ndarray: The mask with touching, solid object groups merged.
    """
    # defining placeholder value for merged mask
    merged_mask = mask.copy()

    # checking if progress tracker is not None
    if progress_tracker:

        # updating progress tracker attributes
        progress_tracker.current_operation = 'merge'

    # getting merge candidates (object ids, boundaries, touching groups)
    object_ids, boundaries_dict, merge_groups = get_merge_candidates(mask=mask,
                                                                     touch_margin=touch_margin,
                                                                     progress_tracker=progress_tracker)

    # iterating over merge candidate groups
    for group in merge_groups:

        # getting current group solidity (were it to be merged)
        group_solidity, group_volume = get_group_solidity(mask=mask,
                                                          group=group,
                                                          boundaries_dict=boundaries_dict,
                                                          scales_dict=scales_dict)

        # getting should merge bool
        should_merge = (group_solidity >= solidity_threshold)

        # checking if expected volume was given
        if expected_volume is not None:

            # rejecting merges resulting in volumes too large compared to expected
            should_merge &= (group_volume <= expected_volume * max_volume_ratio)

        # checking whether current group should be merged
        if not should_merge:

            # skipping
            continue

        # getting target id (minimum id in group)
        target_id = min(group)

        # iterating over group object ids
        for object_id in group:

            # skipping target id (nothing to reassign)
            if object_id == target_id:

                # skipping
                continue

            # reassigning current object id pixels to target id
            merged_mask[mask == object_id] = target_id

    # returning merged mask
    return merged_mask


def relabel_labels(mask: ndarray,
                   progress_tracker: ModuleProgressTracker | None = None
                   ) -> ndarray:
    """
    Given a segmentation mask, relabels
    object ids sequentially (1, 2, 3,
    ...), removing any gaps left by
    previous merging/filtering steps.

    Args:
        mask (ndarray): The segmentation mask to relabel.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        ndarray: The relabeled mask.
    """
    # defining placeholder value for relabeled mask
    relabeled_mask = zeros_like(mask)

    # getting current mask object ids
    object_ids = get_object_ids(mask=mask)

    # getting current image object count (unique mask ids)
    objects_num = len(object_ids)

    # checking if progress tracker is not None
    if progress_tracker:

        # updating progress tracker attributes
        progress_tracker.objects_num = objects_num
        progress_tracker.current_operation = 'relabel'

        # resetting progress tracker attributes
        progress_tracker.current_object = 0

    # iterating over object ids (enumerating from 1, in ascending id order) -
    # not counted towards iterations, the "graph" step already accounts for
    # virtually all the runtime
    for new_id, old_id in enumerate(object_ids, start=1):

        # checking if progress tracker is not None
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_object += 1

        # getting current object mask
        current_mask = get_bool_mask(mask=mask,
                                     object_id=old_id)

        # updating relabeled mask
        relabeled_mask[current_mask] = new_id

    # returning relabeled mask
    return relabeled_mask


def get_footprint(xy_radius: int,
                  z_radius: int
                  ) -> ndarray:
    """
    Given an xy/z radius pair, returns
    a boolean ellipsoid structuring
    element footprint.

    Args:
        xy_radius (int): The footprint's lateral (x/y) radius, in pixels.
        z_radius (int): The footprint's axial (z) radius, in pixels.

    Returns:
        ndarray: The boolean ellipsoid footprint.
    """
    z = arange(-z_radius, z_radius + 1)
    r = arange(-xy_radius, xy_radius + 1)

    # meshgrid: axes are (Z, Y, X)
    zz, yy, xx = meshgrid(z, r, r, indexing='ij')

    # Ellipsoid equation: (z/z_r)² + (y/r)² + (x/r)² <= 1
    ellipsoid = (zz / z_radius) ** 2 + (yy / xy_radius) ** 2 + (xx / xy_radius) ** 2

    # getting footprint
    footprint = (ellipsoid <= 1.0)

    # returning ellipsoid
    return footprint


def resize_labels(mask: ndarray,
                  scales_dict: dict,
                  distance: int = 1,
                  progress_tracker: ModuleProgressTracker | None = None
                  ) -> ndarray:
    """
    GPU optimized version of
    'expand_labels' function from
    scikit-image. Works both for
    dilation and erosion. If distance
    is positive, dilates, else, erodes.

    Args:
        mask (ndarray): The segmentation mask to resize objects in.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        distance (int): The distance to dilate (positive) or erode (negative) by.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        ndarray: The resized mask.
    """
    # defining placeholder value for resized mask
    resized_mask = mask.copy()

    # getting distances sign bool
    distance_is_positive = distance > 0

    # getting operation
    operation_str = ('dil' if distance_is_positive else 'ero')

    # getting absolute distance value (avoids issues with range in case of negative distances)
    distance_abs = abs(distance)

    # getting distances range
    distances_range = range(distance_abs)

    # getting current mask object ids
    object_ids = get_object_ids(mask=mask)

    # getting current image object count (unique mask ids)
    objects_num = len(object_ids)

    # getting footprint based on scales_dict
    xy_radius = 1

    # getting specific distance weights for each axis
    xy_scale = scales_dict['x']
    z_scale = scales_dict['z']

    # getting anisotropy
    anisotropy = (xy_scale / z_scale)

    # scaling z-axis closing radius
    z_radius = max(1, round(xy_radius * anisotropy))

    # getting footprint
    footprint = get_footprint(xy_radius=xy_radius,
                              z_radius=z_radius)

    # checking if progress tracker is not None
    if progress_tracker:

        # resetting progress tracker attributes
        progress_tracker.current_distance = 0

        # updating progress tracker attributes
        progress_tracker.objects_num = objects_num
        progress_tracker.current_operation = operation_str

    # iterating over distances
    for _ in distances_range:

        # checking if progress tracker is not None
        if progress_tracker:

            # resetting progress tracker attributes
            progress_tracker.current_object = 0

            # updating progress tracker attributes
            progress_tracker.current_distance += 1

        # iterating over object ids
        for object_id in object_ids:

            # checking if progress tracker is not None
            if progress_tracker:

                # updating progress tracker attributes
                progress_tracker.current_iteration += 1
                progress_tracker.current_object += 1

            # getting current object mask
            current_mask = get_bool_mask(mask=resized_mask,
                                         object_id=object_id)

            # getting current object undilated mask
            undilated_mask = current_mask.copy()

            # checking if distance is positive
            if distance_is_positive:

                # dilating current mask
                current_mask = binary_dilation(input=current_mask,
                                               structure=footprint)

                # getting masks difference
                masks_difference = (current_mask & (~undilated_mask))

                # getting current background pixels
                current_background = (resized_mask == 0)

                # updating dilated mask (only where there are no masks yet) - prevents overlaps!
                resized_mask[masks_difference & current_background] = object_id

            else:

                # eroding current mask
                current_mask = binary_erosion(input=current_mask,
                                              structure=footprint)

                # getting masks difference
                masks_difference = undilated_mask & (~current_mask)

                # updating dilated mask - enables touching borders erosion!
                resized_mask[masks_difference] = 0

    # returning dilated mask
    return resized_mask


def close_labels(mask: ndarray,
                 scales_dict: dict,
                 closing_radius: int,
                 progress_tracker: ModuleProgressTracker | None = None
                 ) -> ndarray:
    """
    Given a segmentation mask, closes
    small gaps in each object (binary
    closing followed by hole filling),
    using an anisotropy-scaled ellipsoid
    footprint.

    Args:
        mask (ndarray): The segmentation mask to close objects in.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        closing_radius (int): The lateral (x/y) radius of the closing footprint, in pixels.
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        ndarray: The mask with closed objects.
    """
    # getting specific distance weights for each axis
    xy_scale = scales_dict['x']
    z_scale = scales_dict['z']

    # getting anisotropy
    anisotropy = (xy_scale / z_scale)

    # scaling z-axis closing radius
    z_radius = max(1, round(closing_radius * anisotropy))

    # getting footprint
    footprint = get_footprint(xy_radius=closing_radius,
                              z_radius=z_radius)

    # defining placeholder value for closed mask
    closed_mask = zeros_like(mask)

    # getting current mask object ids
    object_ids = get_object_ids(mask=mask)

    # getting current image object count (unique mask ids)
    objects_num = len(object_ids)

    # checking if progress tracker is not None
    if progress_tracker:

        # updating progress tracker attributes
        progress_tracker.objects_num = objects_num

        # resetting progress tracker attributes
        progress_tracker.current_object = 0

    # iterating over object ids
    for object_id in object_ids:

        # checking if progress tracker is not None
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_object += 1

        # getting current object mask
        current_mask = get_bool_mask(mask=mask,
                                     object_id=object_id)

        # running closing step
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_operation = 'close'
            progress_tracker.current_iteration += 1

        # applying binary closing
        current_mask = binary_closing(input=current_mask,
                                      structure=footprint)

        # running fill holes step
        if progress_tracker:

            # updating progress tracker attributes
            progress_tracker.current_operation = 'fill'
            progress_tracker.current_iteration += 1

        # filling remaining interior holes
        current_mask = binary_fill_holes(input=current_mask)

        # updating closed mask
        closed_mask[current_mask] = object_id

    # returning closed mask
    return closed_mask


def validate_min_boundary(value: int,
                          axis_min: int
                          ) -> int:
    """
    Given a min boundary value, and
    respective axis minimum, returns
    valid boundary value.

    Args:
        value (int): The candidate minimum boundary value.
        axis_min (int): The axis' minimum valid value.

    Returns:
        int: The validated minimum boundary value.
    """
    # defining placeholder value for valid value
    valid_value = copy(value)

    # if value is smaller than axis min
    if value < axis_min:

        # setting valid value as axis min
        valid_value = axis_min

    # returning valid value
    return valid_value


def validate_max_boundary(value: int,
                          axis_max: int
                          ) -> int:
    """
    Given a max boundary value, and
    respective axis maximum, returns
    valid boundary value.

    Args:
        value (int): The candidate maximum boundary value (-1 encodes the axis maximum).
        axis_max (int): The axis' maximum valid value.

    Returns:
        int: The validated maximum boundary value.
    """
    # defining placeholder value for valid value
    valid_value = copy(value)

    # if value is -1 (encodes for maximum dimension)
    if value == -1:

        # setting valid value as axis min
        valid_value = axis_max

    # if value is greater than axis max
    elif value > axis_max:

        # setting valid value as axis max
        valid_value = axis_max

    # returning valid value
    return valid_value


def crop_object(image: ndarray,
                boundaries: tuple,
                margin: int
                ) -> ndarray:
    """
    Given a loaded image, and crop
    boundaries, validates boundaries
    and returns cropped image.

    Args:
        image (ndarray): The image to crop.
        boundaries (tuple): The (z_min, z_max, y_min, y_max, x_min, x_max) crop boundaries.
        margin (int): The margin to add around the given boundaries.

    Returns:
        ndarray: The cropped image.
    """
    # getting current image shape
    image_shape = image.shape

    # extracting coords from boundaries
    z_min, z_max, y_min, y_max, x_min, x_max = boundaries

    # adding margins (only if not set to max)
    z_min -= margin
    y_min -= margin
    x_min -= margin
    if z_max != -1:
        z_max += margin
    if y_max != -1:
        y_max += margin
    if x_max != -1:
        x_max += margin

    # getting dimensions num
    dimensions_num = image.ndim

    # checking dimensions num

    # multi-channel image (ZYXC)
    if dimensions_num == 4:

        # getting axis valid values
        z_axis_min = 0
        z_axis_max = image_shape[0]
        y_axis_min = 0
        y_axis_max = image_shape[1]
        x_axis_min = 0
        x_axis_max = image_shape[2]

        # validating boundaries
        z_min = validate_min_boundary(value=z_min, axis_min=z_axis_min)
        z_max = validate_max_boundary(value=z_max, axis_max=z_axis_max)
        y_min = validate_min_boundary(value=y_min, axis_min=y_axis_min)
        y_max = validate_max_boundary(value=y_max, axis_max=y_axis_max)
        x_min = validate_min_boundary(value=x_min, axis_min=x_axis_min)
        x_max = validate_max_boundary(value=x_max, axis_max=x_axis_max)

        # cropping image
        image_crop = image[z_min:z_max,  # z slices selection
                           y_min:y_max,  # y slices selection
                           x_min:x_max,  # x slices selection
                           :]            # all channels

    # single-channel image (ZYX)
    elif dimensions_num == 3:

        # getting axis valid values
        z_axis_min = 0
        z_axis_max = image_shape[0]
        y_axis_min = 0
        y_axis_max = image_shape[1]
        x_axis_min = 0
        x_axis_max = image_shape[2]

        # validating boundaries
        z_min = validate_min_boundary(value=z_min, axis_min=z_axis_min)
        z_max = validate_max_boundary(value=z_max, axis_max=z_axis_max)
        y_min = validate_min_boundary(value=y_min, axis_min=y_axis_min)
        y_max = validate_max_boundary(value=y_max, axis_max=y_axis_max)
        x_min = validate_min_boundary(value=x_min, axis_min=x_axis_min)
        x_max = validate_max_boundary(value=x_max, axis_max=x_axis_max)

        # cropping image
        image_crop = image[z_min:z_max,  # z slices selection
                           y_min:y_max,  # y slices selection
                           x_min:x_max]  # x slices selection

    # single-channel (2d projection)
    else:

        # getting axis valid values
        y_axis_min = 0
        y_axis_max = image_shape[0]
        x_axis_min = 0
        x_axis_max = image_shape[1]

        # validating boundaries
        y_min = validate_min_boundary(value=y_min, axis_min=y_axis_min)
        y_max = validate_max_boundary(value=y_max, axis_max=y_axis_max)
        x_min = validate_min_boundary(value=x_min, axis_min=x_axis_min)
        x_max = validate_max_boundary(value=x_max, axis_max=x_axis_max)

        # cropping image
        image_crop = image[y_min:y_max,  # y slices selection
                           x_min:x_max]  # x slices selection

    # returning crop
    return image_crop

######################################################################
# end of current module
