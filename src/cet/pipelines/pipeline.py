# pipeline module

print(f'starting pipeline run...')

######################################################################
# imports

from sys import argv
from os.path import join
from cet.pipelines import modules
from cet.io.cli import run_commands
from cet.io.Settings import Settings
from cet.io.files import get_vars_dict
from cet.io.cli import assemble_command
from cet.io.files import create_subfolders
from cet.io.files import delete_subfolders
from cet.io.cli import check_wavelength_set
from cet.io.files import get_subfolders_list
from cet.constants import CELLPOSE_MODEL_PATH
from cet.io.Settings import NUCLEI_MASK_NAMES
from cet.io.cli import assemble_filter_commands
from cet.io.cli import assemble_measurements_str

######################################################################
# defining global variables

# getting settings file
SETTINGS_FILE = argv[1]

# loading and validating settings with Pydantic
SETTINGS = Settings.from_yaml(input_path=SETTINGS_FILE)

######################################################################
# getting global settings

##############################
# experiment
##############################

EXPERIMENT_SETTINGS = SETTINGS.experiment

BASE_FOLDER = EXPERIMENT_SETTINGS.base_folder
IMAGES_EXTENSION = EXPERIMENT_SETTINGS.image_extension

##############################
# microscopy
##############################

MICROSCOPY_SETTINGS = SETTINGS.microscopy

NUMERICAL_APERTURE = MICROSCOPY_SETTINGS.numerical_aperture
REFRACTIVE_INDEX = MICROSCOPY_SETTINGS.refractive_index
Z_AXIS = MICROSCOPY_SETTINGS.z_axis
SCALES_STR = MICROSCOPY_SETTINGS.scales_str

##############################
# channels
##############################

CHANNELS_SETTINGS = SETTINGS.channels

CHANNEL_NAMES = CHANNELS_SETTINGS.channel_names
CHANNEL_WAVELENGTHS = CHANNELS_SETTINGS.channel_wavelengths

##############################
# segmentation
##############################

SEGMENTATION_SETTINGS = SETTINGS.segmentation

EMBRYOS_SETTINGS = SEGMENTATION_SETTINGS.embryos
NUCLEI_SETTINGS = SEGMENTATION_SETTINGS.nuclei
DOTS_SETTINGS = SEGMENTATION_SETTINGS.dots

EMBRYOS_DESCRIPTION = EMBRYOS_SETTINGS.description
EMBRYOS_SEGMENTATION_CHANNEL = EMBRYOS_SETTINGS.segmentation_channel
DECONVOLVE_EMBRYOS_CHANNEL = EMBRYOS_SETTINGS.deconvolve
BLUR_EMBRYOS_CHANNEL = EMBRYOS_SETTINGS.blur
EMBRYOS_BLUR_SIGMA = EMBRYOS_SETTINGS.blur_sigma
EMBRYOS_SEGMENTATION_MODE = EMBRYOS_SETTINGS.segmentation_mode
EMBRYOS_DIAMETER = EMBRYOS_SETTINGS.diameter
EMBRYOS_MIN_SIZE = EMBRYOS_SETTINGS.min_size
CLOSE_EMBRYOS_MASKS = EMBRYOS_SETTINGS.close_masks
EMBRYOS_CLOSING_DISTANCE = EMBRYOS_SETTINGS.closing_distance
MERGE_EMBRYOS_MASKS = EMBRYOS_SETTINGS.merge_masks
EMBRYOS_MERGE_SOLIDITY_THRESHOLD = EMBRYOS_SETTINGS.merge_solidity_threshold
EMBRYOS_MERGE_TOUCH_MARGIN = EMBRYOS_SETTINGS.merge_touch_margin
RESIZE_EMBRYOS_MASKS = EMBRYOS_SETTINGS.resize_masks
EMBRYOS_DILATION = EMBRYOS_SETTINGS.dilation
CREATE_EMBRYOS_BORDERS_MASKS = EMBRYOS_SETTINGS.create_borders_masks
EMBRYOS_BORDERS_THICKNESS = EMBRYOS_SETTINGS.borders_thickness
EMBRYOS_BORDERS_DESCRIPTION = EMBRYOS_SETTINGS.borders_description
EMBRYOS_SMOOTH_ITER = EMBRYOS_SETTINGS.smooth_iterations
EMBRYOS_MARGIN = EMBRYOS_SETTINGS.margin
EMBRYOS_BATCH_SIZE = EMBRYOS_SETTINGS.batch_size
EMBRYOS_MEASUREMENTS = EMBRYOS_SETTINGS.measurements
EMBRYOS_FILTERS = EMBRYOS_SETTINGS.filters

NUCLEI_DESCRIPTION = NUCLEI_SETTINGS.description
NUCLEI_SEGMENTATION_CHANNEL = NUCLEI_SETTINGS.segmentation_channel
DECONVOLVE_NUCLEI_CHANNEL = NUCLEI_SETTINGS.deconvolve
BLUR_NUCLEI_CHANNEL = NUCLEI_SETTINGS.blur
NUCLEI_BLUR_SIGMA = NUCLEI_SETTINGS.blur_sigma
NUCLEI_SEGMENTATION_MODE = NUCLEI_SETTINGS.segmentation_mode
NUCLEI_DIAMETER = NUCLEI_SETTINGS.diameter
NUCLEI_MIN_SIZE = NUCLEI_SETTINGS.min_size
CLOSE_NUCLEI_MASKS = NUCLEI_SETTINGS.close_masks
NUCLEI_CLOSING_DISTANCE = NUCLEI_SETTINGS.closing_distance
MERGE_NUCLEI_MASKS = NUCLEI_SETTINGS.merge_masks
NUCLEI_MERGE_SOLIDITY_THRESHOLD = NUCLEI_SETTINGS.merge_solidity_threshold
NUCLEI_MERGE_TOUCH_MARGIN = NUCLEI_SETTINGS.merge_touch_margin
RESIZE_NUCLEI_MASKS = NUCLEI_SETTINGS.resize_masks
NUCLEI_DILATION = NUCLEI_SETTINGS.dilation
CREATE_NUCLEI_BORDERS_MASKS = NUCLEI_SETTINGS.create_borders_masks
NUCLEI_BORDERS_THICKNESS = NUCLEI_SETTINGS.borders_thickness
NUCLEI_BORDERS_DESCRIPTION = NUCLEI_SETTINGS.borders_description
NUCLEI_SMOOTH_ITER = NUCLEI_SETTINGS.smooth_iterations
NUCLEI_MARGIN = NUCLEI_SETTINGS.margin
NUCLEI_BATCH_SIZE = NUCLEI_SETTINGS.batch_size
NUCLEI_MEASUREMENTS = NUCLEI_SETTINGS.measurements
NUCLEI_FILTERS = NUCLEI_SETTINGS.filters

EMBRYOS_BORDERS_SMOOTH_ITER = -1
NUCLEI_BORDERS_SMOOTH_ITER = -1
EROSION_THICKNESS = -1

NUCLEI_DILATION += 1  # important to keep nuclei shape since erode will always be -1 (counteracts -1 erosion step)

# the cilia pipeline is identified by any dot being described as cilia (shared flag, so later checks don't rescan dots)
CILIA_DESCRIPTION = 'arl13b'
IS_CILIA_PIPELINE = any(dot_settings.description == CILIA_DESCRIPTION for dot_settings in DOTS_SETTINGS.values())

CYTOPLASM_DESCRIPTION = 'cyt'
CYTOPLASM_SMOOTH_ITER = -1

##############################
# additional settings
##############################

ADDITIONAL_SETTINGS = SETTINGS.additional_toggles

MAP_NUCLEI_TO_IMAGES = ADDITIONAL_SETTINGS.map_nuclei_to_images
ADDITIONAL_SIGNAL_MEASUREMENTS = ADDITIONAL_SETTINGS.signal_measurements
ADDITIONAL_NUCLEI_MEASUREMENTS = ADDITIONAL_SETTINGS.nuclei
ADDITIONAL_DOTS_MEASUREMENTS = ADDITIONAL_SETTINGS.dots

CREATE_EMBRYOS_BORDERS_DFS = ADDITIONAL_SIGNAL_MEASUREMENTS.embryos_border_signal
CREATE_NUCLEI_BORDERS_DFS = ADDITIONAL_SIGNAL_MEASUREMENTS.nuclei_border_signal

CREATE_NUCLEI_PAIRWISE_DISTANCES_DFS = ADDITIONAL_NUCLEI_MEASUREMENTS.pairwise_distances
CREATE_NUCLEI_BORDER_DISTANCES_DF = ADDITIONAL_NUCLEI_MEASUREMENTS.border_distances

# the dots summary input is swapped for the "w_distances" table only when every dot has border distances enabled
# (a partial table would drop the remaining dots' rows from the summary counts/volumes)
DOTS_BORDER_DISTANCES_TOGGLES = [dot_toggles.border_distances for dot_toggles in ADDITIONAL_DOTS_MEASUREMENTS.values()]
CREATE_DOTS_BORDER_DISTANCES_DFS = bool(DOTS_BORDER_DISTANCES_TOGGLES) and all(DOTS_BORDER_DISTANCES_TOGGLES)

CREATE_DOTS_DISTANCES_DF = ADDITIONAL_SETTINGS.calculate_dots_distances
OVERLAP_THRESHOLD = ADDITIONAL_SETTINGS.overlap_threshold

# resolving which two dots' descriptions to compare when calculating dot distances
DOT1_DESCRIPTION = ADDITIONAL_SETTINGS.dots_distance_dot1_description
DOT2_DESCRIPTION = ADDITIONAL_SETTINGS.dots_distance_dot2_description

# resolving which dot-pair matching algorithm to use when calculating dot distances
DOTS_DISTANCE_MODE = ADDITIONAL_SETTINGS.dots_distance_mode

# getting col names
NUCLEI_PAIRWISE_GROUP_COL = 'image_index' if MAP_NUCLEI_TO_IMAGES else 'embryo_id'
DOTS_PAIRWISE_GROUP_COL = 'nucleus_id'

