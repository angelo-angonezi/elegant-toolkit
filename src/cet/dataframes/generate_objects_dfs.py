# generate objects dfs module

print('initializing...')  # noqa

# Code destined to generating
# per object dataframe.

######################################################################
# imports

print('importing required libraries...')  # noqa
from os.path import join
from cet.config import GPU
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.images import load_image
from cet.io.dataframes import save_df
from cet.io.cli import get_scales_dict
from cet.io.files import get_crop_name
from cet.io.cli import get_channels_dict
from cet.io.cli import get_distances_list
from cet.io.cli import sort_channels_dict
from cet.measurements.mesh import get_mesh
from cet.measurements.labels import get_uid
from cet.io.files import get_skip_file_bool
from cet.io.formatting import get_digits_num
from cet.io.files import get_files_in_folder
from cet.constants import DEFAULT_SCALES_STR
from cet.measurements.mesh import taubin_smooth
from cet.measurements.mesh import get_mesh_volume
from cet.segmentation.mask_ops import crop_object
from cet.measurements.labels import get_object_ids
from cet.measurements.position import offset_coords
from cet.segmentation.mask_ops import get_bool_mask
from cet.measurements.mesh import get_mesh_triangles
from cet.measurements.intensity import get_measurement
from cet.measurements.position import coords_to_string
from cet.measurements.position import string_to_coords
from cet.measurements.texture import get_features_dict
from cet.measurements.morphology import get_sphericity
from cet.measurements.position import get_pixel_coords
from cet.measurements.mesh import get_polyhedron_volume
from cet.measurements.mesh import get_mesh_surface_area
from cet.segmentation.mask_ops import get_object_slices
from cet.measurements.position import get_bounding_shape
from cet.measurements.morphology import get_pixel_volume
from cet.measurements.position import get_pixel_centroid
from cet.measurements.morphology import get_radius_ratio
from cet.measurements.mesh import get_tetrahedron_volumes
from cet.measurements.texture import get_haralick_features
from cet.measurements.morphology import get_volume_radius
from cet.measurements.morphology import get_area_vol_ratio
from cet.measurements.morphology import get_bounding_volume
from cet.segmentation.mask_ops import get_border_pixel_count
from cet.segmentation.mask_ops import get_touches_border_bool
from cet.measurements.position import get_boundaries_from_slice
from cet.segmentation.mask_ops import get_image_boundaries_mask
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.dataframes.df_ops import filter_pandas_performance_warnings

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import ndarray
    from cupy import count_nonzero
    from cupy import mean as arr_mean
else:
    from numpy import ndarray
    from numpy import count_nonzero
    from numpy import mean as arr_mean

print('all required libraries successfully imported.')  # noqa

# filtering Pandas Performance Warnings
filter_pandas_performance_warnings()

######################################################################
# defining global varibales

_INTENSITY_MEASUREMENTS = ['mean',
                           'median',
                           'mode',
                           'std',
                           'sum',
                           'min',
                           'max',
                           'q01',
                           'q05',
                           'q10',
                           'q25',
                           'q50',
                           'q75',
                           'q90',
                           'q95',
                           'q99']

_OVERLAP_MEASUREMENTS = ['pixels',
                         'fraction']

######################################################################
# argument parsing related functions


