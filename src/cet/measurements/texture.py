# texture measurements module

# Code destined to storing texture
# measurements related operations.

######################################################################
# imports

from cet.config import GPU
from cet.gpu.device import transfer_from_gpu
from cet.dataframes.df_ops import get_column_name
from mahotas.features.texture import haralick_labels
from cet.preprocessing.image_ops import rescale_image
from mahotas.features.texture import haralick_features  # noqa
from cet.measurements.position import get_pixel_coords
from cet.progress_tracker.ProgressTracker import ProgressTracker

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import add
    from cupy import full
    from cupy import zeros
    from cupy import array
    from cupy import ndarray
    from cupyx import scatter_add
    from cupy import sum as arr_sum
else:
    from numpy import add
    from numpy import full
    from numpy import zeros
    from numpy import array
    from numpy import ndarray
    from numpy import sum as arr_sum

######################################################################
# defining global varibales

HARALICK_LABELS = haralick_labels[:13]  # excludes 'Maximal Correlation Coefficient' (compute_14th_feature=False below)

######################################################################
# progress tracking related classes


class ModuleProgressTracker(ProgressTracker):
    """
    Defines ModuleProgressTracker class.

    Structural stand-in used only to type-hint the optional progress_tracker
    param below (this module stays a plain function library - see CODE_CONVENTIONS.md -
    so this class is never instantiated or run here; callers pass in their own
    module's ModuleProgressTracker instance, which duck-types against it).
    """
    # defining ProgressTracker init
    def __init__(self) -> None:
        """
        Initializes a ModuleProgressTracker
        instance and defines class attributes.
        """
        # inheriting attributes and methods from ProgressTracker
        super().__init__()

        # defining current module specific attributes

        # measurement
        self.measurements_num = 0
        self.current_measurement = 0

######################################################################
# defining auxiliary functions


def glcm2d(image: ndarray,
           mask: ndarray,
           offset: tuple,
           levels: int,
           coords: tuple | None = None
           ) -> ndarray:
    """
    Returns gray level cooccurrence matrix
    for a 2D image.

    Args:
        image (ndarray): The 2D image.
        mask (ndarray): The region mask.
        offset (tuple): The offset to apply.
        levels (int): Number of gray levels.
        coords (tuple): Precomputed mask pixel coords (ys, xs), to avoid
            recomputing them for every offset. Computed from mask if not given.

    Returns:
        ndarray: The GLCM matrix.
    """
    # getting current image shape
    image_shape = image.shape

    # getting axis valid values
    y_axis_min = 0
    y_axis_max = image_shape[0]
    x_axis_min = 0
    x_axis_max = image_shape[1]

    # defining increment
    increment = 1

    # defining levels shape
    levels_shape = (levels, levels)

    # defining placeholder value for glcm
    glcm = zeros(shape=levels_shape,
                 dtype='uint16')

    # getting current image valid coords (reusing precomputed coords if given)
    if coords is None:
        coords = get_pixel_coords(mask=mask)

    # extracting coords from tuple
    ys, xs = coords

    # extracting coords from tuple
    offset_y, offset_x = offset

    # getting array shape
    arr_shape = len(ys)

    # assembling coords arrays
    ys_add = full(shape=arr_shape, fill_value=offset_y)
    xs_add = full(shape=arr_shape, fill_value=offset_x)

    # getting current offsets arrays
    offset_ys = ys + ys_add
    offset_xs = xs + xs_add

    # defining filters (strict "<" upper bound: an offset index equal to the axis size is always
    # out of bounds - the previous per-pixel "<=" + try/except version reached the same outcome,
    # since indexing at exactly the axis size always raised IndexError and was skipped)
    y_filter = (offset_ys >= y_axis_min) & (offset_ys < y_axis_max)
    x_filter = (offset_xs >= x_axis_min) & (offset_xs < x_axis_max)
    offset_filter = (y_filter & x_filter)

    # applying filter to coords/offsets array
    ys = ys[offset_filter]
    xs = xs[offset_filter]
    offset_ys = offset_ys[offset_filter]
    offset_xs = offset_xs[offset_filter]

    # assembling coords/offset tuple
    coords = (ys, xs)
    offset_coords = (offset_ys, offset_xs)

    # converting data types
    coords = array(coords)
    offset_coords = array(offset_coords)

    # converting data types
    coords = tuple(coords)
    offset_coords = tuple(offset_coords)

    # getting pixel/mask values
    coords_values = image[coords]
    offset_values = image[offset_coords]
    mask_values = mask[offset_coords]

    # getting mask filter
    mask_filter = (mask_values > 0)

    # applying filter to coords/offsets values
    coords_values = coords_values[mask_filter]
    offset_values = offset_values[mask_filter]

    # converting data types
    coords_values = coords_values.astype('uint16')
    offset_values = offset_values.astype('uint16')

    # checking whether array is in gpu ram
    if GPU:

        # updating glcm (both ways since always symmetric to calculate haralick anyways)
        scatter_add(glcm, (coords_values, offset_values), increment)
        scatter_add(glcm, (offset_values, coords_values), increment)

    else:

        # updating glcm (both ways since always symmetric to calculate haralick anyways)
        add.at(glcm, (coords_values, offset_values), increment)  # noqa
        add.at(glcm, (offset_values, coords_values), increment)  # noqa

    # returning glcm
    return glcm