##############################
# cescale
##############################

CESCALE_SETTINGS = SETTINGS.cescale

CESCALE_REFERENCE_FOLDER = CESCALE_SETTINGS.reference_folder
CESCALE_REFERENCE_DATASET = CESCALE_SETTINGS.reference_dataset
CESCALE_CELL_TYPES_PATH = CESCALE_SETTINGS.cell_types_path
CESCALE_GENE_EXPRESSION_PATH = CESCALE_SETTINGS.gene_expression_path
CESCALE_TREE_FILL_COLOR_COL = CESCALE_SETTINGS.tree_fill_color_col
CESCALE_TREE_FILL_COLOR_PALETTE = CESCALE_SETTINGS.tree_fill_color_palette
CESCALE_TREE_EDGE_COLOR_COL = CESCALE_SETTINGS.tree_edge_color_col
CESCALE_TREE_EDGE_COLOR_PALETTE = CESCALE_SETTINGS.tree_edge_color_palette
CESCALE_TREE_EDGE_WIDTH = CESCALE_SETTINGS.tree_edge_width
CESCALE_TREE_SIZE_COL = CESCALE_SETTINGS.tree_size_col
CESCALE_TREE_HOVER_COLS = CESCALE_SETTINGS.tree_hover_cols
CESCALE_TREE_FORMAT = CESCALE_SETTINGS.tree_format

##############################
# pipeline toggles
##############################

PIPELINE_TOGGLES = SETTINGS.pipeline_toggles

RUN_INITIAL_PREPROCESSING = PIPELINE_TOGGLES.initial_preprocessing
RUN_GENERATE_FINAL_TABLES = PIPELINE_TOGGLES.generate_final_tables
RUN_CESCALE = PIPELINE_TOGGLES.run_cescale

EMBRYOS_TOGGLES = PIPELINE_TOGGLES.embryos
NUCLEI_TOGGLES = PIPELINE_TOGGLES.nuclei
CYTOPLASM_TOGGLES = PIPELINE_TOGGLES.cytoplasm
DOTS_TOGGLES = PIPELINE_TOGGLES.dots

RUN_EMBRYOS_IMAGE_PREPROCESSING = EMBRYOS_TOGGLES.image_preprocessing
RUN_EMBRYOS_SEGMENTATION = EMBRYOS_TOGGLES.segmentation
RUN_EMBRYOS_MASKS_POSTPROCESSING = EMBRYOS_TOGGLES.masks_postprocessing
RUN_EMBRYOS_TABLES_CREATION = EMBRYOS_TOGGLES.create_tables
RUN_EMBRYOS_CROPS_CREATION = EMBRYOS_TOGGLES.create_crops

RUN_NUCLEI_IMAGE_PREPROCESSING = NUCLEI_TOGGLES.image_preprocessing
RUN_NUCLEI_SEGMENTATION = NUCLEI_TOGGLES.segmentation
RUN_NUCLEI_MASKS_POSTPROCESSING = NUCLEI_TOGGLES.masks_postprocessing
RUN_NUCLEI_TABLES_CREATION = NUCLEI_TOGGLES.create_tables
RUN_NUCLEI_CROPS_CREATION = NUCLEI_TOGGLES.create_crops

RUN_CYTOPLASM_IMAGE_PREPROCESSING = CYTOPLASM_TOGGLES.image_preprocessing
RUN_CYTOPLASM_SEGMENTATION = CYTOPLASM_TOGGLES.segmentation
RUN_CYTOPLASM_MASKS_POSTPROCESSING = CYTOPLASM_TOGGLES.masks_postprocessing
RUN_CYTOPLASM_TABLES_CREATION = CYTOPLASM_TOGGLES.create_tables

##############################
# runtime toggles
##############################

RUNTIME_SETTINGS = SETTINGS.runtime

SKIP_ENTER = RUNTIME_SETTINGS.skip_enter
OVERWRITE_OUTPUT = RUNTIME_SETTINGS.overwrite_output
SIMULATE_RUN = RUNTIME_SETTINGS.simulate_run
CLEAR_INTERMEDIATE_FILES = RUNTIME_SETTINGS.clear_intermediate_files

######################################################################
# assembling paths

##############################
# base folders
##############################

# CELLPOSE_MODEL_PATH imported from cet.constants above - shared with
# cet.segmentation.run_cellpose's own -p default and cet.setup.download_cp_models's
# download target, so all three always agree

IMGS_FOLDER = join(BASE_FOLDER, 'imgs')
TIFS_FOLDER = join(BASE_FOLDER, 'tifs')
PSFS_FOLDER = join(BASE_FOLDER, 'psfs')
LOG_FOLDER = join(BASE_FOLDER, 'logs')

CHANNELS_FOLDER = join(BASE_FOLDER, 'channels')
IMGS_CHANNELS_FOLDER = join(CHANNELS_FOLDER, 'imgs')
EMBRYOS_CROPS_CHANNELS_FOLDER = join(CHANNELS_FOLDER, 'embryos')
NUCLEI_CROPS_CHANNELS_FOLDER = join(CHANNELS_FOLDER, 'nuclei')

# checking whether to map nuclei to images instead embryos crops
if MAP_NUCLEI_TO_IMAGES:

    # overwriting embryos crops to images reference folder
    # in case image lacks embryos as reference (only nuclei in FOV)
    EMBRYOS_CROPS_CHANNELS_FOLDER = IMGS_CHANNELS_FOLDER

    # removing embryos id from measurements dicts
    NUCLEI_MEASUREMENTS.pop('embryos_crops')

    # removing embryos id from every configured dot's measurements dict
    for dot_settings in DOTS_SETTINGS.values():
        dot_settings.measurements.pop('embryos_crops')

##############################
# channel strings
##############################

EMBRYOS_CHANNEL_STR = f'ch{EMBRYOS_SEGMENTATION_CHANNEL}'
EMBRYOS_DECONV_CHANNEL_STR = f'ch{EMBRYOS_SEGMENTATION_CHANNEL}_deconv'
EMBRYOS_BLUR_CHANNEL_STR = f'ch{EMBRYOS_SEGMENTATION_CHANNEL}_blur'
EMBRYOS_CHANNEL_WAVELENGTH = CHANNEL_WAVELENGTHS[EMBRYOS_CHANNEL_STR]

NUCLEI_CHANNEL_STR = f'ch{NUCLEI_SEGMENTATION_CHANNEL}'
NUCLEI_DECONV_CHANNEL_STR = f'ch{NUCLEI_SEGMENTATION_CHANNEL}_deconv'
NUCLEI_BLUR_CHANNEL_STR = f'ch{NUCLEI_SEGMENTATION_CHANNEL}_blur'
NUCLEI_CHANNEL_WAVELENGTH = CHANNEL_WAVELENGTHS[NUCLEI_CHANNEL_STR]

EMBRYOS_PSF_FILE = f'psf_{EMBRYOS_CHANNEL_WAVELENGTH}.tif'
NUCLEI_PSF_FILE = f'psf_{NUCLEI_CHANNEL_WAVELENGTH}.tif'

EMBRYOS_PSF_PATH = join(PSFS_FOLDER, EMBRYOS_PSF_FILE)
NUCLEI_PSF_PATH = join(PSFS_FOLDER, NUCLEI_PSF_FILE)

##############################
# channel folders
##############################

EMBRYOS_CHANNEL_FOLDER = join(IMGS_CHANNELS_FOLDER, EMBRYOS_CHANNEL_STR)
EMBRYOS_DECONV_CHANNEL_FOLDER = join(IMGS_CHANNELS_FOLDER, EMBRYOS_DECONV_CHANNEL_STR)
EMBRYOS_BLUR_CHANNEL_FOLDER = join(IMGS_CHANNELS_FOLDER, EMBRYOS_BLUR_CHANNEL_STR)

##############################
# crops folders
##############################

CROPS_FOLDER = join(BASE_FOLDER, 'crops')
EMBRYOS_CROPS_FOLDER = join(CROPS_FOLDER, 'embryos')
NUCLEI_CROPS_FOLDER = join(CROPS_FOLDER, 'nuclei')

EMBRYO_CROP_NUCLEI_CHANNEL_FOLDER = join(EMBRYOS_CROPS_CHANNELS_FOLDER, NUCLEI_CHANNEL_STR)
EMBRYO_CROP_NUCLEI_DECONV_CHANNEL_FOLDER = join(EMBRYOS_CROPS_CHANNELS_FOLDER, NUCLEI_DECONV_CHANNEL_STR)
EMBRYO_CROP_NUCLEI_BLUR_CHANNEL_FOLDER = join(EMBRYOS_CROPS_CHANNELS_FOLDER, NUCLEI_BLUR_CHANNEL_STR)

##############################
# masks folders
##############################

MASKS_FOLDER = join(BASE_FOLDER, 'masks')

EMBRYOS_MASKS_FOLDER = join(MASKS_FOLDER, 'embryos')
EMBRYOS_MASKS_CLOSED_FOLDER = join(MASKS_FOLDER, 'embryos_closed')
EMBRYOS_MASKS_MERGED_FOLDER = join(MASKS_FOLDER, 'embryos_merged')
EMBRYOS_MASKS_RESIZED_FOLDER = join(MASKS_FOLDER, 'embryos_resized')
EMBRYOS_MASKS_CROPS_FOLDER = join(MASKS_FOLDER, 'embryos_crops')

NUCLEI_MASKS_FOLDER = join(MASKS_FOLDER, 'nuclei')
NUCLEI_MASKS_CLOSED_FOLDER = join(MASKS_FOLDER, 'nuclei_closed')
NUCLEI_MASKS_MERGED_FOLDER = join(MASKS_FOLDER, 'nuclei_merged')
NUCLEI_MASKS_RESIZED_FOLDER = join(MASKS_FOLDER, 'nuclei_resized')
NUCLEI_MASKS_CROPS_FOLDER = join(MASKS_FOLDER, 'nuclei_crops')