def get_args_dict() -> dict:
    """
    Parses command-line arguments and returns
    them as a dictionary.

    Returns:
        dict: A dictionary containing all parsed command-line arguments.
    """
    # defining program description
    description = "generate objects dfs module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing segmentation masks [.tif]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain objects dfs [.csv])')

    # channels param
    parser.add_argument('-c', '--channels',
                        dest='channels',
                        type=str,
                        required=False,
                        default=None,
                        help='defines a "dictionary" of structure ch_name_1#measurement@ch_path_1,ch_name_2#measurement@ch_path_2 for additional channels to be analysed')

    # haralick distances param
    parser.add_argument('-hd', '--haralick-distances',
                        dest='haralick_distances',
                        type=str,
                        required=False,
                        default='1',
                        help='defines a comma-separated list of pixel distances at which to compute haralick texture features (e.g. "1,2,3")')

    # haralick range param
    parser.add_argument('-hr', '--haralick-range',
                        dest='haralick_range',
                        type=str,
                        required=False,
                        default=None,
                        help='defines a "(low,high)" intensity range, fixed for all objects, used to bin gray levels for haralick texture features (e.g. "(0,4000)"; applies to all texture channels; uses each object crop\'s own min/max if omitted)')

    # description param
    parser.add_argument('-p', '--description',
                        dest='description',
                        type=str,
                        required=False,
                        default='obj',
                        help='defines a constant value to be placed in a "description" column')

    # scales dict param
    parser.add_argument('-sd', '--scales-dict',
                        dest='scales_dict',
                        type=str,
                        required=False,
                        default=DEFAULT_SCALES_STR,
                        help='defines a "dictionary" of structure x=x_scale,y=y_scale,z=z_scale for scales (in microns) for each channel')

    # smooth mesh iterations param
    parser.add_argument('-smi', '--smooth-mesh-iterations',
                        dest='smooth_mesh_iterations',
                        type=int,
                        required=False,
                        default=-1,
                        help='defines number of iterations for smoothing meshes (turn off with -1)')

    # skip positional param
    parser.add_argument('-sp', '--skip-positional',
                        dest='skip_positional',
                        action='store_true',
                        required=False,
                        help='defines whether to skip positional measurements (centroid, boundaries, border info)')

    # skip morphological param
    parser.add_argument('-sm', '--skip-morphological',
                        dest='skip_morphological',
                        action='store_true',
                        required=False,
                        help='defines whether to skip morphological measurements (volume, sphericity, etc.)')

    # overwrite output param
    parser.add_argument('-ow', '--overwrite-output',
                        dest='overwrite_output',
                        action='store_true',
                        required=False,
                        help='defines whether overwrite files in output folder (skips existing output by default)')

    # skip enter param
    parser.add_argument('-s', '--skip-enter',
                        dest='skip_enter',
                        action='store_true',
                        required=False,
                        help='defines whether to suppress "Enter to continue" input before execution')

    # creating arguments dictionary
    args_dict = vars(parser.parse_args())

    # returning the arguments dictionary
    return args_dict

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

        # defining current module specific attributes

        # df being currently built (index, positional, morphology, id, intensity, texture, or overlap)
        self.df_name = ''

        # image
        self.images_num = 0
        self.current_image = 0

        # object
        self.objects_num = 0
        self.current_object = 0

        # channel
        self.channels_num = 0
        self.current_channel = 0

        # measurement
        self.measurements_num = 0
        self.current_measurement = 0

        # iterations dict
        self.iterations_dict = {}

    # overwriting class methods (using current module specific attributes)

    def get_progress_string(self) -> str:
        """
        Returns a formatted progress
        string, based on current progress
        attributes.

        Returns:
            str: The current progress string.
        """
        # assembling current progress string
        progress_string = f''

        # checking if iterations total has already been obtained

        # if totals are still being updated
        if not self.totals_updated.is_set():

            # updating progress string based on attributes
            progress_string += f'calculating totals...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | images: {self.images_num}'
            progress_string += f' | channels: {self.channels_num}'
            progress_string += f' | objects: {self.objects_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'generating dfs...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | df: {self.df_name}'
            progress_string += f' | image: {self.current_image}/{self.images_num}'
            progress_string += f' | channel: {self.current_channel}/{self.channels_num}'
            progress_string += f' | object: {self.current_object}/{self.objects_num}'
            progress_string += f' | measurement: {self.current_measurement}/{self.measurements_num}'
            progress_string += f' | progress: {self.progress_percentage_str}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'
            progress_string += f' | ETC: {self.etc_str}'

        # returning progress string
        return progress_string

    def update_totals(self,
                      args_dict: dict
                      ) -> None:
        """
        Implements module specific method
        to update total iterations num.

        Args:
            args_dict (dict): A dictionary containing all parsed command-line arguments.

        Returns:
            None.
        """
        # getting input folder
        input_folder = args_dict['input_folder']

        # getting channels
        channels = args_dict['channels']

        # getting haralick distances
        haralick_distances = args_dict['haralick_distances']

        # getting skip positional bool
        skip_positional = args_dict['skip_positional']

        # getting skip morphological bool
        skip_morphological = args_dict['skip_morphological']

        # getting channels dict
        channels_dict = get_channels_dict(channels_str=channels)

        # sorting channels dict by path
        channels_dict = sort_channels_dict(channels_dict=channels_dict)

        # getting haralick distances list
        haralick_distances_list = get_distances_list(distances=haralick_distances)

        # getting dict items
        dict_items = channels_dict.items()

        # getting channels count
        channels_num = len(dict_items)

        # updating progress tracker attributes
        self.channels_num = channels_num

        # getting images
        images = get_files_in_folder(input_folder=input_folder,
                                     extension='.tif')

        # iterating over files
        for image_name in images:

            # updating progress tracker attributes
            self.images_num += 1

            # defining placeholder value for current iterations dict
            current_iterations_dict = {image_name: 0}

            # getting current image path
            input_path = join(input_folder,
                              image_name)

            # loading current mask
            mask = load_image(input_path=input_path)

            # getting current mask object ids
            object_ids = get_object_ids(mask=mask)

            # getting current image object count (unique mask ids)
            objects_num = len(object_ids)

            # getting mask is 3d bool (determines haralick offsets count per distance: 13 for 3d, 4 for 2d -
            # mirrors get_haralick_features's own image_is_3d check, duplicated here rather than shared,
            # since update_totals must never share state with the real per-image run)
            mask_is_3d = (mask.ndim == 3)
            haralick_offsets_per_distance = (13 if mask_is_3d else 4)

            # getting current image object range
            objects_range = range(objects_num)

            # getting base dfs per object count (index, plus positional/morphological unless skipped)
            base_dfs_num = 1

            # checking skip positional flag
            if not skip_positional:

                # updating base dfs num
                base_dfs_num += 1

            # checking skip morphological flag
            if not skip_morphological:

                # updating base dfs num
                base_dfs_num += 1

            # iterating over objects
            for _ in objects_range:

                # updating progress tracker attributes
                self.objects_num += 1

                # iterating over base dfs (one iteration per object per df)
                for _ in range(base_dfs_num):

                    # updating progress tracker attributes (base dfs features, per object)
                    self.iterations_num += 1

                    # updating current iterations dict
                    current_iterations_dict[image_name] += 1

            # iterating over dict items
            for channel_item in dict_items:

                # getting current key/value
                channel_prefix, channel_path = channel_item

                # getting current channel split
                channel_split = channel_prefix.split('#')

                # getting current channel name/measurement
                channel_name, measurement = channel_split

                # getting measurement is intensity/texture bools
                measurement_is_id = (measurement == 'id')
                measurement_is_intensity = (measurement == 'intensity')
                measurement_is_texture = (measurement == 'texture')
                measurement_is_overlap = (measurement == 'overlap')

                # checking whether measurement is id
                if measurement_is_id:

                    # updating progress tracker attributes
                    self.measurements_num += 1

                    # iterating over objects
                    for _ in objects_range:

                        # updating progress tracker attributes (additional id features, per object)
                        self.iterations_num += 1

                        # updating current iterations dict
                        current_iterations_dict[image_name] += 1

                # checking whether measurement is intensity
                elif measurement_is_intensity:

                    # iterating over measurements list
                    for _ in _INTENSITY_MEASUREMENTS:  # (one extra loop for background measurements)

                        # updating progress tracker attributes (additional intensity features, per image)
                        self.measurements_num += 1
                        self.iterations_num += 1

                        # updating current iterations dict
                        current_iterations_dict[image_name] += 1

                    # iterating over intensity, bg removed, and bg normalized passes (each one iteration
                    # per measurement per object)
                    for _ in range(3):

                        # iterating over measurements list
                        for _ in _INTENSITY_MEASUREMENTS:

                            # updating progress tracker attributes
                            self.measurements_num += 1

                            # iterating over objects
                            for _ in objects_range:

                                # updating progress tracker attributes (additional intensity features, per object)
                                self.iterations_num += 1

                                # updating current iterations dict
                                current_iterations_dict[image_name] += 1

                # checking whether measurement is texture
                elif measurement_is_texture:

                    # iterating over haralick distances
                    for _ in haralick_distances_list:

                        # iterating over haralick offsets (true unit of work per distance)
                        for _ in range(haralick_offsets_per_distance):

                            # updating progress tracker attributes
                            self.measurements_num += 1

                            # iterating over objects
                            for _ in objects_range:

                                # updating progress tracker attributes (additional texture features, per object)
                                self.iterations_num += 1

                                # updating current iterations dict
                                current_iterations_dict[image_name] += 1

                # checking whether measurement is overlap
                elif measurement_is_overlap:

                    # iterating over overlap measurements (pixels count, fraction)
                    for _ in _OVERLAP_MEASUREMENTS:

                        # updating progress tracker attributes
                        self.measurements_num += 1

                        # iterating over objects
                        for _ in objects_range:

                            # updating progress tracker attributes (additional overlap features, per object)
                            self.iterations_num += 1

                            # updating current iterations dict
                            current_iterations_dict[image_name] += 1

            # updating progress tracker attributes
            self.iterations_dict.update(current_iterations_dict)

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | channels: {self.channels_num}'
        totals_string += f' | objects: {self.objects_num}'
        totals_string += f' | measurements: {self.measurements_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_index_dict(image_name: str,
                   image_index: int,
                   description: str,
                   object_id: int,
                   object_digits_num: int,
                   progress_tracker: ModuleProgressTracker
                   ) -> dict:
    """
    Given an object metadata,
    returns index dict.

    Args:
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        description (str): The object's description label.
        object_id (int): The object's id.
        object_digits_num (int): The number of digits to zero-pad the object id with.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The object's index dict.
    """
    # updating progress tracker attributes
    progress_tracker.current_iteration += 1
    progress_tracker.current_measurement += 1

    # getting object uid
    object_uid = get_uid(image_index=image_index,
                         description=description,
                         object_id=object_id)

    # getting crop name
    crop_name = get_crop_name(image_name=image_name,
                              description=description,
                              object_id=object_id,
                              digits=object_digits_num)

    # assembling index dict
    index_dict = {'image_name': image_name,
                  'image_index': image_index,
                  'description': description,
                  'object_id': object_id,
                  'uid': object_uid,
                  'crop_name': crop_name}

    # returning index dict
    return index_dict