def glcm3d(image: ndarray,
           mask: ndarray,
           offset: tuple,
           levels: int,
           coords: tuple | None = None
           ) -> ndarray:
    """
    Returns gray level cooccurrence matrix
    for a 3D image.

    Args:
        image (ndarray): The 3D image.
        mask (ndarray): The region mask.
        offset (tuple): The offset to apply.
        levels (int): Number of gray levels.
        coords (tuple): Precomputed mask pixel coords (zs, ys, xs), to avoid
            recomputing them for every offset. Computed from mask if not given.

    Returns:
        ndarray: The GLCM matrix.
    """
    # getting current image shape
    image_shape = image.shape

    # getting axis valid values
    z_axis_min = 0
    z_axis_max = image_shape[0]
    y_axis_min = 0
    y_axis_max = image_shape[1]
    x_axis_min = 0
    x_axis_max = image_shape[2]

    # defining increment
    increment = 1

    # defining levels shape
    levels_shape = (levels, levels)

    # defining placeholder value for glcm
    glcm = zeros(shape=levels_shape,
                 dtype='uint32')

    # getting current image valid coords (reusing precomputed coords if given)
    if coords is None:
        coords = get_pixel_coords(mask=mask)

    # extracting coords from tuple
    zs, ys, xs = coords

    # extracting coords from tuple
    offset_z, offset_y, offset_x = offset

    # getting array shape
    arr_shape = len(zs)

    # assembling coords arrays
    zs_add = full(shape=arr_shape, fill_value=offset_z)
    ys_add = full(shape=arr_shape, fill_value=offset_y)
    xs_add = full(shape=arr_shape, fill_value=offset_x)

    # getting current offsets arrays
    offset_zs = zs + zs_add
    offset_ys = ys + ys_add
    offset_xs = xs + xs_add

    # defining filters
    z_filter = (offset_zs >= z_axis_min) & (offset_zs < z_axis_max)
    y_filter = (offset_ys >= y_axis_min) & (offset_ys < y_axis_max)
    x_filter = (offset_xs >= x_axis_min) & (offset_xs < x_axis_max)
    offset_filter = (z_filter & y_filter & x_filter)

    # applying filter to coords/offsets array
    zs = zs[offset_filter]
    ys = ys[offset_filter]
    xs = xs[offset_filter]
    offset_zs = offset_zs[offset_filter]
    offset_ys = offset_ys[offset_filter]
    offset_xs = offset_xs[offset_filter]

    # assembling coords/offset tuple
    coords = (zs, ys, xs)
    offset_coords = (offset_zs, offset_ys, offset_xs)

    # converting data types
    coords = array(coords)
    offset_coords = array(offset_coords)

    # converting data types
    coords = tuple(coords)
    offset_coords = tuple(offset_coords)

    # getting pixel/mask values
    coords_values = image[coords]
    offset_values = image[offset_coords]
    mask_values = mask[offset_coords]

    # getting mask filter
    mask_filter = (mask_values > 0)

    # applying filter to coords/offsets values
    coords_values = coords_values[mask_filter]
    offset_values = offset_values[mask_filter]

    # converting data types
    coords_values = coords_values.astype('uint32')
    offset_values = offset_values.astype('uint32')

    # checking whether array is in gpu ram
    if GPU:

        # updating glcm (both ways since always symmetric to calculate haralick anyways)
        scatter_add(glcm, (coords_values, offset_values), increment)
        scatter_add(glcm, (offset_values, coords_values), increment)

    else:

        # updating glcm (both ways since always symmetric to calculate haralick anyways)
        add.at(glcm, (coords_values, offset_values), increment)  # noqa
        add.at(glcm, (offset_values, coords_values), increment)  # noqa

    # returning glcm
    return glcm


def normalize_glcm(glcm: ndarray) -> ndarray:
    """
    Returns a normalized GLCM by
    converting counts to ratios.

    Args:
        glcm (ndarray): The count GLCM.

    Returns:
        ndarray: The normalized GLCM.
    """
    # getting current glcm total
    total = arr_sum(glcm)

    # converting data types
    glcm = glcm.astype('float64')
    total = total.astype('uint64')

    # normalizing values
    try:
        glcm /= total
    except ZeroDivisionError:
        return glcm

    # returning normalized glcm
    return glcm