EMBRYOS_MASKS_DILATED_FOLDER = join(MASKS_FOLDER, 'embryos_dilated')
EMBRYOS_MASKS_ERODED_FOLDER = join(MASKS_FOLDER, 'embryos_eroded')

NUCLEI_MASKS_DILATED_FOLDER = join(MASKS_FOLDER, 'nuclei_dilated')
NUCLEI_MASKS_ERODED_FOLDER = join(MASKS_FOLDER, 'nuclei_eroded')

EMBRYOS_BORDERS_MASKS_FOLDER = join(MASKS_FOLDER, 'embryos_borders')
NUCLEI_BORDERS_MASKS_FOLDER = join(MASKS_FOLDER, 'nuclei_borders')

CYTOPLASM_MASKS_FOLDER = join(MASKS_FOLDER, 'cytoplasm')

DOTS_MASKS_FOLDER = join(MASKS_FOLDER, 'dots')

##############################
# dataframes folders
##############################

DFS_FOLDER = join(BASE_FOLDER, 'dataframes')
OBJECTS_DFS_FOLDER = join(DFS_FOLDER, 'objects')
DISTANCES_DFS_FOLDER = join(DFS_FOLDER, 'distances')
JOINED_DFS_FOLDER = join(DFS_FOLDER, 'joined')
SUMMARY_DFS_FOLDER = join(DFS_FOLDER, 'summary')
LINEAGES_FOLDER = join(BASE_FOLDER, 'lineage')

EMBRYOS_OBJECTS_DFS_FOLDER = join(OBJECTS_DFS_FOLDER, 'embryos')
EMBRYOS_BORDERS_OBJECTS_DFS_FOLDER = join(OBJECTS_DFS_FOLDER, 'embryos_borders')
NUCLEI_OBJECTS_DFS_FOLDER = join(OBJECTS_DFS_FOLDER, 'nuclei')
NUCLEI_BORDERS_OBJECTS_DFS_FOLDER = join(OBJECTS_DFS_FOLDER, 'nuclei_borders')
CYTOPLASM_OBJECTS_DFS_FOLDER = join(OBJECTS_DFS_FOLDER, 'cytoplasm')

DOTS_OBJECTS_DFS_FOLDER = join(OBJECTS_DFS_FOLDER, 'dots')

EMBRYOS_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'embryos_joined_df.csv')
EMBRYOS_BORDERS_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'embryos_borders_joined_df.csv')
NUCLEI_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'nuclei_joined_df.csv')
NUCLEI_BORDERS_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'nuclei_borders_joined_df.csv')
CYTOPLASM_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'cytoplasm_joined_df.csv')

DOTS_JOINED_DFS_FOLDER = join(JOINED_DFS_FOLDER, 'dots')
DOTS_JOINED_DFS_W_DISTANCES_FOLDER = join(JOINED_DFS_FOLDER, 'dots_w_border_distances')
DOTS_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'dots_joined_df.csv')

PAIRWISE_DISTANCES_DFS_FOLDER = join(DISTANCES_DFS_FOLDER, 'pairwise')

NUCLEI_PAIRWISE_DISTANCES_DFS_FOLDER = join(PAIRWISE_DISTANCES_DFS_FOLDER, 'nuclei')
NUCLEI_PAIRWISE_DISTANCES_DF_PATH = join(JOINED_DFS_FOLDER, 'nuclei_pairwise_distances_joined_df.csv')

DOTS_PAIRWISE_DISTANCES_DFS_FOLDER = join(PAIRWISE_DISTANCES_DFS_FOLDER, 'dots')

# NUCLEI_BORDER_DISTANCES_DF_PATH = join(JOINED_DFS_FOLDER, 'nuclei_joined_df_w_border_distances.csv')
# TODO: temporary fix! Only because generate_mask_distances_df does not yet support embryo_id as input (hardcoded embryo+nucleus id inner loop)
NUCLEI_BORDER_DISTANCES_DF_PATH = join(JOINED_DFS_FOLDER, 'nuclei_joined_df.csv')
DOTS_BORDER_DISTANCES_DF_PATH = join(JOINED_DFS_FOLDER, 'dots_joined_df_w_border_distances.csv')

DOTS_DISTANCES_DFS_FOLDER = join(DISTANCES_DFS_FOLDER, 'dots_distances')
DOTS_DISTANCES_DF_PATH = join(JOINED_DFS_FOLDER, 'dots_distances_df.csv')

EMBRYOS_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'embryos_summary_df.csv')
NUCLEI_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'nuclei_summary_df.csv')
DOTS_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'dots_summary_df.csv')
CYTOPLASM_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'cytoplasm_summary_df.csv')
CILIA_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'cilia_summary_df.csv')
EMBRYOS_NORMALIZED_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'embryos_summary_df_normalized.csv')
NUCLEI_NORMALIZED_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'nuclei_summary_df_normalized.csv')
DOTS_NORMALIZED_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'dots_summary_df_normalized.csv')
CYTOPLASM_NORMALIZED_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'cytoplasm_summary_df_normalized.csv')
NUCLEI_CESCALE_INPUT_PATH = join(SUMMARY_DFS_FOLDER, 'cescale_input.csv')
LINEAGES_JOINED_DF_PATH = join(JOINED_DFS_FOLDER, 'lineages_joined_df.csv')
NUCLEI_LINEAGES_DF_PATH = join(SUMMARY_DFS_FOLDER, 'nuclei_lineages_df.csv')
NUCLEI_LINEAGE_SUMMARY_DF_PATH = join(SUMMARY_DFS_FOLDER, 'lineage_summary_df.csv')

##############################
# dynamic input folders
##############################

EMBRYOS_BLUR_INPUT_CHANNEL_FOLDER = (
    EMBRYOS_DECONV_CHANNEL_FOLDER if DECONVOLVE_EMBRYOS_CHANNEL else
    EMBRYOS_CHANNEL_FOLDER
)

NUCLEI_BLUR_INPUT_CHANNEL_FOLDER = (
    EMBRYO_CROP_NUCLEI_DECONV_CHANNEL_FOLDER if DECONVOLVE_NUCLEI_CHANNEL else
    EMBRYO_CROP_NUCLEI_CHANNEL_FOLDER
)

EMBRYOS_SEGMENT_INPUT_CHANNEL_FOLDER = (
    EMBRYOS_BLUR_CHANNEL_FOLDER if BLUR_EMBRYOS_CHANNEL else
    EMBRYOS_DECONV_CHANNEL_FOLDER if DECONVOLVE_EMBRYOS_CHANNEL else
    EMBRYOS_CHANNEL_FOLDER
)

NUCLEI_SEGMENT_INPUT_CHANNEL_FOLDER = (
    EMBRYO_CROP_NUCLEI_BLUR_CHANNEL_FOLDER if BLUR_NUCLEI_CHANNEL else
    EMBRYO_CROP_NUCLEI_DECONV_CHANNEL_FOLDER if DECONVOLVE_NUCLEI_CHANNEL else
    EMBRYO_CROP_NUCLEI_CHANNEL_FOLDER
)

EMBRYOS_MERGE_INPUT_FOLDER = (
    EMBRYOS_MASKS_CLOSED_FOLDER if CLOSE_EMBRYOS_MASKS else
    EMBRYOS_MASKS_FOLDER
)

NUCLEI_MERGE_INPUT_FOLDER = (
    NUCLEI_MASKS_CLOSED_FOLDER if CLOSE_NUCLEI_MASKS else
    NUCLEI_MASKS_FOLDER
)

EMBRYOS_RESIZE_INPUT_FOLDER = (
    EMBRYOS_MASKS_MERGED_FOLDER if MERGE_EMBRYOS_MASKS else
    EMBRYOS_MASKS_CLOSED_FOLDER if CLOSE_EMBRYOS_MASKS else
    EMBRYOS_MASKS_FOLDER
)

NUCLEI_RESIZE_INPUT_FOLDER = (
    NUCLEI_MASKS_MERGED_FOLDER if MERGE_NUCLEI_MASKS else
    NUCLEI_MASKS_CLOSED_FOLDER if CLOSE_NUCLEI_MASKS else
    NUCLEI_MASKS_FOLDER
)

EMBRYOS_FINAL_MASKS_FOLDER = (
    EMBRYOS_MASKS_RESIZED_FOLDER if RESIZE_EMBRYOS_MASKS else
    EMBRYOS_MASKS_MERGED_FOLDER if MERGE_EMBRYOS_MASKS else
    EMBRYOS_MASKS_CLOSED_FOLDER if CLOSE_EMBRYOS_MASKS else
    EMBRYOS_MASKS_FOLDER
)

EMBRYOS_BORDERS_FINAL_MASKS_FOLDER = (
    EMBRYOS_BORDERS_MASKS_FOLDER
)

NUCLEI_FINAL_MASKS_FOLDER = (
    NUCLEI_MASKS_RESIZED_FOLDER if RESIZE_NUCLEI_MASKS else
    NUCLEI_MASKS_MERGED_FOLDER if MERGE_NUCLEI_MASKS else
    NUCLEI_MASKS_CLOSED_FOLDER if CLOSE_NUCLEI_MASKS else
    NUCLEI_MASKS_FOLDER
)

# input of the nuclei objects table only: the mask folder selected in the nuclei "Link to masks" setting
# (a nuclei* key in the nuclei measurements, removed here as it is not a measurement), else the automatic one
NUCLEI_LINKED_MASK_KEYS = [key for key in NUCLEI_MEASUREMENTS if key in NUCLEI_MASK_NAMES]
for linked_key in NUCLEI_LINKED_MASK_KEYS:
    NUCLEI_MEASUREMENTS.pop(linked_key)
NUCLEI_OBJECTS_DFS_INPUT_FOLDER = (
    join(MASKS_FOLDER, NUCLEI_LINKED_MASK_KEYS[0]) if NUCLEI_LINKED_MASK_KEYS else
    NUCLEI_FINAL_MASKS_FOLDER
)