def get_index_df(image_name: str,
                 image_index: int,
                 description: str,
                 object_slices: dict,
                 object_digits_num: int,
                 progress_tracker: ModuleProgressTracker
                 ) -> DataFrame:
    """
    Given per-object bounding-box slices,
    iterates over object ids, and returns
    a per object index df.

    Args:
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        description (str): The objects' description label.
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        object_digits_num (int): The number of digits to zero-pad the object id with.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The per-object index df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'index'

    # updating progress tracker attributes
    progress_tracker.measurements_num = 1

    # defining placeholder value for dicts list
    dicts_list = []

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # getting current object ids
    object_ids = object_slices.keys()

    # iterating over object ids
    for object_id in object_ids:

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object index dict
        current_dict = get_index_dict(image_name=image_name,
                                      image_index=image_index,
                                      description=description,
                                      object_id=object_id,
                                      object_digits_num=object_digits_num,
                                      progress_tracker=progress_tracker)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling index df from dicts list
    index_df = DataFrame(dicts_list)

    # returning index df
    return index_df


def get_positional_dict(current_mask: ndarray,
                        object_coords: ndarray,
                        boundaries: tuple,
                        image_boundaries_mask: ndarray,
                        progress_tracker: ModuleProgressTracker
                        ) -> dict:
    """
    Given an object's mask and coords,
    returns a dict of positional
    measurements for that object.

    Args:
        current_mask (ndarray): The object's boolean mask, cropped to its tight bounding box.
        object_coords (ndarray): The object's pixel coordinates, in global image coordinates.
        boundaries (tuple): The object's boundaries.
        image_boundaries_mask (ndarray): The image's boundaries mask, cropped to the object's tight bounding box.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The object's positional measurements dict.
    """
    # updating progress tracker attributes
    progress_tracker.current_iteration += 1
    progress_tracker.current_measurement += 1

    # getting current object centroid
    centroid = get_pixel_centroid(coords=object_coords)

    # getting shape
    bounding_shape = get_bounding_shape(boundaries=boundaries)

    # getting object/image border masks intersection
    border_intersection = (current_mask & image_boundaries_mask)

    # getting object border pixel count
    border_pixel_count = get_border_pixel_count(masks_intersection=border_intersection)

    # checking whether object touches image border
    touches_border = get_touches_border_bool(masks_intersection=border_intersection)

    # getting object total pixel count
    object_pixel_count = object_coords.shape[1]

    # getting object border pixel ratio
    try:
        border_pixel_ratio = border_pixel_count / object_pixel_count
    except ZeroDivisionError:
        border_pixel_ratio = 0

    # converting data types
    centroid = coords_to_string(coords=centroid)
    boundaries = coords_to_string(coords=boundaries)
    bounding_shape = coords_to_string(coords=bounding_shape)

    # assembling positional dict
    positional_dict = {'centroid': centroid,
                       'boundaries': boundaries,
                       'bounding_shape': bounding_shape,
                       'touches_border': touches_border,
                       'border_pixel_count': border_pixel_count,
                       'border_pixel_ratio': border_pixel_ratio}

    # returning positional dict
    return positional_dict


def get_positional_df(mask: ndarray,
                      object_slices: dict,
                      image_boundaries_mask: ndarray,
                      progress_tracker: ModuleProgressTracker
                      ) -> DataFrame:
    """
    Given a mask and per-object
    bounding-box slices, iterates
    over object ids, and returns
    a per object positional df.
    Assumes a 3D mask.

    Args:
        mask (ndarray): The image's segmentation mask.
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        image_boundaries_mask (ndarray): The image's boundaries mask.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The per-object positional df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'positional'

    # updating progress tracker attributes
    progress_tracker.measurements_num = 1

    # defining placeholder value for dicts list
    dicts_list = []

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # getting object slices items
    object_slices_items = object_slices.items()

    # iterating over object slices items
    for object_item in object_slices_items:

        # getting current object id/slice
        object_id, object_slice = object_item

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object boundaries directly from its bounding-box slice (tight, no full-array scan)
        boundaries = get_boundaries_from_slice(object_slice=object_slice)

        # getting current object mask (small, tight crop - cropped before comparing to object id)
        mask_crop = mask[object_slice]
        current_mask = get_bool_mask(mask=mask_crop,
                                     object_id=object_id)

        # getting current object pixel coords (local to crop), translated to global image coordinates
        object_offsets = (object_slice[0].start, object_slice[1].start, object_slice[2].start)
        local_coords = get_pixel_coords(mask=current_mask)
        object_coords = offset_coords(coords=local_coords,
                                      offsets=object_offsets)

        # getting current image boundaries mask crop (matching object's tight bounding box)
        current_image_boundaries_mask = image_boundaries_mask[object_slice]

        # getting current object positional dict
        positional_dict = get_positional_dict(current_mask=current_mask,
                                              object_coords=object_coords,
                                              boundaries=boundaries,
                                              image_boundaries_mask=current_image_boundaries_mask,
                                              progress_tracker=progress_tracker)

        # assembling current dict
        current_dict = ({'object_id': object_id}
                        | positional_dict)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling positional df from dicts list
    positional_df = DataFrame(dicts_list)

    # returning positional df
    return positional_df


def get_morphology_dict(mask: ndarray,
                        object_id: int,
                        boundaries: tuple,
                        scales_dict: dict,
                        smooth_mesh_iterations: int,
                        progress_tracker: ModuleProgressTracker,
                        margin: int = 3
                        ) -> dict:
    """
    Given an object's id and boundaries,
    returns a dict of morphology
    measurements for that object.

    Args:
        mask (ndarray): The image's segmentation mask.
        object_id (int): The object's id.
        boundaries (tuple): The object's boundaries.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        smooth_mesh_iterations (int): The number of mesh-smoothing iterations (-1 disables smoothing).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.
        margin (int): The margin (in pixels) to apply when cropping the mask.

    Returns:
        dict: The object's morphology measurements dict.
    """
    # updating progress tracker attributes
    progress_tracker.current_iteration += 1
    progress_tracker.current_measurement += 1

    # getting current mask crop (small, margin-padded label crop - cropped before comparing to object id)
    mask_crop = crop_object(image=mask,
                            boundaries=boundaries,
                            margin=margin)

    # getting current object mask crop
    current_mask_crop = get_bool_mask(mask=mask_crop,
                                      object_id=object_id)

    # getting current object volume (in pixels)
    pixel_volume = get_pixel_volume(mask=current_mask_crop)

    # getting current object mesh
    object_mesh = get_mesh(mask=current_mask_crop,
                           scales_dict=scales_dict)

    # extracting values from tuple
    vertices, faces = object_mesh

    # getting smooth mesh bool
    smooth_meshes = (smooth_mesh_iterations != -1)

    # checking whether to smooth mesh
    if smooth_meshes:

        # smoothing mesh
        vertices = taubin_smooth(vertices=vertices,
                                 faces=faces,
                                 iterations=smooth_mesh_iterations)

    # getting current object mesh triangles
    triangles = get_mesh_triangles(vertices=vertices,
                                   faces=faces)

    # getting current object tetrahedron volumes
    tetrahedron_volumes = get_tetrahedron_volumes(triangles=triangles)

    # getting current object polyhedron volume
    polyhedron_volume = get_polyhedron_volume(tetrahedron_volumes=tetrahedron_volumes)

    # getting current object volume
    volume = get_mesh_volume(polyhedron_volume=polyhedron_volume)

    # getting current object surface area
    surface_area = get_mesh_surface_area(triangles=triangles)

    # getting current object area to volume ratio
    area_vol_ratio = get_area_vol_ratio(volume=volume,
                                        surface_area=surface_area)

    # getting current object bounding volume
    bounding_volume = get_bounding_volume(boundaries=boundaries)

    # getting current object volume radius
    volume_radius = get_volume_radius(volume=volume)

    # getting current object radius ratio
    radius_ratio = get_radius_ratio(vertices=vertices,
                                    triangles=triangles,
                                    tetrahedron_volumes=tetrahedron_volumes,
                                    polyhedron_volume=polyhedron_volume)

    # getting current object sphericity
    sphericity = get_sphericity(volume=volume,
                                surface_area=surface_area)

    # assembling morphology dict
    morphology_dict = {'pixel_volume': pixel_volume,
                       'volume': volume,
                       'surface_area': surface_area,
                       'area_vol_ratio': area_vol_ratio,
                       'bounding_volume': bounding_volume,
                       'volume_radius': volume_radius,
                       'radius_ratio': radius_ratio,
                       'sphericity': sphericity}

    # returning morphology dict
    return morphology_dict


