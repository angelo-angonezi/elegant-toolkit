# constants module

# Code destined to storing constant
# global variables used in multiple scripts.

######################################################################
# imports

from os.path import join
from os.path import expanduser
from importlib.resources import files

######################################################################
# defining global variables

# plotting
FIG_SIZE = (12, 8)
FONT_DICT = {'fontsize': 16}
DPI = 300
DEFAULT_CONTINUOUS_COLORMAP = 'Viridis'  # plotly colorscale name (numerical data)
DEFAULT_DISCRETE_COLORMAP = 'Plotly'  # plotly qualitative palette name (non-numerical data)

# reproducibility
SEED = 53

# bit depths
MAX_8BIT = (2 ** 8) - 1
MAX_16BIT = (2 ** 16) - 1
MAX_32BIT = (2 ** 32) - 1
# note: 'float32' reuses MAX_32BIT (2 ** 32 - 1) as a normalization ceiling, not the true float32
# maximum (~3.4e38); this is an intentional choice, so float images are scaled like uint32 ones
BIT_DEPTH_MAX_DICT = {'uint8': MAX_8BIT,
                      'uint16': MAX_16BIT,
                      'uint32': MAX_32BIT,
                      'float32': MAX_32BIT}

# ml input shapes
NUCLEI_SHAPE = (1, 32, 64, 64)
SHAPES_DICT = {'nuclei': NUCLEI_SHAPE,
               'nuclei_resnet50': NUCLEI_SHAPE,
               'nuclei_resnet18': NUCLEI_SHAPE}

# byte units
ONE_BYTE = 1
MULTIPLIER = 1024
ONE_KB = ONE_BYTE * MULTIPLIER
ONE_MB = ONE_KB * MULTIPLIER
ONE_GB = ONE_MB * MULTIPLIER
ONE_TB = ONE_GB * MULTIPLIER

# cli
SPACER_STR = ('#' * 30)
SKIP_ENTER_FLAG = '-s'
OVERWRITE_OUTPUT_FLAG = '-ow'
DEFAULT_SCALES_STR = 'x=0.065,y=0.065,z=0.21'

# bundled read-only resources (anchored to the installed package)
CET_PATH = files('cet')
FONTS_PATH = files('cet.gui.fonts')
ICONS_PATH = files('cet.gui.icons')
DEFAULT_SETTINGS_PATH = str(CET_PATH.joinpath('pipelines', 'settings', 'default_settings.yaml'))
GUI_TOOLTIPS_PATH = str(CET_PATH.joinpath('gui', 'tooltips', 'tooltips.json'))

# per-user data (downloaded/written data)
USER_HOME = expanduser('~')
CET_HOME = join(USER_HOME, '.cet')
CELLPOSE_FOLDER = join(CET_HOME, 'cellpose')
CELLPOSE_MODELS_FOLDER = join(CELLPOSE_FOLDER, 'models')
CELLPOSE_MODEL_PATH = join(CELLPOSE_MODELS_FOLDER, 'cpsam')
LINEAGE_FOLDER = join(CET_HOME, 'lineage')
REFERENCE_DATA_FOLDER = join(LINEAGE_FOLDER, 'reference_data')
CELL_TYPES_FOLDER = join(LINEAGE_FOLDER, 'cell_types')
CELL_TYPES_HTML_PATH = join(CELL_TYPES_FOLDER, 'wormatlas_complete_cell_list_source.html')
CELL_TYPES_CSV_PATH = join(CELL_TYPES_FOLDER, 'wormatlas_complete_cell_list.csv')

# lineage
FOUNDER_CELLS = ['AB',
                 'MS',
                 'E',
                 'C',
                 'D',
                 'P']

# delimiters
# note: MERGED_UID_DELIMITER and AMBIGUOUS_CELL_TYPE_DELIMITER currently share the value '+' but are
# independent (different meanings, different consumers); either can change without the other

# separates the original object uids merged into a single pseudo-object's uid (e.g. the Z2/Z3
# germline pseudo-cell built by cet.dataframes.converters.summary_to_cescale_df's z2z3-mode
# output, later unpacked back onto both original nuclei by generate_lineages_df)
MERGED_UID_DELIMITER = '+'

# separates multiple distinct cell types resolved for a single ancestor/precursor
# lineage that has not yet fully differentiated (see generate_lineages_df.get_cell_type)
AMBIGUOUS_CELL_TYPE_DELIMITER = '+'

######################################################################
# end of current module