NUCLEI_BORDERS_FINAL_MASKS_FOLDER = (
    NUCLEI_BORDERS_MASKS_FOLDER
)

CYTOPLASM_FINAL_MASKS_FOLDER = (
    CYTOPLASM_MASKS_FOLDER
)

# inputs of the summary dfs: the tables with border distances columns, when those were generated
SUMMARY_NUCLEI_INPUT_DF_PATH = (
    NUCLEI_BORDER_DISTANCES_DF_PATH if CREATE_NUCLEI_BORDER_DISTANCES_DF else
    NUCLEI_JOINED_DF_PATH
)

SUMMARY_DOTS_INPUT_DF_PATH = (
    DOTS_BORDER_DISTANCES_DF_PATH if CREATE_DOTS_BORDER_DISTANCES_DFS else
    DOTS_JOINED_DF_PATH
)

##############################
# plots folders
##############################

PLOTS_FOLDER = join(BASE_FOLDER, 'plots')

######################################################################
# defining commands

##############################
# modules
##############################

convert_images_module = modules.convert_images_modules[IMAGES_EXTENSION]
split_channels_module = modules.split_channels_module
preprocess_images_module = modules.preprocess_images_module
crop_images_module = modules.crop_images_module
deconvolve_images_module = modules.deconvolve_images_module
create_psfs_module = modules.create_psfs_module
pad_images_module = modules.pad_images_module
gaussian_blur_module = modules.gaussian_blur_module
difference_of_gaussians_module = modules.difference_of_gaussians_module
generate_binary_masks_module = modules.generate_binary_masks_module
generate_segmentation_masks_module = modules.generate_segmentation_masks_module
run_cellpose_module = modules.run_cellpose_module
optimize_bit_depth_module = modules.optimize_bit_depth_module
close_masks_module = modules.close_masks_module
merge_masks_module = modules.merge_masks_module
resize_masks_module = modules.resize_masks_module
apply_masks_module = modules.apply_masks_module
generate_objects_dfs_module = modules.generate_objects_dfs_module
generate_pseudoembryos_df_module = modules.generate_pseudoembryos_df_module
join_dfs_module = modules.join_dfs_module
generate_summary_dfs_module = modules.generate_summary_dfs_module
generate_cilia_summary_df_module = modules.generate_cilia_summary_df_module
normalize_summary_dfs_module = modules.normalize_summary_dfs_module
generate_pairwise_distances_dfs_module = modules.generate_pairwise_distances_dfs_module
generate_mask_distances_df_module = modules.generate_mask_distances_df_module
generate_dots_distances_df_module = modules.generate_dots_distances_df_module
summary_to_cescale_df_module = modules.summary_to_cescale_df_module
generate_lineages_df_module = modules.generate_lineages_df_module
generate_lineage_summary_df_module = modules.generate_lineage_summary_df_module
plot_lineage_tree_module = modules.plot_lineage_tree_module
run_cescale_module = modules.run_cescale_module

##############################
# commands
##############################

# convert images
convert_images = assemble_command(module=convert_images_module,
                                  args={'-i': IMGS_FOLDER,
                                        '-o': TIFS_FOLDER})

# split channels
split_channels_imgs = assemble_command(module=split_channels_module,
                                       args={'-i': TIFS_FOLDER,
                                             '-o': IMGS_CHANNELS_FOLDER})
split_channels_embryos = assemble_command(module=split_channels_module,
                                          args={'-i': EMBRYOS_CROPS_FOLDER,
                                                '-o': EMBRYOS_CROPS_CHANNELS_FOLDER})
split_channels_nuclei = assemble_command(module=split_channels_module,
                                         args={'-i': NUCLEI_CROPS_FOLDER,
                                               '-o': NUCLEI_CROPS_CHANNELS_FOLDER})

# crop images
crop_embryos_images = assemble_command(module=crop_images_module,
                                       args={'-m': EMBRYOS_MARGIN,
                                             '-d': EMBRYOS_JOINED_DF_PATH,
                                             '-i': TIFS_FOLDER,
                                             '-o': EMBRYOS_CROPS_FOLDER})
crop_embryos_masks = assemble_command(module=crop_images_module,
                                      args={'-m': EMBRYOS_MARGIN,
                                            '-d': EMBRYOS_JOINED_DF_PATH,
                                            '-i': EMBRYOS_FINAL_MASKS_FOLDER,
                                            '-o': EMBRYOS_MASKS_CROPS_FOLDER},
                                      flags=['-k'])
crop_nuclei_images = assemble_command(module=crop_images_module,
                                      args={'-m': NUCLEI_MARGIN,
                                            '-d': NUCLEI_JOINED_DF_PATH,
                                            '-i': EMBRYOS_CROPS_FOLDER,
                                            '-o': NUCLEI_CROPS_FOLDER})
crop_nuclei_masks = assemble_command(module=crop_images_module,
                                     args={'-m': NUCLEI_MARGIN,
                                           '-d': NUCLEI_JOINED_DF_PATH,
                                           '-i': NUCLEI_FINAL_MASKS_FOLDER,
                                           '-o': NUCLEI_MASKS_CROPS_FOLDER},
                                     flags=['-k'])

# create psfs
psf_wavelengths = sorted({wavelength for wavelength in CHANNEL_WAVELENGTHS.values() if wavelength})
PSF_WAVELENGTHS_STR = ','.join(str(wavelength) for wavelength in psf_wavelengths)
create_psfs = assemble_command(module=create_psfs_module,
                               args={'-o': PSFS_FOLDER,
                                     '-w': PSF_WAVELENGTHS_STR,
                                     '-n': NUMERICAL_APERTURE,
                                     '-r': REFRACTIVE_INDEX,
                                     '-sd': SCALES_STR})

# deconvolve images
deconvolve_embryos_channel = assemble_command(module=deconvolve_images_module,
                                              args={'-sd': SCALES_STR,
                                                    '-n': NUMERICAL_APERTURE,
                                                    '-r': REFRACTIVE_INDEX,
                                                    '-w': EMBRYOS_CHANNEL_WAVELENGTH,
                                                    '-p': EMBRYOS_PSF_PATH,
                                                    '-i': EMBRYOS_CHANNEL_FOLDER,
                                                    '-o': EMBRYOS_DECONV_CHANNEL_FOLDER})
deconvolve_nuclei_channel = assemble_command(module=deconvolve_images_module,
                                             args={'-sd': SCALES_STR,
                                                   '-n': NUMERICAL_APERTURE,
                                                   '-r': REFRACTIVE_INDEX,
                                                   '-w': NUCLEI_CHANNEL_WAVELENGTH,
                                                   '-p': NUCLEI_PSF_PATH,
                                                   '-i': EMBRYO_CROP_NUCLEI_CHANNEL_FOLDER,
                                                   '-o': EMBRYO_CROP_NUCLEI_DECONV_CHANNEL_FOLDER})

# pad images
pad_embryos_channel = assemble_command(module=pad_images_module,
                                       args={'-i': EMBRYOS_DECONV_CHANNEL_FOLDER,
                                             '-r': EMBRYOS_CHANNEL_FOLDER,
                                             '-o': EMBRYOS_DECONV_CHANNEL_FOLDER},
                                       flags=['-ow'])
pad_nuclei_channel = assemble_command(module=pad_images_module,
                                      args={'-i': EMBRYO_CROP_NUCLEI_DECONV_CHANNEL_FOLDER,
                                            '-r': EMBRYO_CROP_NUCLEI_CHANNEL_FOLDER,
                                            '-o': EMBRYO_CROP_NUCLEI_DECONV_CHANNEL_FOLDER},
                                      flags=['-ow'])

# gaussian blur
blur_embryos_channel = assemble_command(module=gaussian_blur_module,
                                        args={'-g': EMBRYOS_BLUR_SIGMA,
                                              '-i': EMBRYOS_BLUR_INPUT_CHANNEL_FOLDER,
                                              '-o': EMBRYOS_BLUR_CHANNEL_FOLDER})
blur_nuclei_channel = assemble_command(module=gaussian_blur_module,
                                       args={'-g': NUCLEI_BLUR_SIGMA,
                                             '-i': NUCLEI_BLUR_INPUT_CHANNEL_FOLDER,
                                             '-o': EMBRYO_CROP_NUCLEI_BLUR_CHANNEL_FOLDER})

# segment objects
segment_embryos = assemble_command(module=run_cellpose_module,
                                   args={'-sd': SCALES_STR,
                                         '-p': CELLPOSE_MODEL_PATH,
                                         '-z': Z_AXIS,
                                         '-i': EMBRYOS_SEGMENT_INPUT_CHANNEL_FOLDER,
                                         '-o': EMBRYOS_MASKS_FOLDER,
                                         '-t': EMBRYOS_DIAMETER,
                                         '-m': EMBRYOS_MIN_SIZE,
                                         '-b': EMBRYOS_BATCH_SIZE})
segment_nuclei = assemble_command(module=run_cellpose_module,
                                  args={'-sd': SCALES_STR,
                                        '-p': CELLPOSE_MODEL_PATH,
                                        '-z': Z_AXIS,
                                        '-i': NUCLEI_SEGMENT_INPUT_CHANNEL_FOLDER,
                                        '-o': NUCLEI_MASKS_FOLDER,
                                        '-t': NUCLEI_DIAMETER,
                                        '-m': NUCLEI_MIN_SIZE,
                                        '-b': NUCLEI_BATCH_SIZE})

# optimizing bit depths
optimize_bit_depth_embryos = assemble_command(module=optimize_bit_depth_module,
                                              args={'-i': EMBRYOS_MASKS_FOLDER,
                                                    '-o': EMBRYOS_MASKS_FOLDER},
                                              flags=['-ow'])
optimize_bit_depth_nuclei = assemble_command(module=optimize_bit_depth_module,
                                             args={'-i': NUCLEI_MASKS_FOLDER,
                                                   '-o': NUCLEI_MASKS_FOLDER},
                                             flags=['-ow'])