def get_morphology_df(mask: ndarray,
                      object_slices: dict,
                      scales_dict: dict,
                      smooth_mesh_iterations: int,
                      progress_tracker: ModuleProgressTracker
                      ) -> DataFrame:
    """
    Given a mask and per-object
    bounding-box slices, iterates
    over object ids, and returns
    a per object morphology df.

    Args:
        mask (ndarray): The image's segmentation mask.
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        smooth_mesh_iterations (int): The number of mesh-smoothing iterations (-1 disables smoothing).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The per-object morphology df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'morphology'

    # updating progress tracker attributes
    progress_tracker.measurements_num = 1

    # defining placeholder value for dicts list
    dicts_list = []

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # getting object slices items
    object_slices_items = object_slices.items()

    # iterating over object slices items
    for object_item in object_slices_items:

        # getting current object id/slice
        object_id, object_slice = object_item

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object boundaries directly from its bounding-box slice (tight, no full-array scan)
        boundaries = get_boundaries_from_slice(object_slice=object_slice)

        # getting current object morphology dict
        morphology_dict = get_morphology_dict(mask=mask,
                                              object_id=object_id,
                                              boundaries=boundaries,
                                              scales_dict=scales_dict,
                                              smooth_mesh_iterations=smooth_mesh_iterations,
                                              progress_tracker=progress_tracker)

        # assembling current dict
        current_dict = ({'object_id': object_id}
                        | morphology_dict)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling morphology df from dicts list
    morphology_df = DataFrame(dicts_list)

    # returning morphology df
    return morphology_df


def get_base_df(image_name: str,
                image_index: int,
                mask: ndarray,
                object_slices: dict,
                description: str,
                scales_dict: dict,
                smooth_mesh_iterations: int,
                skip_positional: bool,
                skip_morphological: bool,
                progress_tracker: ModuleProgressTracker
                ) -> DataFrame:
    """
    Given a loaded mask and per-object
    bounding-box slices, returns a per
    object dataframe, containing index
    and (unless skipped) positional and
    morphological measurements.

    Args:
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        mask (ndarray): The image's segmentation mask.
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        description (str): The objects' description label.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        smooth_mesh_iterations (int): The number of mesh-smoothing iterations (-1 disables smoothing).
        skip_positional (bool): Whether to skip positional measurements.
        skip_morphological (bool): Whether to skip morphological measurements.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The per-object base df.
    """
    # defining object id col
    object_id_col = 'object_id'

    # getting object ids
    object_ids = list(object_slices.keys())

    # getting object count
    object_digits_num = get_digits_num(items_list=object_ids)

    # getting index df (always kept, holds the uid used to merge dfs)
    base_df = get_index_df(image_name=image_name,
                           image_index=image_index,
                           description=description,
                           object_slices=object_slices,
                           object_digits_num=object_digits_num,
                           progress_tracker=progress_tracker)

    # checking whether to include positional measurements
    if not skip_positional:

        # getting image boundaries mask
        image_boundaries_mask = get_image_boundaries_mask(mask=mask)

        # getting positional df
        positional_df = get_positional_df(mask=mask,
                                          object_slices=object_slices,
                                          image_boundaries_mask=image_boundaries_mask,
                                          progress_tracker=progress_tracker)

        # merging positional df into base df
        base_df = base_df.merge(right=positional_df,
                                on=object_id_col)

    # checking whether to include morphological measurements
    if not skip_morphological:

        # getting morphology df
        morphology_df = get_morphology_df(mask=mask,
                                          object_slices=object_slices,
                                          scales_dict=scales_dict,
                                          smooth_mesh_iterations=smooth_mesh_iterations,
                                          progress_tracker=progress_tracker)

        # merging morphology df into base df
        base_df = base_df.merge(right=morphology_df,
                                on=object_id_col)

    # returning base df
    return base_df


def get_object_crop(image: ndarray,
                    mask: ndarray,
                    object_slice: tuple,
                    object_id: int,
                    margin: int = 1
                    ) -> tuple:
    """
    Given an image, mask, and an
    object's bounding-box slice,
    returns the object's margin-padded
    image and boolean mask crops.

    Args:
        image (ndarray): The channel image.
        mask (ndarray): The image's segmentation mask.
        object_slice (tuple): The object's tight bounding-box slice tuple.
        object_id (int): The object's id.
        margin (int): The margin (in pixels) to apply when cropping the image/mask.

    Returns:
        tuple: A (image_crop, current_mask_crop) tuple.
    """
    # getting current object boundaries directly from its bounding-box slice (tight, no full-array scan)
    boundaries = get_boundaries_from_slice(object_slice=object_slice)

    # getting current image crop
    image_crop = crop_object(image=image,
                             boundaries=boundaries,
                             margin=margin)

    # getting current mask crop (small, margin-padded label crop - cropped before comparing to object id)
    mask_crop = crop_object(image=mask,
                            boundaries=boundaries,
                            margin=margin)

    # getting current object mask crop
    current_mask_crop = get_bool_mask(mask=mask_crop,
                                      object_id=object_id)

    # assembling current image/mask crops tuple
    current_crops_tuple = (image_crop, current_mask_crop)

    # returning image/mask crops tuple
    return current_crops_tuple


def get_id_dict(image: ndarray,
                mask: ndarray,
                channel_name: str,
                haralick_distances: list,
                progress_tracker: ModuleProgressTracker
                ) -> dict:
    """
    Given an image and corresponding
    mask, returns id dict, according
    to specified channel name.

    Args:
        image (ndarray): The channel image crop.
        mask (ndarray): The object's boolean mask crop.
        channel_name (str): The channel's name.
        haralick_distances (list): Unused for this measurement (kept for a uniform measurement function signature).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The channel's id dict.
    """
    # updating progress tracker attributes
    progress_tracker.current_iteration += 1
    progress_tracker.current_measurement += 1

    # getting haralick distances (unused for this measurement)
    _ = haralick_distances

    # getting current filtered_image (pixels inside object)
    filtered_image = image[mask]

    # getting current id
    current_id = get_measurement(values=filtered_image,
                                 measurement='mode')

    # assembling current id dict
    id_dict = {channel_name: current_id}

    # returning id dict
    return id_dict


def get_id_df(image: ndarray,
              mask: ndarray,
              channel_name: str,
              haralick_distances: list,
              haralick_range: tuple | None,
              object_slices: dict,
              progress_tracker: ModuleProgressTracker
              ) -> DataFrame:
    """
    Given a channel image/mask and
    per-object bounding-box slices,
    iterates over object ids, and
    returns a per object id df.

    Args:
        image (ndarray): The channel image.
        mask (ndarray): The image's segmentation mask.
        channel_name (str): The channel's name.
        haralick_distances (list): Unused for this measurement (kept for a uniform measurement function signature).
        haralick_range (tuple | None): Unused for this measurement (kept for a uniform measurement function signature).
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The channel's per-object id df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'id'

    # getting haralick range (unused for this measurement)
    _ = haralick_range

    # defining placeholder value for dicts list
    dicts_list = []

    # updating progress tracker attributes
    progress_tracker.measurements_num = 1

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # getting object slices items
    object_slices_items = object_slices.items()

    # iterating over object slices items
    for object_item in object_slices_items:

        # getting current object id/slice
        object_id, object_slice = object_item

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object image/mask crops
        current_image_crop, current_mask_crop = get_object_crop(image=image,
                                                                mask=mask,
                                                                object_slice=object_slice,
                                                                object_id=object_id,
                                                                margin=1)

        # getting current object id dict
        id_dict = get_id_dict(image=current_image_crop,
                              mask=current_mask_crop,
                              channel_name=channel_name,
                              haralick_distances=haralick_distances,
                              progress_tracker=progress_tracker)

        # assembling current dict
        current_dict = ({'object_id': object_id}
                        | id_dict)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling id df from dicts list
    id_df = DataFrame(dicts_list)

    # returning id df
    return id_df