def get_haralick_features(image: ndarray,
                          mask: ndarray,
                          levels: int,
                          distances: list,
                          intensity_range: tuple | None = None,
                          progress_tracker: ModuleProgressTracker | None = None
                          ) -> dict:
    """
    Returns haralick features computed at
    each given pixel distance.

    Args:
        image (ndarray): The input image.
        mask (ndarray): The region mask.
        levels (int): Number of gray levels.
        distances (list): The pixel distances.
        intensity_range (tuple | None): Optional fixed (low, high) intensity range used to bin gray levels (per-image min/max if None).
        progress_tracker (ModuleProgressTracker | None): Optional progress tracker instance.

    Returns:
        dict: Features by distance.
    """
    # getting dimensions num
    dimensions_num = image.ndim

    # defining placeholder value for features by distance dict
    features_by_distance = {}

    # getting max value
    max_value = (levels - 1)

    # rescaling image (fixed intensity range if given, so that gray levels mean the same
    # thing across objects; otherwise min-max over the full array passed in, which may
    # include margin pixels outside mask)
    image = rescale_image(image=image,
                          max_value=max_value,
                          input_range=intensity_range)

    # getting image is 3d bool
    image_is_3d = (dimensions_num == 3)

    # checking dimensions num

    # 3d image (ZYX)
    if image_is_3d:

        # defining base (unit distance) offsets
        base_offsets = [(-1, 0, 1),
                        (-1, 1, -1),
                        (-1, 1, 0),
                        (-1, 1, 1),
                        (0, 0, 1),
                        (0, 1, -1),
                        (0, 1, 0),
                        (0, 1, 1),
                        (1, 0, 0),
                        (1, 0, 1),
                        (1, 1, -1),
                        (1, 1, 0),
                        (1, 1, 1)]

        # defining glcm func
        func = glcm3d

    # 2d image (YX)
    else:

        # defining base (unit distance) offsets
        base_offsets = [(0, 1),
                        (1, 1),
                        (1, 0),
                        (1, -1)]

        # defining glcm func
        func = glcm2d

    # getting mask pixel coords once, reused across all offsets/distances (both 2d and 3d)
    mask_coords = get_pixel_coords(mask=mask)

    # defining placeholder value for all glcms (flat across every distance/offset, batched
    # into a single haralick_features call below) and their per-distance group sizes
    all_glcms = []
    offsets_per_distance = []

    # iterating over distances
    for distance in distances:

        # scaling base offsets to current distance
        offsets = [tuple(axis * distance for axis in offset) for offset in base_offsets]

        # getting offsets num
        offsets_num = len(offsets)

        # iterating over offsets
        for offset in offsets:

            # getting current offset glcm (glcm2d/glcm3d share the same call signature)
            current_glcm = func(image=image,
                                mask=mask,
                                offset=offset,
                                levels=levels,
                                coords=mask_coords)

            # normalizing glcm
            current_glcm = normalize_glcm(glcm=current_glcm)

            # checking whether array is in gpu ram
            if GPU:

                # transferring array from gpu
                current_glcm = transfer_from_gpu(arr=current_glcm)

            # appending current glcm to all glcms list (kept flat; grouped back by distance below)
            all_glcms.append(current_glcm)

            # checking whether progress tracker was given
            if progress_tracker:

                # updating progress tracker attributes
                progress_tracker.current_iteration += 1
                progress_tracker.current_measurement += 1

        # recording current distance's offset count (to split the batched features back out below)
        offsets_per_distance.append(offsets_num)

    # getting features for every glcm (every distance/offset) in a single batched call (skipping
    # 14th feature: eigendecomposition-based, expensive and prone to LinAlgError non-convergence
    # on degenerate GLCMs)
    all_features = haralick_features(cmats=all_glcms,
                                     compute_14th_feature=False)

    # defining current slice start index
    slice_start = 0

    # iterating over distances/offset-counts to split batched features back into groups
    for distance, offset_count in zip(distances, offsets_per_distance):

        # getting current distance's slice end index
        slice_end = (slice_start + offset_count)

        # slicing current distance's features out of the batched features array
        features = all_features[slice_start:slice_end]

        # updating features by distance dict
        features_by_distance[distance] = features

        # updating current slice start index
        slice_start = slice_end

    # returning features by distance dict
    return features_by_distance


def get_features_dict(features_arr: ndarray) -> dict:
    """
    Returns a labeled features dictionary
    from haralick features.

    Args:
        features_arr (ndarray): The haralick features array.

    Returns:
        dict: The labeled features dictionary.
    """
    # defining placeholder value for features dict
    features_dict = {}

    # getting features label/value zip
    label_value_zip = zip(HARALICK_LABELS, features_arr)

    # iterating over label/value zip
    for label_value in label_value_zip:

        # extracting values from tuple
        label, value = label_value

        # updating label name
        label = get_column_name(label=label)

        # assembling current dict
        current_dict = {label: value}

        # updating features dict
        features_dict.update(current_dict)

    # returning features dict
    return features_dict

######################################################################
# end of current module