# close masks
close_masks_embryos = assemble_command(module=close_masks_module,
                                       args={'-sd': SCALES_STR,
                                             '-cr': EMBRYOS_CLOSING_DISTANCE,
                                             '-i': EMBRYOS_MASKS_FOLDER,
                                             '-o': EMBRYOS_MASKS_CLOSED_FOLDER})
close_masks_nuclei = assemble_command(module=close_masks_module,
                                      args={'-sd': SCALES_STR,
                                            '-cr': NUCLEI_CLOSING_DISTANCE,
                                            '-i': NUCLEI_MASKS_FOLDER,
                                            '-o': NUCLEI_MASKS_CLOSED_FOLDER})

# merge masks
merge_masks_embryos = assemble_command(module=merge_masks_module,
                                       args={'-sd': SCALES_STR,
                                             '-st': EMBRYOS_MERGE_SOLIDITY_THRESHOLD,
                                             '-tm': EMBRYOS_MERGE_TOUCH_MARGIN,
                                             '-i': EMBRYOS_MERGE_INPUT_FOLDER,
                                             '-o': EMBRYOS_MASKS_MERGED_FOLDER})
merge_masks_nuclei = assemble_command(module=merge_masks_module,
                                      args={'-sd': SCALES_STR,
                                            '-st': NUCLEI_MERGE_SOLIDITY_THRESHOLD,
                                            '-tm': NUCLEI_MERGE_TOUCH_MARGIN,
                                            '-i': NUCLEI_MERGE_INPUT_FOLDER,
                                            '-o': NUCLEI_MASKS_MERGED_FOLDER})

# resize masks
resize_masks_embryos = assemble_command(module=resize_masks_module,
                                        args={'-d': EMBRYOS_DILATION,
                                              '-i': EMBRYOS_RESIZE_INPUT_FOLDER,
                                              '-o': EMBRYOS_MASKS_RESIZED_FOLDER})
resize_masks_nuclei = assemble_command(module=resize_masks_module,
                                       args={'-d': NUCLEI_DILATION,
                                             '-i': NUCLEI_RESIZE_INPUT_FOLDER,
                                             '-o': NUCLEI_MASKS_RESIZED_FOLDER})

# erode/dilate masks
erode_masks_embryos = assemble_command(module=resize_masks_module,
                                       args={'-d': EROSION_THICKNESS,
                                             '-i': EMBRYOS_MASKS_CROPS_FOLDER,
                                             '-o': EMBRYOS_MASKS_ERODED_FOLDER})
dilate_masks_embryos = assemble_command(module=resize_masks_module,
                                        args={'-d': EMBRYOS_BORDERS_THICKNESS,
                                              '-i': EMBRYOS_MASKS_ERODED_FOLDER,
                                              '-o': EMBRYOS_MASKS_DILATED_FOLDER})
erode_masks_nuclei = assemble_command(module=resize_masks_module,
                                      args={'-d': EROSION_THICKNESS,
                                            '-i': NUCLEI_FINAL_MASKS_FOLDER,
                                            '-o': NUCLEI_MASKS_ERODED_FOLDER})
dilate_masks_nuclei = assemble_command(module=resize_masks_module,
                                       args={'-d': NUCLEI_BORDERS_THICKNESS,
                                             '-i': NUCLEI_MASKS_ERODED_FOLDER,
                                             '-o': NUCLEI_MASKS_DILATED_FOLDER})

# apply masks
apply_masks_embryos = assemble_command(module=apply_masks_module,
                                       args={'-i': EMBRYOS_MASKS_DILATED_FOLDER,
                                             '-m': EMBRYOS_MASKS_ERODED_FOLDER,
                                             '-o': EMBRYOS_BORDERS_MASKS_FOLDER},
                                       flags=['-r'])
apply_masks_nuclei = assemble_command(module=apply_masks_module,
                                      args={'-i': NUCLEI_MASKS_DILATED_FOLDER,
                                            '-m': NUCLEI_MASKS_ERODED_FOLDER,
                                            '-o': NUCLEI_BORDERS_MASKS_FOLDER},
                                      flags=['-r'])
apply_masks_cytoplasm = assemble_command(module=apply_masks_module,
                                         args={'-i': EMBRYOS_MASKS_CROPS_FOLDER,
                                               '-m': NUCLEI_FINAL_MASKS_FOLDER,
                                               '-o': CYTOPLASM_MASKS_FOLDER},
                                         flags=['-r'])

# generate objects dfs
embryos_measurements_str = assemble_measurements_str(channels_folder=IMGS_CHANNELS_FOLDER,
                                                     channel_names=CHANNEL_NAMES,
                                                     measurements_dict=EMBRYOS_MEASUREMENTS)
generate_objects_dfs_embryos = assemble_command(module=generate_objects_dfs_module,
                                                args={'-sd': SCALES_STR,
                                                      '-smi': EMBRYOS_SMOOTH_ITER,
                                                      '-i': EMBRYOS_FINAL_MASKS_FOLDER,
                                                      '-p': EMBRYOS_DESCRIPTION,
                                                      '-o': EMBRYOS_OBJECTS_DFS_FOLDER,
                                                      '-c': embryos_measurements_str})

embryos_borders_measurements_str = assemble_measurements_str(channels_folder=EMBRYOS_CROPS_CHANNELS_FOLDER,
                                                             channel_names=CHANNEL_NAMES,
                                                             measurements_dict=EMBRYOS_MEASUREMENTS)
generate_objects_dfs_embryos_borders = assemble_command(module=generate_objects_dfs_module,
                                                        args={'-sd': SCALES_STR,
                                                              '-smi': EMBRYOS_BORDERS_SMOOTH_ITER,
                                                              '-i': EMBRYOS_BORDERS_FINAL_MASKS_FOLDER,
                                                              '-p': EMBRYOS_BORDERS_DESCRIPTION,
                                                              '-o': EMBRYOS_BORDERS_OBJECTS_DFS_FOLDER,
                                                              '-c': embryos_borders_measurements_str})

nuclei_measurements_str = assemble_measurements_str(channels_folder=EMBRYOS_CROPS_CHANNELS_FOLDER,
                                                    masks_folder=MASKS_FOLDER,
                                                    channel_names=CHANNEL_NAMES,
                                                    measurements_dict=NUCLEI_MEASUREMENTS)
generate_objects_dfs_nuclei = assemble_command(module=generate_objects_dfs_module,
                                               args={'-sd': SCALES_STR,
                                                     '-smi': NUCLEI_SMOOTH_ITER,
                                                     '-i': NUCLEI_OBJECTS_DFS_INPUT_FOLDER,
                                                     '-p': NUCLEI_DESCRIPTION,
                                                     '-o': NUCLEI_OBJECTS_DFS_FOLDER,
                                                     '-c': nuclei_measurements_str})
generate_objects_dfs_nuclei_borders = assemble_command(module=generate_objects_dfs_module,
                                                       args={'-sd': SCALES_STR,
                                                             '-smi': NUCLEI_BORDERS_SMOOTH_ITER,
                                                             '-i': NUCLEI_BORDERS_FINAL_MASKS_FOLDER,
                                                             '-p': NUCLEI_BORDERS_DESCRIPTION,
                                                             '-o': NUCLEI_BORDERS_OBJECTS_DFS_FOLDER,
                                                             '-c': nuclei_measurements_str})

cytoplasm_measurements_str = assemble_measurements_str(channels_folder=EMBRYOS_CROPS_CHANNELS_FOLDER,
                                                       masks_folder=MASKS_FOLDER,
                                                       channel_names=CHANNEL_NAMES,
                                                       measurements_dict=EMBRYOS_MEASUREMENTS)
generate_objects_dfs_cytoplasm = assemble_command(module=generate_objects_dfs_module,
                                                  args={'-sd': SCALES_STR,
                                                        '-smi': CYTOPLASM_SMOOTH_ITER,
                                                        '-i': CYTOPLASM_FINAL_MASKS_FOLDER,
                                                        '-p': CYTOPLASM_DESCRIPTION,
                                                        '-o': CYTOPLASM_OBJECTS_DFS_FOLDER,
                                                        '-c': cytoplasm_measurements_str})

# generate pairwise distances dfs
generate_pairwise_distances_dfs_nuclei = assemble_command(module=generate_pairwise_distances_dfs_module,
                                                          args={'-sd': SCALES_STR,
                                                                '-g': NUCLEI_PAIRWISE_GROUP_COL,
                                                                '-i': NUCLEI_JOINED_DF_PATH,
                                                                '-o': NUCLEI_PAIRWISE_DISTANCES_DFS_FOLDER})

# generate border distances dfs
generate_border_distances_df_nuclei = assemble_command(module=generate_mask_distances_df_module,
                                                       args={'-sd': SCALES_STR,
                                                             '-m': EMBRYOS_BORDERS_MASKS_FOLDER,
                                                             '-n': EMBRYOS_BORDERS_DESCRIPTION,
                                                             '-i': NUCLEI_JOINED_DF_PATH,
                                                             '-o': NUCLEI_BORDER_DISTANCES_DF_PATH})

# generate dots distances df
generate_dots_distances_df = assemble_command(module=generate_dots_distances_df_module,
                                              args={'-sd': SCALES_STR,
                                                    '-t': OVERLAP_THRESHOLD,
                                                    '-d1': DOT1_DESCRIPTION,
                                                    '-d2': DOT2_DESCRIPTION,
                                                    '-m': DOTS_DISTANCE_MODE,
                                                    '-i': DOTS_JOINED_DF_PATH,
                                                    '-o': DOTS_DISTANCES_DFS_FOLDER})

# join dfs
join_dfs_embryos = assemble_command(module=join_dfs_module,
                                    args={'-i': EMBRYOS_OBJECTS_DFS_FOLDER,
                                          '-o': EMBRYOS_JOINED_DF_PATH})