def get_intensities_dict(image: ndarray,
                         mask: ndarray,
                         channel_name: str,
                         haralick_distances: list,
                         progress_tracker: ModuleProgressTracker,
                         background: bool = False
                         ) -> dict:
    """
    Given an image and corresponding
    mask, returns intensities dict,
    according to specified channel
    name. Foreground mode (default)
    expects the object's image crop
    and boolean mask crop; background
    mode expects the full channel
    image and the full label mask
    (pixels where mask == 0 are
    measured).

    Args:
        image (ndarray): The channel image crop (foreground) or the full channel image (background).
        mask (ndarray): The object's boolean mask crop (foreground) or the full label mask (background).
        channel_name (str): The channel's name.
        haralick_distances (list): Unused for this measurement (kept for a uniform measurement function signature).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.
        background (bool): Whether to measure background (outside object) pixels instead of foreground.

    Returns:
        dict: The channel's intensities dict.
    """
    # getting haralick distances (unused for this measurement)
    _ = haralick_distances

    # defining placeholder value for intensities dict
    intensities_dict = {}

    # getting background/foreground masks
    background_mask = (mask == 0)  # works both with numbers and bools since zero is falsy
    foreground_mask = (mask != 0)

    # checking whether measure in background
    if background:

        # getting current filtered image (pixels outside objects)
        filtered_image = image[background_mask]

    else:

        # getting current filtered_image (pixels inside object)
        filtered_image = image[foreground_mask]

    # iterating over measurements list
    for measurement in _INTENSITY_MEASUREMENTS:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_measurement += 1

        # getting current measurement
        current_measurement = get_measurement(values=filtered_image,
                                              measurement=measurement)

        # assembling current prefix
        current_prefix = f'{channel_name}'

        # checking whether measure in background
        if background:

            # updating current prefix
            current_prefix += '_background'

        # assembling current measurement string
        measurement_string = f'{current_prefix}_{measurement}_intensity'

        # assembling current measurement dict
        current_dict = {measurement_string: current_measurement}

        # updating intensities dict
        intensities_dict.update(current_dict)

    # returning intensities dict
    return intensities_dict


def get_bg_removed_dict(intensities_dict: dict,
                        background_dict: dict,
                        progress_tracker: ModuleProgressTracker
                        ) -> dict:
    """
    Given an object's intensities dict
    and the channel's background
    intensities dict (both generated
    by get_intensities_dict, so
    measurements match in order),
    returns a dict with each object
    intensity minus its respective
    background intensity (columns
    named "*_bg_removed").

    Args:
        intensities_dict (dict): The object's intensities dict.
        background_dict (dict): The channel's background intensities dict.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The object's background removed intensities dict.
    """
    # defining placeholder value for bg removed dict
    bg_removed_dict = {}

    # getting intensities/background dict values
    intensities_items = intensities_dict.items()
    background_values = background_dict.values()

    # iterating over intensities items/background values
    for intensity_item, background_value in zip(intensities_items, background_values):

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_measurement += 1

        # getting current measurement string/intensity
        measurement_string, intensity = intensity_item

        # getting current background removed intensity
        bg_removed_intensity = (intensity - background_value)

        # assembling current bg removed dict
        current_dict = {f'{measurement_string}_bg_removed': bg_removed_intensity}

        # updating bg removed dict
        bg_removed_dict.update(current_dict)

    # returning bg removed dict
    return bg_removed_dict


def get_bg_normalized_dict(intensities_dict: dict,
                           background_dict: dict,
                           progress_tracker: ModuleProgressTracker
                           ) -> dict:
    """
    Given an object's intensities dict
    and the channel's background
    intensities dict (both generated
    by get_intensities_dict, so
    measurements match in order),
    returns a dict with each object
    intensity divided by its respective
    background intensity (columns named
    "*_bg_normalized"). Zero background
    values yield nan.

    Args:
        intensities_dict (dict): The object's intensities dict.
        background_dict (dict): The channel's background intensities dict.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The object's background normalized intensities dict.
    """
    # defining placeholder value for bg normalized dict
    bg_normalized_dict = {}

    # getting intensities/background dict values
    intensities_items = intensities_dict.items()
    background_values = background_dict.values()

    # iterating over intensities items/background values
    for intensity_item, background_value in zip(intensities_items, background_values):

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_measurement += 1

        # getting current measurement string/intensity
        measurement_string, intensity = intensity_item

        # checking whether background is zero
        if background_value == 0:

            # setting normalized intensity to None (avoids division by zero)
            bg_normalized_intensity = None

        else:

            # getting current background normalized intensity
            bg_normalized_intensity = (intensity / background_value)

        # assembling current bg normalized dict
        current_dict = {f'{measurement_string}_bg_normalized': bg_normalized_intensity}

        # updating bg normalized dict
        bg_normalized_dict.update(current_dict)

    # returning bg normalized dict
    return bg_normalized_dict