join_dfs_embryos_borders = assemble_command(module=join_dfs_module,
                                            args={'-i': EMBRYOS_BORDERS_OBJECTS_DFS_FOLDER,
                                                  '-o': EMBRYOS_BORDERS_JOINED_DF_PATH})
join_dfs_nuclei = assemble_command(module=join_dfs_module,
                                   args={'-i': NUCLEI_OBJECTS_DFS_FOLDER,
                                         '-o': NUCLEI_JOINED_DF_PATH})
join_dfs_nuclei_borders = assemble_command(module=join_dfs_module,
                                           args={'-i': NUCLEI_BORDERS_OBJECTS_DFS_FOLDER,
                                                 '-o': NUCLEI_BORDERS_JOINED_DF_PATH})
join_dfs_nuclei_pairwise_distances = assemble_command(module=join_dfs_module,
                                                      args={'-i': NUCLEI_PAIRWISE_DISTANCES_DFS_FOLDER,
                                                            '-o': NUCLEI_PAIRWISE_DISTANCES_DF_PATH})
join_dfs_cytoplasm = assemble_command(module=join_dfs_module,
                                      args={'-i': CYTOPLASM_OBJECTS_DFS_FOLDER,
                                            '-o': CYTOPLASM_JOINED_DF_PATH})
join_dfs_dots = assemble_command(module=join_dfs_module,
                                 args={'-i': DOTS_JOINED_DFS_FOLDER,
                                       '-o': DOTS_JOINED_DF_PATH})
join_dfs_dots_w_distances = assemble_command(module=join_dfs_module,
                                             args={'-i': DOTS_JOINED_DFS_W_DISTANCES_FOLDER,
                                                   '-o': DOTS_BORDER_DISTANCES_DF_PATH})
join_dfs_dots_distances = assemble_command(module=join_dfs_module,
                                           args={'-i': DOTS_DISTANCES_DFS_FOLDER,
                                                 '-o': DOTS_DISTANCES_DF_PATH})
join_dfs_cescale = assemble_command(module=join_dfs_module,
                                    args={'-i': LINEAGES_FOLDER,
                                          '-o': LINEAGES_JOINED_DF_PATH})

# generate pseudoembryos df
generate_pseudoembryos_df = assemble_command(module=generate_pseudoembryos_df_module,
                                             args={'-i': NUCLEI_FINAL_MASKS_FOLDER,
                                                   '-o': EMBRYOS_JOINED_DF_PATH})

# dots (looped over every configured dot - supports any number of dots)

# defining placeholders for per-dot folder/path collectors (flattened by get_subfolders_list)
EMBRYO_CROP_DOT_CHANNEL_FOLDERS = {}
EMBRYO_CROP_DOT_DECONV_CHANNEL_FOLDERS = {}
EMBRYO_CROP_DOT_BLUR_CHANNEL_FOLDERS = {}
DOT_MASKS_FOLDERS = {}
DOT_OBJECTS_DFS_FOLDERS = {}
DOT_JOINED_DF_PATHS = {}
DOT_PAIRWISE_DISTANCES_DFS_FOLDERS = {}
DOT_PAIRWISE_DISTANCES_DF_PATHS = {}
DOT_BORDER_DISTANCES_DF_PATHS = {}

# defining placeholder for the key of the dot described as cilia (None if there is none)
CILIA_DOT_KEY = None

# defining placeholder for per-dot toggle-gated stage command lists
DOT_STAGE_COMMANDS = {}

# getting dots settings dict items
dots_settings_dict_items = DOTS_SETTINGS.items()

# iterating over every configured dot
for dot_settings_item in dots_settings_dict_items:

    # getting current dot key/settings
    dot_key, dot_settings = dot_settings_item

    # getting current dot's additional measurement toggles
    dot_additional_measurements = ADDITIONAL_DOTS_MEASUREMENTS[dot_key]

    # getting current dot channel strings/wavelength/psf path
    dot_channel_str = f'ch{dot_settings.segmentation_channel}'
    dot_deconv_channel_str = f'ch{dot_settings.segmentation_channel}_deconv'
    dot_blur_channel_str = f'ch{dot_settings.segmentation_channel}_blur'
    dot_channel_wavelength = CHANNEL_WAVELENGTHS[dot_channel_str]
    dot_psf_file = f'psf_{dot_channel_wavelength}.tif'
    dot_psf_path = join(PSFS_FOLDER, dot_psf_file)

    # getting current dot channel folders
    dot_channel_folder = join(EMBRYOS_CROPS_CHANNELS_FOLDER, dot_channel_str)
    dot_deconv_channel_folder = join(EMBRYOS_CROPS_CHANNELS_FOLDER, dot_deconv_channel_str)
    dot_blur_channel_folder = join(EMBRYOS_CROPS_CHANNELS_FOLDER, dot_blur_channel_str)
    EMBRYO_CROP_DOT_CHANNEL_FOLDERS[dot_key] = dot_channel_folder
    EMBRYO_CROP_DOT_DECONV_CHANNEL_FOLDERS[dot_key] = dot_deconv_channel_folder
    EMBRYO_CROP_DOT_BLUR_CHANNEL_FOLDERS[dot_key] = dot_blur_channel_folder

    # getting current dot masks folder
    dot_masks_folder = join(DOTS_MASKS_FOLDER, dot_settings.description)
    DOT_MASKS_FOLDERS[dot_key] = dot_masks_folder

    # getting current dot dataframes folders/paths
    dot_objects_dfs_folder = join(DOTS_OBJECTS_DFS_FOLDER, dot_settings.description)
    dot_joined_df_path = join(DOTS_JOINED_DFS_FOLDER, f'{dot_settings.description}_joined_df.csv')
    dot_pairwise_distances_dfs_folder = join(DOTS_PAIRWISE_DISTANCES_DFS_FOLDER, dot_settings.description)
    dot_pairwise_distances_df_path = join(JOINED_DFS_FOLDER, f'{dot_settings.description}_pairwise_distances_joined_df.csv')
    dot_border_distances_df_path = join(DOTS_JOINED_DFS_W_DISTANCES_FOLDER, f'{dot_settings.description}_{NUCLEI_BORDERS_DESCRIPTION}_distances_df.csv')
    DOT_OBJECTS_DFS_FOLDERS[dot_key] = dot_objects_dfs_folder
    DOT_JOINED_DF_PATHS[dot_key] = dot_joined_df_path
    DOT_PAIRWISE_DISTANCES_DFS_FOLDERS[dot_key] = dot_pairwise_distances_dfs_folder
    DOT_PAIRWISE_DISTANCES_DF_PATHS[dot_key] = dot_pairwise_distances_df_path
    DOT_BORDER_DISTANCES_DF_PATHS[dot_key] = dot_border_distances_df_path

    # checking whether current dot is the cilia dot
    if dot_settings.description == CILIA_DESCRIPTION:
        CILIA_DOT_KEY = dot_key

    # getting current dot filter list
    dot_filters = dot_settings.filters

    # getting current dot dynamic input folders
    dot_blur_input_channel_folder = (
        dot_deconv_channel_folder if dot_settings.deconvolve else
        dot_channel_folder
    )
    dot_segment_input_channel_folder = (
        dot_blur_channel_folder if (dot_settings.blur or dot_settings.dog) else
        dot_deconv_channel_folder if dot_settings.deconvolve else
        dot_channel_folder
    )

    # deconvolve/pad current dot channel
    deconvolve_dot_channel = assemble_command(module=deconvolve_images_module,
                                              args={'-sd': SCALES_STR,
                                                    '-n': NUMERICAL_APERTURE,
                                                    '-r': REFRACTIVE_INDEX,
                                                    '-w': dot_channel_wavelength,
                                                    '-p': dot_psf_path,
                                                    '-i': dot_channel_folder,
                                                    '-o': dot_deconv_channel_folder})
    pad_dot_channel = assemble_command(module=pad_images_module,
                                       args={'-i': dot_deconv_channel_folder,
                                             '-r': dot_channel_folder,
                                             '-o': dot_deconv_channel_folder},
                                       flags=['-ow'])

    # blur/dog current dot channel
    blur_dot_channel = assemble_command(module=gaussian_blur_module,
                                        args={'-g': dot_settings.blur_sigma,
                                              '-i': dot_blur_input_channel_folder,
                                              '-o': dot_blur_channel_folder})
    dog_dot_channel = assemble_command(module=difference_of_gaussians_module,
                                       args={'-i': dot_blur_input_channel_folder,
                                             '-o': dot_blur_channel_folder,
                                             '-lg': dot_settings.blur_sigma_low,
                                             '-hg': dot_settings.blur_sigma_high})

    # segment current dot
    generate_binary_masks_dot = assemble_command(module=generate_binary_masks_module,
                                                 args={'-i': dot_segment_input_channel_folder,
                                                       '-o': dot_masks_folder,
                                                       '-m': dot_settings.segmentation_mode,
                                                       '-lt': dot_settings.lower_threshold,
                                                       '-ut': dot_settings.upper_threshold},
                                                 flags=['-p'])
    generate_segmentation_masks_dot = assemble_command(module=generate_segmentation_masks_module,
                                                       args={'-i': dot_masks_folder,
                                                             '-o': dot_masks_folder},
                                                       flags=['-ow'])

    # optimize current dot's masks bit depth
    optimize_bit_depth_dot = assemble_command(module=optimize_bit_depth_module,
                                              args={'-i': dot_masks_folder,
                                                    '-o': dot_masks_folder},
                                              flags=['-ow'])

    # generate current dot's objects df
    dot_measurements_str = assemble_measurements_str(channels_folder=EMBRYOS_CROPS_CHANNELS_FOLDER,
                                                     masks_folder=MASKS_FOLDER,
                                                     channel_names=CHANNEL_NAMES,
                                                     measurements_dict=dot_settings.measurements)

    # adding overlap with nuclei borders masks to current dot's measurements (only if those masks are created)
    dot_overlap_entry = f'{NUCLEI_BORDERS_DESCRIPTION}#overlap@{NUCLEI_BORDERS_FINAL_MASKS_FOLDER}'
    if CREATE_NUCLEI_BORDERS_MASKS:
        dot_measurements_str = ','.join(filter(None, [dot_measurements_str, dot_overlap_entry]))
    generate_objects_dfs_dot =assemble_command(module=generate_objects_dfs_module,
                                                args={'-sd': SCALES_STR,
                                                      '-smi': dot_settings.smooth_iterations,
                                                      '-i': dot_masks_folder,
                                                      '-p': dot_settings.description,
                                                      '-o': dot_objects_dfs_folder,
                                                      '-c': dot_measurements_str})
    join_dfs_dot = assemble_command(module=join_dfs_module,
                                    args={'-i': dot_objects_dfs_folder,
                                          '-o': dot_joined_df_path})

    # generate current dot's pairwise/border distances dfs
    generate_pairwise_distances_dfs_dot = assemble_command(module=generate_pairwise_distances_dfs_module,
                                                           args={'-sd': SCALES_STR,
                                                                 '-g': DOTS_PAIRWISE_GROUP_COL,
                                                                 '-i': dot_joined_df_path,
                                                                 '-o': dot_pairwise_distances_dfs_folder})
    join_dfs_dot_pairwise_distances = assemble_command(module=join_dfs_module,
                                                       args={'-i': dot_pairwise_distances_dfs_folder,
                                                             '-o': dot_pairwise_distances_df_path})
    generate_border_distances_df_dot = assemble_command(module=generate_mask_distances_df_module,
                                                        args={'-sd': SCALES_STR,
                                                              '-m': NUCLEI_BORDERS_MASKS_FOLDER,
                                                              '-n': NUCLEI_BORDERS_DESCRIPTION,
                                                              '-i': dot_joined_df_path,
                                                              '-o': dot_border_distances_df_path})

    # getting current table filters commands list
    filter_commands = assemble_filter_commands(df_path=dot_joined_df_path,
                                               filters=dot_filters)

    # building current dot's toggle-gated stage command lists
    dot_image_preprocessing_commands = []
    dot_segmentation_commands = [generate_binary_masks_dot,
                                 generate_segmentation_masks_dot]
    dot_masks_postprocessing_commands = [optimize_bit_depth_dot]
    dot_tables_creation_commands = [generate_objects_dfs_dot,
                                    join_dfs_dot]
    dot_tables_creation_commands.extend(filter_commands)
    if dot_settings.deconvolve:
        check_wavelength_set(channel_str=dot_channel_str, channel_wavelengths=CHANNEL_WAVELENGTHS)
        dot_image_preprocessing_commands.append(deconvolve_dot_channel)
        dot_image_preprocessing_commands.append(pad_dot_channel)
    if dot_settings.blur:
        dot_image_preprocessing_commands.append(blur_dot_channel)
    if dot_settings.dog:
        dot_image_preprocessing_commands.append(dog_dot_channel)
    if dot_additional_measurements.pairwise_distances:
        dot_tables_creation_commands.append(generate_pairwise_distances_dfs_dot)
        dot_tables_creation_commands.append(join_dfs_dot_pairwise_distances)
    if dot_additional_measurements.border_distances:
        dot_tables_creation_commands.append(generate_border_distances_df_dot)

    # storing current dot's stage commands, keyed by dot key
    DOT_STAGE_COMMANDS[dot_key] = {'image_preprocessing': dot_image_preprocessing_commands,
                                   'segmentation': dot_segmentation_commands,
                                   'masks_postprocessing': dot_masks_postprocessing_commands,
                                   'create_tables': dot_tables_creation_commands}