def get_intensities_df(image: ndarray,
                       mask: ndarray,
                       channel_name: str,
                       haralick_distances: list,
                       haralick_range: tuple | None,
                       object_slices: dict,
                       progress_tracker: ModuleProgressTracker
                       ) -> DataFrame:
    """
    Given a channel image/mask and
    per-object bounding-box slices,
    iterates over object ids, and
    returns a per object intensities
    df. Background (outside objects)
    intensities are computed once per
    channel and merged into every row
    (columns named "*_background_*").

    Args:
        image (ndarray): The channel image.
        mask (ndarray): The image's segmentation mask.
        channel_name (str): The channel's name.
        haralick_distances (list): Unused for this measurement (kept for a uniform measurement function signature).
        haralick_range (tuple | None): Unused for this measurement (kept for a uniform measurement function signature).
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The channel's per-object intensities df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'intensity'

    # getting haralick range (unused for this measurement)
    _ = haralick_range

    # getting base measurements num
    base_measurements_num = len(_INTENSITY_MEASUREMENTS)

    # getting bg measurements num
    bg_measurements_num = (base_measurements_num * 1)

    # getting obj measurements num
    obj_measurements_num = (base_measurements_num * 3)

    # updating progress tracker attributes
    progress_tracker.measurements_num = bg_measurements_num

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # resetting progress tracker attributes
    progress_tracker.current_measurement = 0

    # getting background dict (common to all objects)
    background_dict = get_intensities_dict(image=image,
                                           mask=mask,
                                           channel_name=channel_name,
                                           haralick_distances=haralick_distances,
                                           progress_tracker=progress_tracker,
                                           background=True)

    # defining placeholder value for dicts list
    dicts_list = []

    # updating progress tracker attributes
    progress_tracker.measurements_num = obj_measurements_num

    # getting object slices items
    object_slices_items = object_slices.items()

    # iterating over object slices items
    for object_item in object_slices_items:

        # getting current object id/slice
        object_id, object_slice = object_item

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object image/mask crops
        current_image_crop, current_mask_crop = get_object_crop(image=image,
                                                                mask=mask,
                                                                object_slice=object_slice,
                                                                object_id=object_id,
                                                                margin=1)

        # getting current object intensities dict
        intensities_dict = get_intensities_dict(image=current_image_crop,
                                                mask=current_mask_crop,
                                                channel_name=channel_name,
                                                haralick_distances=haralick_distances,
                                                progress_tracker=progress_tracker,
                                                background=False)

        # getting current object bg removed dict
        bg_removed_dict = get_bg_removed_dict(intensities_dict=intensities_dict,
                                              background_dict=background_dict,
                                              progress_tracker=progress_tracker)

        # getting current object bg normalized dict
        bg_normalized_dict = get_bg_normalized_dict(intensities_dict=intensities_dict,
                                                    background_dict=background_dict,
                                                    progress_tracker=progress_tracker)

        # assembling current dict
        current_dict = ({'object_id': object_id}
                        | intensities_dict
                        | background_dict
                        | bg_removed_dict
                        | bg_normalized_dict)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling intensities df from dicts list
    intensities_df = DataFrame(dicts_list)

    # returning intensities df
    return intensities_df


def get_textures_dict(image: ndarray,
                      mask: ndarray,
                      channel_name: str,
                      haralick_distances: list,
                      haralick_range: tuple | None,
                      progress_tracker: ModuleProgressTracker
                      ) -> dict:
    """
    Given an image and corresponding
    mask, returns textures dict,
    according to specified channel
    name, computed at each given
    haralick distance.

    Args:
        image (ndarray): The channel image crop.
        mask (ndarray): The object's boolean mask crop.
        channel_name (str): The channel's name.
        haralick_distances (list): The pixel distances to compute haralick features at.
        haralick_range (tuple | None): The fixed (low, high) intensity range used to bin gray levels (per-crop min/max if None).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The channel's textures dict.
    """
    # defining placeholder value for textures dict
    textures_dict = {}

    # defining haralick levels
    levels = 64

    # getting haralick features by distance (progress_tracker.current_measurement updated internally)
    haralick_features_by_distance = get_haralick_features(image=image,
                                                          mask=mask,
                                                          levels=levels,
                                                          distances=haralick_distances,
                                                          intensity_range=haralick_range,
                                                          progress_tracker=progress_tracker)

    # getting multiple distances bool (keeps col names backwards compatible for the single-distance default)
    multiple_distances = (len(haralick_distances) > 1)

    # getting haralick features by distance items
    distance_features_items = haralick_features_by_distance.items()

    # iterating over haralick features by distance items
    for distance_features_item in distance_features_items:

        # getting current distance/features
        distance, haralick_features = distance_features_item

        # getting features mean (across offsets)
        haralick_features = arr_mean(haralick_features,
                                     axis=0)

        # getting features dict
        features_dict = get_features_dict(features_arr=haralick_features)

        # getting features dict items
        features_dict_items = features_dict.items()

        # iterating over features dict
        for feature_dict_item in features_dict_items:

            # getting current feature name/value
            feature_name, feature_value = feature_dict_item

            # assembling current texture name
            if multiple_distances:
                texture_name = f'{channel_name}_d{distance}_{feature_name}'
            else:
                texture_name = f'{channel_name}_{feature_name}'

            # assembling current texture dict
            texture_dict = {texture_name: feature_value}

            # updating textures dict
            textures_dict.update(texture_dict)

    # returning textures dict
    return textures_dict


def get_textures_df(image: ndarray,
                    mask: ndarray,
                    channel_name: str,
                    haralick_distances: list,
                    haralick_range: tuple | None,
                    object_slices: dict,
                    progress_tracker: ModuleProgressTracker
                    ) -> DataFrame:
    """
    Given a channel image/mask and
    per-object bounding-box slices,
    iterates over object ids, and
    returns a per object texture df.

    Args:
        image (ndarray): The channel image.
        mask (ndarray): The image's segmentation mask.
        channel_name (str): The channel's name.
        haralick_distances (list): The pixel distances to compute haralick features at.
        haralick_range (tuple | None): The fixed (low, high) intensity range used to bin gray levels (per-crop min/max if None).
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The channel's per-object texture df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'texture'

    # getting mask is 3d bool (determines haralick offsets count per distance: 13 for 3d, 4 for 2d -
    # mirrors get_haralick_features's own image_is_3d check)
    mask_is_3d = (mask.ndim == 3)
    haralick_offsets_per_distance = (13 if mask_is_3d else 4)

    # getting measurements num (one per offset, per distance)
    measurements_num = (len(haralick_distances) * haralick_offsets_per_distance)

    # updating progress tracker attributes
    progress_tracker.measurements_num = measurements_num

    # defining placeholder value for dicts list
    dicts_list = []

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # getting object slices items
    object_slices_items = object_slices.items()

    # iterating over object slices items
    for object_item in object_slices_items:

        # getting current object id/slice
        object_id, object_slice = object_item

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object image/mask crops
        current_image_crop, current_mask_crop = get_object_crop(image=image,
                                                                mask=mask,
                                                                object_slice=object_slice,
                                                                object_id=object_id,
                                                                margin=1)

        # getting current object textures dict
        textures_dict = get_textures_dict(image=current_image_crop,
                                          mask=current_mask_crop,
                                          channel_name=channel_name,
                                          haralick_distances=haralick_distances,
                                          haralick_range=haralick_range,
                                          progress_tracker=progress_tracker)

        # assembling current dict
        current_dict = ({'object_id': object_id}
                        | textures_dict)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling final df from dicts list
    final_df = DataFrame(dicts_list)

    # returning final df
    return final_df


def get_overlap_dict(image: ndarray,
                     mask: ndarray,
                     channel_name: str,
                     haralick_distances: list,
                     progress_tracker: ModuleProgressTracker
                     ) -> dict:
    """
    Given another object mask crop and
    the current object's mask crop,
    returns overlap dict, according to
    specified channel name (overlap
    is measured within the boundaries
    of the current object).

    Args:
        image (ndarray): The other mask's crop (non-zero pixels are considered object pixels).
        mask (ndarray): The object's boolean mask crop.
        channel_name (str): The channel's name.
        haralick_distances (list): Unused for this measurement (kept for a uniform measurement function signature).
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        dict: The channel's overlap dict.
    """
    # getting haralick distances (unused for this measurement)
    _ = haralick_distances

    # defining placeholder value for overlap dict
    overlap_dict = {}

    # getting current filtered image (other mask pixels inside object)
    filtered_image = image[mask]

    # getting current object pixels/overlapping pixels counts
    object_pixels = int(count_nonzero(mask))
    overlap_pixels = int(count_nonzero(filtered_image))

    # getting overlap fraction (relative to current object)
    overlap_fraction = ((overlap_pixels / object_pixels) if object_pixels > 0 else 0.0)

    # assembling overlap values dict
    overlap_values = {'pixels': overlap_pixels,
                      'fraction': overlap_fraction}

    # iterating over overlap measurements
    for measurement in _OVERLAP_MEASUREMENTS:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_measurement += 1

        # assembling current measurement string
        measurement_string = f'{channel_name}_overlap_{measurement}'

        # getting current measurement
        current_measurement = overlap_values[measurement]

        # assembling current measurement dict
        current_dict = {measurement_string: current_measurement}

        # updating overlap dict
        overlap_dict.update(current_dict)

    # returning overlap dict
    return overlap_dict


def get_overlap_df(image: ndarray,
                   mask: ndarray,
                   channel_name: str,
                   haralick_distances: list,
                   haralick_range: tuple | None,
                   object_slices: dict,
                   progress_tracker: ModuleProgressTracker
                   ) -> DataFrame:
    """
    Given another object mask, the
    image's segmentation mask, and
    per-object bounding-box slices,
    iterates over object ids, and
    returns a per object overlap df.

    Args:
        image (ndarray): The other object mask (non-zero pixels are considered object pixels).
        mask (ndarray): The image's segmentation mask.
        channel_name (str): The channel's name.
        haralick_distances (list): Unused for this measurement (kept for a uniform measurement function signature).
        haralick_range (tuple | None): Unused for this measurement (kept for a uniform measurement function signature).
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The channel's per-object overlap df.
    """
    # updating progress tracker attributes
    progress_tracker.df_name = 'overlap'

    # getting haralick range (unused for this measurement)
    _ = haralick_range

    # getting measurements num
    measurements_num = len(_OVERLAP_MEASUREMENTS)

    # updating progress tracker attributes
    progress_tracker.measurements_num = measurements_num

    # defining placeholder value for dicts list
    dicts_list = []

    # resetting progress tracker attributes
    progress_tracker.current_object = 0

    # getting object slices items
    object_slices_items = object_slices.items()

    # iterating over object slices items
    for object_item in object_slices_items:

        # getting current object id/slice
        object_id, object_slice = object_item

        # updating progress tracker attributes
        progress_tracker.current_object += 1

        # resetting progress tracker attributes
        progress_tracker.current_measurement = 0

        # getting current object other mask/mask crops
        current_image_crop, current_mask_crop = get_object_crop(image=image,
                                                                mask=mask,
                                                                object_slice=object_slice,
                                                                object_id=object_id,
                                                                margin=1)

        # getting current object overlap dict
        overlap_dict = get_overlap_dict(image=current_image_crop,
                                        mask=current_mask_crop,
                                        channel_name=channel_name,
                                        haralick_distances=haralick_distances,
                                        progress_tracker=progress_tracker)

        # assembling current dict
        current_dict = ({'object_id': object_id}
                        | overlap_dict)

        # appending current dict to dicts list
        dicts_list.append(current_dict)

    # assembling overlap df from dicts list
    overlap_df = DataFrame(dicts_list)

    # returning overlap df
    return overlap_df


def get_additional_df(image: ndarray,
                      mask: ndarray,
                      channel_name: str,
                      measurement: str,
                      haralick_distances: list,
                      haralick_range: tuple | None,
                      object_slices: dict,
                      progress_tracker: ModuleProgressTracker
                      ) -> DataFrame:
    """
    Given a channel image/mask and
    per-object bounding-box slices,
    returns the channel's per-object
    additional measurements df,
    according to specified measurement.

    Args:
        image (ndarray): The channel image.
        mask (ndarray): The image's segmentation mask.
        channel_name (str): The channel's name.
        measurement (str): The measurement type to compute ("id", "intensity", "texture" or "overlap").
        haralick_distances (list): The pixel distances to compute haralick features at.
        haralick_range (tuple | None): The fixed (low, high) intensity range used to bin gray levels for texture (per-crop min/max if None).
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The channel's per-object additional measurements df.

    Raises:
        Exception: If measurement is not a recognized measurement type.
    """
    # assembling measurements dict
    measurement_funcs = {'id': get_id_df,
                         'intensity': get_intensities_df,
                         'texture': get_textures_df,
                         'overlap': get_overlap_df}

    # getting valid function names
    valid_funcs = measurement_funcs.keys()
    valid_funcs = list(valid_funcs)

    # getting default measurement function
    measurement_func = measurement_funcs.get(measurement)

    # checking if measurement is valid
    if measurement_func is None:

        # defining error message
        e_string = f'Invalid measurement "{measurement}".\n'
        e_string += f'Valid measurements: {valid_funcs}\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # getting additional df
    additional_df = measurement_func(image=image,
                                     mask=mask,
                                     channel_name=channel_name,
                                     haralick_distances=haralick_distances,
                                     haralick_range=haralick_range,
                                     object_slices=object_slices,
                                     progress_tracker=progress_tracker)

    # returning additional df
    return additional_df


def get_additional_dfs(image_name: str,
                       mask: ndarray,
                       channels_dict: dict,
                       haralick_distances: list,
                       haralick_range: tuple | None,
                       object_slices: dict,
                       progress_tracker: ModuleProgressTracker
                       ) -> list:
    """
    Given a channels dict and per-object
    bounding-box slices, iterates over
    channels, loads the corresponding
    images, and returns additional
    dfs with respective measurements.
    Consecutive channels sharing the
    same folder path reuse the already
    loaded image.

    Args:
        image_name (str): The name of the image being processed.
        mask (ndarray): The image's segmentation mask.
        channels_dict (dict): A dictionary mapping "name#measurement" prefixes to channel folder paths.
        haralick_distances (list): The pixel distances to compute haralick features at.
        haralick_range (tuple | None): The fixed (low, high) intensity range used to bin gray levels for texture (per-crop min/max if None).
        object_slices (dict): A dict mapping object id to its bounding-box slice tuple.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        list: The list of per-channel dfs.
    """
    # defining placeholder value for additional dfs list
    additional_dfs = []

    # defining placeholder value for previous path/image
    previous_path = None
    previous_image = None

    # getting dict items
    dict_items = channels_dict.items()

    # iterating over dict items
    for channel_item in dict_items:

        # updating progress tracker attributes
        progress_tracker.current_channel += 1

        # getting current key/value
        channel_prefix, channel_path = channel_item

        # getting current channel split
        channel_split = channel_prefix.split('#')

        # getting current channel name/measurement
        channel_name, measurement = channel_split

        # getting current image path
        current_path = join(channel_path,
                            image_name)

        # checking if previous path is none
        if previous_path is None:  # first image on iteration

            # loading current channel image
            current_image = load_image(input_path=current_path)

            # updating previous path/image
            previous_path = current_path
            previous_image = current_image

        # getting current channel same as last bool
        current_same_as_last = (current_path == previous_path)

        # checking if current channel is same as last
        if current_same_as_last:

            # getting current image
            current_image = previous_image

        else:

            # loading current channel image
            current_image = load_image(input_path=current_path)

            # updating previous path/image
            previous_path = current_path
            previous_image = current_image

        # getting current channel df
        current_channel_df = get_additional_df(image=current_image,
                                               mask=mask,
                                               channel_name=channel_name,
                                               measurement=measurement,
                                               haralick_distances=haralick_distances,
                                               haralick_range=haralick_range,
                                               object_slices=object_slices,
                                               progress_tracker=progress_tracker)

        # appending current channel df to dfs list
        additional_dfs.append(current_channel_df)

    # returning additional dfs
    return additional_dfs