# generate summary dfs
generate_summary_dfs_args = {'-e': EMBRYOS_JOINED_DF_PATH,
                             '-n': SUMMARY_NUCLEI_INPUT_DF_PATH,
                             '-d': SUMMARY_DOTS_INPUT_DF_PATH,
                             '-bd': NUCLEI_BORDERS_DESCRIPTION,
                             '-o': SUMMARY_DFS_FOLDER}
if RUN_CYTOPLASM_TABLES_CREATION:
    current_dict = {'-c': CYTOPLASM_JOINED_DF_PATH}
    generate_summary_dfs_args.update(current_dict)
generate_summary_dfs = assemble_command(module=generate_summary_dfs_module,
                                        args=generate_summary_dfs_args)

# generate cilia summary df (only when one of the dots is described as cilia)
if IS_CILIA_PIPELINE:
    cilia_pairwise_distances_toggle = ADDITIONAL_DOTS_MEASUREMENTS[CILIA_DOT_KEY].pairwise_distances
    generate_cilia_summary_df_args = {'-n': NUCLEI_SUMMARY_DF_PATH,
                                      '-nd': NUCLEI_PAIRWISE_DISTANCES_DF_PATH,
                                      '-c': DOT_JOINED_DF_PATHS[CILIA_DOT_KEY],
                                      '-cd': DOT_PAIRWISE_DISTANCES_DF_PATHS[CILIA_DOT_KEY],
                                      '-o': CILIA_SUMMARY_DF_PATH}
    generate_cilia_summary_df = assemble_command(module=generate_cilia_summary_df_module,
                                                 args=generate_cilia_summary_df_args)

# normalize summary dfs
normalize_summary_dfs_args = {'-e': EMBRYOS_SUMMARY_DF_PATH,
                              '-n': NUCLEI_SUMMARY_DF_PATH,
                              '-d': DOTS_SUMMARY_DF_PATH,
                              '-bd': NUCLEI_BORDERS_DESCRIPTION,
                              '-o': SUMMARY_DFS_FOLDER}
if RUN_CYTOPLASM_TABLES_CREATION:
    current_dict = {'-c': CYTOPLASM_SUMMARY_DF_PATH}
    normalize_summary_dfs_args.update(current_dict)
normalize_summary_dfs = assemble_command(module=normalize_summary_dfs_module,
                                         args=normalize_summary_dfs_args)

# df conversions
summary_to_cescale_df = assemble_command(module=summary_to_cescale_df_module,
                                         args={'-i': NUCLEI_NORMALIZED_SUMMARY_DF_PATH,
                                               '-o': NUCLEI_CESCALE_INPUT_PATH})
run_cescale_args = {'-i': NUCLEI_CESCALE_INPUT_PATH,
                    '-rd': CESCALE_REFERENCE_DATASET,
                    '-is': SCALES_STR,
                    '-o': LINEAGES_FOLDER}
if CESCALE_REFERENCE_FOLDER:
    current_dict = {'-r': CESCALE_REFERENCE_FOLDER}
    run_cescale_args.update(current_dict)
run_cescale = assemble_command(module=run_cescale_module,
                               args=run_cescale_args)
generate_lineages_df_args = {'-i': NUCLEI_NORMALIZED_SUMMARY_DF_PATH,
                             '-c': LINEAGES_JOINED_DF_PATH,
                             '-o': NUCLEI_LINEAGES_DF_PATH}
if CESCALE_CELL_TYPES_PATH:
    current_dict = {'-t': CESCALE_CELL_TYPES_PATH}
    generate_lineages_df_args.update(current_dict)
if CESCALE_GENE_EXPRESSION_PATH:
    current_dict = {'-g': CESCALE_GENE_EXPRESSION_PATH}
    generate_lineages_df_args.update(current_dict)
generate_lineages_df = assemble_command(module=generate_lineages_df_module,
                                        args=generate_lineages_df_args)
generate_lineage_summary_df = assemble_command(module=generate_lineage_summary_df_module,
                                               args={'-i': NUCLEI_LINEAGES_DF_PATH,
                                                     '-o': NUCLEI_LINEAGE_SUMMARY_DF_PATH})
plot_lineage_tree_args = {'-i': NUCLEI_LINEAGE_SUMMARY_DF_PATH,
                          '-o': PLOTS_FOLDER,
                          '-f': CESCALE_TREE_FORMAT,
                          '-fc': CESCALE_TREE_FILL_COLOR_COL,
                          '-fcp': CESCALE_TREE_FILL_COLOR_PALETTE,
                          '-ecp': CESCALE_TREE_EDGE_COLOR_PALETTE,
                          '-sc': CESCALE_TREE_SIZE_COL}
if CESCALE_TREE_EDGE_COLOR_COL:
    current_dict = {'-ec': CESCALE_TREE_EDGE_COLOR_COL}
    plot_lineage_tree_args.update(current_dict)
if CESCALE_TREE_EDGE_WIDTH is not None:
    current_dict = {'-ew': CESCALE_TREE_EDGE_WIDTH}
    plot_lineage_tree_args.update(current_dict)  # noqa
# -hc is nargs='+' (not a repeatable flag), so it goes through flags instead of args
plot_lineage_tree_flags = ['-hc'] + CESCALE_TREE_HOVER_COLS if CESCALE_TREE_HOVER_COLS else None
plot_lineage_tree = assemble_command(module=plot_lineage_tree_module,
                                     args=plot_lineage_tree_args,
                                     flags=plot_lineage_tree_flags)

######################################################################
# assembling commands list

##############################
# base lists
##############################

# assembling initial preprocessing commands list
initial_preprocessing_commands = [create_psfs,
                                  convert_images,
                                  split_channels_imgs]

# embryos

# getting embryos table filters commands list
embryos_filter_commands = assemble_filter_commands(df_path=EMBRYOS_JOINED_DF_PATH,
                                                   filters=EMBRYOS_FILTERS)
embryos_image_preprocessing_commands = []
embryos_segmentation_commands = [segment_embryos]
embryos_masks_postprocessing_commands = [optimize_bit_depth_embryos]
embryos_tables_creation_commands = [generate_objects_dfs_embryos,
                                    join_dfs_embryos]
embryos_tables_creation_commands.extend(embryos_filter_commands)
embryos_crops_creation_commands = [crop_embryos_images,
                                   crop_embryos_masks,
                                   split_channels_embryos]
if DECONVOLVE_EMBRYOS_CHANNEL:
    check_wavelength_set(channel_str=EMBRYOS_CHANNEL_STR, channel_wavelengths=CHANNEL_WAVELENGTHS)
    embryos_image_preprocessing_commands.append(deconvolve_embryos_channel)
    embryos_image_preprocessing_commands.append(pad_embryos_channel)
if BLUR_EMBRYOS_CHANNEL:
    embryos_image_preprocessing_commands.append(blur_embryos_channel)
if CLOSE_EMBRYOS_MASKS:
    embryos_masks_postprocessing_commands.append(close_masks_embryos)
if MERGE_EMBRYOS_MASKS:
    embryos_masks_postprocessing_commands.append(merge_masks_embryos)
if RESIZE_EMBRYOS_MASKS:
    embryos_masks_postprocessing_commands.append(resize_masks_embryos)
if CREATE_EMBRYOS_BORDERS_MASKS:
    embryos_crops_creation_commands.append(erode_masks_embryos)
    embryos_crops_creation_commands.append(dilate_masks_embryos)
    embryos_crops_creation_commands.append(apply_masks_embryos)
if CREATE_EMBRYOS_BORDERS_DFS:
    embryos_crops_creation_commands.append(generate_objects_dfs_embryos_borders)
    embryos_crops_creation_commands.append(join_dfs_embryos_borders)

# nuclei

# getting nuclei table filters commands list
nuclei_filter_commands = assemble_filter_commands(df_path=NUCLEI_JOINED_DF_PATH,
                                                  filters=NUCLEI_FILTERS)
nuclei_image_preprocessing_commands = []
nuclei_segmentation_commands = [segment_nuclei]
nuclei_masks_postprocessing_commands = [optimize_bit_depth_nuclei]
nuclei_tables_creation_commands = [generate_objects_dfs_nuclei,
                                   join_dfs_nuclei]
nuclei_tables_creation_commands.extend(nuclei_filter_commands)
nuclei_crops_creation_commands = [crop_nuclei_images,
                                  crop_nuclei_masks,
                                  split_channels_nuclei]
if DECONVOLVE_NUCLEI_CHANNEL:
    check_wavelength_set(channel_str=NUCLEI_CHANNEL_STR, channel_wavelengths=CHANNEL_WAVELENGTHS)
    nuclei_image_preprocessing_commands.append(deconvolve_nuclei_channel)
    nuclei_image_preprocessing_commands.append(pad_nuclei_channel)
if BLUR_NUCLEI_CHANNEL:
    nuclei_image_preprocessing_commands.append(blur_nuclei_channel)
if CLOSE_NUCLEI_MASKS:
    nuclei_masks_postprocessing_commands.append(close_masks_nuclei)
if MERGE_NUCLEI_MASKS:
    nuclei_masks_postprocessing_commands.append(merge_masks_nuclei)
if RESIZE_NUCLEI_MASKS:
    nuclei_masks_postprocessing_commands.append(resize_masks_nuclei)
    nuclei_masks_postprocessing_commands.append(erode_masks_nuclei)
if CREATE_NUCLEI_BORDERS_MASKS:
    nuclei_masks_postprocessing_commands.append(dilate_masks_nuclei)
    nuclei_masks_postprocessing_commands.append(apply_masks_nuclei)
if CREATE_NUCLEI_BORDERS_DFS:
    nuclei_tables_creation_commands.append(generate_objects_dfs_nuclei_borders)
    nuclei_tables_creation_commands.append(join_dfs_nuclei_borders)
if CREATE_NUCLEI_PAIRWISE_DISTANCES_DFS:
    nuclei_tables_creation_commands.append(generate_pairwise_distances_dfs_nuclei)
    nuclei_tables_creation_commands.append(join_dfs_nuclei_pairwise_distances)
if CREATE_NUCLEI_BORDER_DISTANCES_DF:
    nuclei_tables_creation_commands.append(generate_border_distances_df_nuclei)

# cytoplasm
cytoplasm_image_preprocessing_commands = []
cytoplasm_segmentation_commands = [apply_masks_cytoplasm]
cytoplasm_masks_postprocessing_commands = []
cytoplasm_tables_creation_commands = [generate_objects_dfs_cytoplasm,
                                      join_dfs_cytoplasm]

# assembling generate final tables commands list
generate_final_tables = [join_dfs_dots,
                         generate_summary_dfs,
                         normalize_summary_dfs]
if CREATE_DOTS_BORDER_DISTANCES_DFS:
    generate_final_tables.insert(1, join_dfs_dots_w_distances)

# assembling cescale commands list
cescale_commands_list = [summary_to_cescale_df,
                         run_cescale,
                         join_dfs_cescale,
                         generate_lineages_df,
                         generate_lineage_summary_df,
                         plot_lineage_tree]

##############################
# final list
##############################

# defining placeholder for commands list
commands_list = []

# extending list based on conditionals

if RUN_INITIAL_PREPROCESSING:
    commands_list.extend(initial_preprocessing_commands)

if RUN_EMBRYOS_IMAGE_PREPROCESSING:
    commands_list.extend(embryos_image_preprocessing_commands)
if RUN_EMBRYOS_SEGMENTATION:
    commands_list.extend(embryos_segmentation_commands)
if RUN_EMBRYOS_MASKS_POSTPROCESSING:
    commands_list.extend(embryos_masks_postprocessing_commands)
if RUN_EMBRYOS_TABLES_CREATION:
    commands_list.extend(embryos_tables_creation_commands)
if RUN_EMBRYOS_CROPS_CREATION:
    commands_list.extend(embryos_crops_creation_commands)

if RUN_NUCLEI_IMAGE_PREPROCESSING:
    commands_list.extend(nuclei_image_preprocessing_commands)
if RUN_NUCLEI_SEGMENTATION:
    commands_list.extend(nuclei_segmentation_commands)
if RUN_NUCLEI_MASKS_POSTPROCESSING:
    commands_list.extend(nuclei_masks_postprocessing_commands)
if RUN_NUCLEI_TABLES_CREATION:
    commands_list.extend(nuclei_tables_creation_commands)
if RUN_NUCLEI_CROPS_CREATION:
    commands_list.extend(nuclei_crops_creation_commands)

if RUN_CYTOPLASM_IMAGE_PREPROCESSING:
    commands_list.extend(cytoplasm_image_preprocessing_commands)
if RUN_CYTOPLASM_SEGMENTATION:
    commands_list.extend(cytoplasm_segmentation_commands)
if RUN_CYTOPLASM_MASKS_POSTPROCESSING:
    commands_list.extend(cytoplasm_masks_postprocessing_commands)
if RUN_CYTOPLASM_TABLES_CREATION:
    commands_list.extend(cytoplasm_tables_creation_commands)

# getting dot stage commands dict items
dot_stage_commands_dict_items = DOT_STAGE_COMMANDS.items()

# iterating over every configured dot's toggle-gated stage commands
for dot_stage_commands_item in dot_stage_commands_dict_items:

    # getting current dot key/stage commands
    dot_key, dot_stage_commands = dot_stage_commands_item

    # getting current dot toggles
    dot_pipeline_toggles = DOTS_TOGGLES[dot_key]

    # extracting current commands
    current_image_preprocessing_commands = dot_stage_commands['image_preprocessing']
    current_segmentation_commands = dot_stage_commands['segmentation']
    current_mask_postprocessing_commands = dot_stage_commands['masks_postprocessing']
    current_create_tables_commands = dot_stage_commands['create_tables']

    if dot_pipeline_toggles.image_preprocessing:
        commands_list.extend(current_image_preprocessing_commands)
    if dot_pipeline_toggles.segmentation:
        commands_list.extend(current_segmentation_commands)
    if dot_pipeline_toggles.masks_postprocessing:
        commands_list.extend(current_mask_postprocessing_commands)
    if dot_pipeline_toggles.create_tables:
        commands_list.extend(current_create_tables_commands)

# checking whether to calculate dots distances
if CREATE_DOTS_DISTANCES_DF:
    generate_final_tables.insert(1, generate_dots_distances_df)
    generate_final_tables.insert(2, join_dfs_dots_distances)

# checking whether to map nuclei to images instead embryos crops
if MAP_NUCLEI_TO_IMAGES:
    generate_final_tables.insert(0, generate_pseudoembryos_df)

# checking whether to summarize cilia (a dot is described as cilia)
if IS_CILIA_PIPELINE:
    generate_final_tables.append(generate_cilia_summary_df)  # noqa

if RUN_GENERATE_FINAL_TABLES:
    commands_list.extend(generate_final_tables)

# checking whether to run cescale lineage alignment (requires cescale.reference_folder to be set) -
# run after generate_final_tables, since it needs the normalized nuclei_summary_df.csv
# (produced by normalize_summary_dfs, above)
if RUN_CESCALE:
    commands_list.extend(cescale_commands_list)

######################################################################
# running pipeline

# getting vars dict
vars_dict = get_vars_dict()

# defining vars to skip
vars_to_skip = ['BASE_FOLDER']

# defining intermediate subfolders (can be safely deleted)
intermediate_subfolders = [TIFS_FOLDER,
                           CROPS_FOLDER,
                           IMGS_CHANNELS_FOLDER]

# getting subfolder list
subfolders_list = get_subfolders_list(vars_dict=vars_dict,
                                      vars_to_skip=vars_to_skip)

# creating subfolders
create_subfolders(base_folder=BASE_FOLDER,
                  subfolders_list=subfolders_list)

# running commands
run_commands(commands_list=commands_list,
             overwrite_output=OVERWRITE_OUTPUT,
             skip_enter=SKIP_ENTER,
             simulate=SIMULATE_RUN,
             log_folder=LOG_FOLDER)

# checking if intermediate files should be cleared
if CLEAR_INTERMEDIATE_FILES:

    # deleting subfolders
    delete_subfolders(subfolders_list=intermediate_subfolders)

# printing execution message
print(f'finished pipeline run.')

######################################################################
# end of current module