def get_objects_df(image_name: str,
                   image_index: int,
                   input_path: str,
                   channels_dict: dict,
                   description: str,
                   scales_dict: dict,
                   smooth_mesh_iterations: int,
                   haralick_distances: list,
                   haralick_range: tuple | None,
                   skip_positional: bool,
                   skip_morphological: bool,
                   progress_tracker: ModuleProgressTracker
                   ) -> DataFrame:
    """
    Given a path to a segmentation
    mask, returns a per object
    dataframe, containing index and
    (unless skipped) positional and
    morphological measurements, plus pixel value
    info for additional channels,
    according to specified
    measurement (merged on object id).
    Returns an empty df if the mask
    contains no objects.

    Args:
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        input_path (str): The path to the segmentation mask.
        channels_dict (dict): A dictionary mapping "name#measurement" prefixes to channel folder paths.
        description (str): The objects' description label.
        scales_dict (dict): The per-axis pixel-to-micron scales.
        smooth_mesh_iterations (int): The number of mesh-smoothing iterations (-1 disables smoothing).
        haralick_distances (list): The pixel distances to compute haralick features at.
        haralick_range (tuple | None): The fixed (low, high) intensity range used to bin gray levels for texture (per-crop min/max if None).
        skip_positional (bool): Whether to skip positional measurements.
        skip_morphological (bool): Whether to skip morphological measurements.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        DataFrame: The image's per-object df.
    """
    # defining placeholder value for objects df
    objects_df = DataFrame()

    # defining object id col
    object_id_col = 'object_id'

    # loading current mask
    mask = load_image(input_path=input_path)

    # getting current mask object ids
    object_ids = get_object_ids(mask=mask)

    # getting current image object count
    object_count = len(object_ids)

    # checking if there are any objects in given mask
    if object_count == 0:

        # returning empty dataframe
        return objects_df

    # updating progress tracker attributes
    progress_tracker.objects_num = object_count

    # resetting progress tracker attributes
    progress_tracker.current_channel = 0

    # getting object bounding-box slices (single O(image_size) pass for all objects)
    object_slices = get_object_slices(mask=mask)

    # getting base objects df (obtains positional and morphological features)
    objects_df = get_base_df(image_name=image_name,
                             image_index=image_index,
                             mask=mask,
                             object_slices=object_slices,
                             description=description,
                             scales_dict=scales_dict,
                             smooth_mesh_iterations=smooth_mesh_iterations,
                             skip_positional=skip_positional,
                             skip_morphological=skip_morphological,
                             progress_tracker=progress_tracker)

    # getting additional measurements dfs (obtains intensity and textural features)
    additional_dfs = get_additional_dfs(image_name=image_name,
                                        mask=mask,
                                        channels_dict=channels_dict,
                                        haralick_distances=haralick_distances,
                                        haralick_range=haralick_range,
                                        object_slices=object_slices,
                                        progress_tracker=progress_tracker)

    # iterating over additional dfs
    for additional_df in additional_dfs:

        # merging df
        objects_df = objects_df.merge(right=additional_df,
                                      on=object_id_col)

    # returning final df
    return objects_df


def generate_objects_dfs(input_folder: str,
                         output_folder: str,
                         channels: str,
                         haralick_distances: str,
                         haralick_range: tuple | None,
                         description: str,
                         scales_dict: str,
                         smooth_mesh_iterations: int,
                         skip_positional: bool,
                         skip_morphological: bool,
                         overwrite_output: bool,
                         progress_tracker: ModuleProgressTracker
                         ) -> None:
    """
    Given a path to a folder containing
    segmentation masks, generates per
    object dataframes, containing index
    and (unless skipped) positional and
    morphological
    measurements, plus pixel value info
    for additional channels, according
    to specified measurement. Saves one
    csv per mask (.tif -> .csv) to given
    output folder, skipping existing
    outputs unless overwrite_output is set.

    Args:
        input_folder (str): The path to the folder containing segmentation masks.
        output_folder (str): The path to the folder to save per-object dfs to.
        channels (str): The "dictionary" string of additional channels to analyze.
        haralick_distances (str): The comma-separated list of pixel distances for haralick texture features.
        haralick_range (tuple | None): The (low, high) fixed intensity range used to bin gray levels for texture (per-crop min/max if None).
        description (str): The objects' description label.
        scales_dict (str): The "dictionary" string of x/y/z scales (in microns) per channel.
        smooth_mesh_iterations (int): The number of mesh-smoothing iterations (-1 disables smoothing).
        skip_positional (bool): Whether to skip positional measurements.
        skip_morphological (bool): Whether to skip morphological measurements.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting images in input folder
    images = get_files_in_folder(input_folder=input_folder,
                                 extension='.tif')

    # getting channels dict
    channels_dict = get_channels_dict(channels_str=channels)

    # sorting channels dict by path
    channels_dict = sort_channels_dict(channels_dict=channels_dict)

    # getting channel keys
    channel_keys = channels_dict.keys()

    # getting channels num
    channels_count = len(channel_keys)

    # updating progress tracker attributes
    progress_tracker.channels_num = channels_count

    # getting scales dict
    scales_dict = get_scales_dict(scales_str=scales_dict)

    # getting haralick distances list
    haralick_distances = get_distances_list(distances=haralick_distances)

    # getting progress tracker iterations dict
    iterations_dict = progress_tracker.iterations_dict

    # iterating over images in input folder
    for image_name in images:

        # updating progress tracker attributes
        progress_tracker.current_image += 1

        # getting current image iterations num
        current_iterations_num = iterations_dict[image_name]

        # getting current image index
        image_index = progress_tracker.current_image

        # getting current image input/output paths
        image_path = join(input_folder,
                          image_name)
        output_name = image_name.replace('.tif', '.csv')
        output_path = join(output_folder,
                           output_name)

        # getting skip file bool
        skip_file = get_skip_file_bool(file_path=output_path,
                                       overwrite_output=overwrite_output)

        # checking whether to skip current file
        if skip_file:

            # sleeping
            progress_tracker.wait(0.05)

            # updating progress tracker attributes
            progress_tracker.current_iteration += current_iterations_num
            progress_tracker.skipped_iterations += current_iterations_num

            # skipping to next file
            continue

        # getting current image df
        current_image_df = get_objects_df(image_name=image_name,
                                          image_index=image_index,
                                          input_path=image_path,
                                          channels_dict=channels_dict,
                                          description=description,
                                          scales_dict=scales_dict,
                                          smooth_mesh_iterations=smooth_mesh_iterations,
                                          haralick_distances=haralick_distances,
                                          haralick_range=haralick_range,
                                          skip_positional=skip_positional,
                                          skip_morphological=skip_morphological,
                                          progress_tracker=progress_tracker)

        # saving current image df
        save_df(save_path=output_path,
                df=current_image_df)


def parse_and_run(args_dict: dict,
                  progress_tracker: ModuleProgressTracker
                  ) -> None:
    """
    Extracts args from args_dict
    and runs module function.

    Args:
        args_dict (dict): A dictionary containing all parsed command-line arguments.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting input folder
    input_folder = args_dict['input_folder']

    # getting output folder
    output_folder = args_dict['output_folder']

    # getting channels
    channels = args_dict['channels']

    # getting haralick distances
    haralick_distances = args_dict['haralick_distances']

    # getting haralick range
    haralick_range = args_dict['haralick_range']

    # checking if haralick range was given
    if haralick_range is not None:

        # getting haralick range tuple
        haralick_range = string_to_coords(coords_str=haralick_range)

    # getting description
    description = args_dict['description']

    # getting scales dict
    scales_dict = args_dict['scales_dict']

    # getting smooth mesh iterations
    smooth_mesh_iterations = args_dict['smooth_mesh_iterations']

    # getting skip positional
    skip_positional = args_dict['skip_positional']

    # getting skip morphological
    skip_morphological = args_dict['skip_morphological']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_objects_dfs function
    generate_objects_dfs(input_folder=input_folder,
                         output_folder=output_folder,
                         channels=channels,
                         haralick_distances=haralick_distances,
                         haralick_range=haralick_range,
                         description=description,
                         scales_dict=scales_dict,
                         smooth_mesh_iterations=smooth_mesh_iterations,
                         skip_positional=skip_positional,
                         skip_morphological=skip_morphological,
                         overwrite_output=overwrite_output,
                         progress_tracker=progress_tracker)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # initializing current module progress tracker instance
    progress_tracker = ModuleProgressTracker()

    # running code in separate thread
    progress_tracker.run(function=parse_and_run,
                         args_parser=get_args_dict)

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
