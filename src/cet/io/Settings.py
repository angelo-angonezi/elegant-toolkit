# Settings module

# Code destined to defining
# Settings class and
# related attributes/methods.

######################################################################
# imports

import re
from pydantic import Field
from typing import Literal
from yaml import safe_load
from pydantic import BaseModel
from pydantic import RootModel
from pydantic import field_validator

######################################################################
# constants

# nuclear mask subfolders a dot can be linked to (masks/<name>)
NUCLEI_MASK_NAMES = ('nuclei', 'nuclei_closed', 'nuclei_merged', 'nuclei_resized', 'nuclei_eroded', 'nuclei_dilated')

# table filter condition: comparison operator followed by a number (e.g. '>= 2000')
FILTER_CONDITION_PATTERN = re.compile(r'^\s*(>=|<=|==|!=|>|<)\s*-?\d+(\.\d+)?\s*$')

######################################################################
# Settings definition


class ExperimentSettings(BaseModel):
    """
    Stores experiment settings.

    Attributes:
        base_folder (str): Path to the base experiment folder.
        image_extension (str): File extension of raw images.
    """
    base_folder: str
    image_extension: str


class MicroscopySettings(BaseModel):
    """
    Stores microscopy settings.

    Attributes:
        numerical_aperture (float): Numerical aperture of the
            objective lens.
        refractive_index (float): Refractive index of the medium.
        xy_scale (float): Pixel size in XY plane (micrometers).
        z_scale (float): Pixel size in Z plane (micrometers).
        z_axis (int): Z-axis dimension index.
    """
    numerical_aperture: float
    refractive_index: float
    xy_scale: float
    z_scale: float
    z_axis: int

    @property
    def scales_str(self) -> str:
        """
        Helper property to format scale parameter
        for CLI tools.

        Returns:
            str: A comma-separated scale string in format 'x=xy_scale,y=xy_scale,z=z_scale'.
        """
        # assembling scales str
        scales_str = f'x={self.xy_scale},y={self.xy_scale},z={self.z_scale}'

        # returning scales str
        return scales_str


class ChannelSettings(BaseModel):
    """
    Stores details for an individual channel.

    Attributes:
        name (str | None): The friendly name of the channel. None marks
            an unused channel (excluded from measurements).
        wavelength (int | None): The wavelength of the channel
            in nanometers. None if not set.
    """
    name: str | None = None
    wavelength: int | None = None

    @field_validator('name', 'wavelength', mode='before')
    @classmethod
    def empty_to_none(cls, value):
        """Treats empty or whitespace-only strings (and empty lists) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, list) and not value:
            return None
        return value


class ChannelsSettings(RootModel[dict[str, ChannelSettings]]):
    """
    Stores settings for all microscopy channels.

    Attributes:
        root (dict[str, ChannelSettings]): A dictionary mapping
            channel keys to ChannelSettings objects.
    """
    @property
    def channel_names(self) -> dict[str, str | None]:
        """
        Helper property to extract mapping of channel
        keys to friendly names.

        Nuclear mask folders (NUCLEI_MASK_NAMES) missing from
        the settings default to 'nucleus_id', so any of them can
        be used as a measurements key.

        Returns:
            dict[str, str | None]: A dictionary mapping channel keys to channel names, None for unused channels
                (e.g., {'ch0': 'dapi', 'ch1': 'cpd', 'ch3': None}).
        """
        # assembling names dict
        ch_names = {key: 'nucleus_id' for key in NUCLEI_MASK_NAMES}
        ch_names.update({key: details.name for key, details in self.root.items()})

        # returning names dict
        return ch_names

    @property
    def channel_wavelengths(self) -> dict[str, int | None]:
        """
        Helper property to extract mapping of channel
        keys to wavelengths.

        Returns:
            dict[str, int | None]: A dictionary mapping channel keys to wavelengths in nanometers, None if not set
                (e.g., {'ch0': 405, 'ch1': 561, 'ch3': None}).
        """
        # assembling wavelengths dict
        ch_wavelengths = {key: details.wavelength for key, details in self.root.items()}

        # returning wavelenghts dict
        return ch_wavelengths


class SegmentationSettings(BaseModel):
    """
    Stores segmentation settings (embryos, nuclei,
    dots...).

    Attributes:
        description (str): Object description identifier.
        segmentation_channel (int): Channel index to segment.
        deconvolve (bool): Whether to deconvolve the channel.
        blur (bool): Whether to apply blur to the channel.
        dog (bool): Whether to use difference of gaussians.
        close_masks (bool): Whether to close mask holes.
        merge_masks (bool): Whether to merge touching masks.
        resize_masks (bool): Whether to resize masks.
        create_borders_masks (bool): Create borders masks.
        blur_sigma (float): Blur kernel size in pixels.
        blur_sigma_low (float): Low gaussian sigma for DoG.
        blur_sigma_high (float): High gaussian sigma for DoG.
        lower_threshold (int | float): Lower intensity threshold.
        upper_threshold (int | float): Upper intensity threshold.
        segmentation_mode (str): Segmentation algorithm to use.
        diameter (int): Expected object diameter for Cellpose.
        min_size (int): Minimum object size in pixels (Cellpose).
        closing_distance (int): Closing operation distance.
        merge_solidity_threshold (float): Solidity threshold
            for merging.
        merge_touch_margin (int): Margin pixels for touch check.
        dilation (int): Dilation kernel size in pixels.
        smooth_iterations (int): Mask smoothing iterations.
        borders_thickness (int): Border thickness in pixels.
        borders_description (str): Border mask description.
        margin (int): Crop margin around objects.
        batch_size (int): Batch size for processing.
        measurements (dict[str, list[str]]): Measurements to
            extract per channel/mask.
        filters (dict[str, str]): Table filters, mapping a dataframe
            column name to a condition (e.g. {'pixel_volume': '>= 2000'}).
            One condition per column.
    """
    description: str = 'obj'
    segmentation_channel: int
    deconvolve: bool = False
    blur: bool = False
    dog: bool = False
    close_masks: bool = False
    merge_masks: bool = False
    resize_masks: bool = False
    create_borders_masks: bool = False
    blur_sigma: float = 0.0
    blur_sigma_low: float = 1.02
    blur_sigma_high: float = 1.6
    lower_threshold: int | float = 20
    upper_threshold: int | float = -1
    segmentation_mode: str = 'binary'
    diameter: int = 0
    min_size: int = 0
    closing_distance: int = 0
    merge_solidity_threshold: float = 0.9
    merge_touch_margin: int = 1
    dilation: int = 0
    smooth_iterations: int = -1
    borders_thickness: int = 2
    borders_description: str = 'border'
    margin: int = 0
    batch_size: int = 16
    measurements: dict[str, list[str]] = Field(default_factory=dict)
    filters: dict[str, str] = Field(default_factory=dict)

    @field_validator('measurements')
    @classmethod
    def validate_single_nuclei_mask(cls, measurements: dict[str, list[str]]) -> dict[str, list[str]]:
        """
        Ensures at most one nuclear mask folder key
        (NUCLEI_MASK_NAMES) is present in measurements.
        """
        # collecting nuclear mask keys
        mask_keys = [key for key in measurements if key in NUCLEI_MASK_NAMES]

        # checking there is at most one
        if len(mask_keys) > 1:
            raise ValueError(f'measurements can link to at most one nuclei mask, found: {mask_keys}')

        # returning measurements
        return measurements

    @field_validator('filters')
    @classmethod
    def validate_filter_conditions(cls, filters: dict[str, str]) -> dict[str, str]:
        """
        Ensures every filter condition is a comparison
        operator followed by a number (conditions are
        evaluated by filter_df, so nothing else is allowed).
        """
        # initializing stripped filters dict
        stripped_filters = {}

        # getting dict items
        dict_items = filters.items()

        # looping through filters
        for filter_item in dict_items:

            # getting current column/condition
            column, condition = filter_item

            # checking condition format
            if not FILTER_CONDITION_PATTERN.match(str(condition)):
                raise ValueError(f"invalid filter condition for '{column}': {condition!r} (expected e.g. '>= 2000')")

            # storing stripped condition
            current_dict = {column: str(condition).strip()}
            stripped_filters.update(current_dict)

        # returning filters
        return stripped_filters


class SegmentationsSettings(BaseModel):
    """
    Store multi channel settings.

    Attributes:
        embryos (SegmentationSettings): Embryo segmentation
            settings.
        nuclei (SegmentationSettings): Nuclei segmentation
            settings.
        dots (dict[str, SegmentationSettings]): Dot segmentation
            settings per dot type.
    """
    embryos: SegmentationSettings
    nuclei: SegmentationSettings
    dots: dict[str, SegmentationSettings] = Field(default_factory=dict)


class DistanceToggles(BaseModel):
    """
    Generic toggle settings for distance
    calculation routines.

    Attributes:
        pairwise_distances (bool): Enable pairwise distances
            (nucleus-to-nucleus or dot-to-dot based on context).
        border_distances (bool): Enable border distances
            (embryo border or lamina based on context).
    """
    pairwise_distances: bool = False  # referes to nucleus-to-nucleus or dot-to-dot based on context
    border_distances: bool = False  # refers to embryo border or lamina based on context


class ObjectSignalToggles(BaseModel):
    """
    Generic toggle settings for boundary/border
    signal measurement.

    Attributes:
        embryos_border_signal (bool): Enable embryo border signal
            measurement.
        nuclei_border_signal (bool): Enable nuclei border signal
            measurement.
    """
    embryos_border_signal: bool = False
    nuclei_border_signal: bool = False


class AdditionalSettings(BaseModel):
    """
    Stores structured additional toggles for
    objects and measurements.

    Attributes:
        map_nuclei_to_images (bool): Enable nuclei to image
            mapping.
        signal_measurements (ObjectSignalToggles): Signal
            measurement settings.
        nuclei (DistanceToggles): Nuclei distance settings.
        dots (dict[str, DistanceToggles]): Dot distance settings
            per dot type.
        calculate_dots_distances (bool): Calculate dot distances.
        dots_distance_dot1_description (str): Description of the
            first dot type to compare when calculating dot-to-dot
            distances.
        dots_distance_dot2_description (str): Description of the
            second dot type to compare when calculating dot-to-dot
            distances.
        dots_distance_mode (str): Dot-pair matching algorithm to use
            when calculating dot-to-dot distances ("hungarian" or
            "legacy").
        overlap_threshold (float): Threshold for overlap
            detection.
    """
    map_nuclei_to_images: bool = False
    signal_measurements: ObjectSignalToggles = Field(default_factory=ObjectSignalToggles)
    nuclei: DistanceToggles = Field(default_factory=DistanceToggles)
    dots: dict[str, DistanceToggles] = Field(default_factory=dict)
    calculate_dots_distances: bool = False
    dots_distance_dot1_description: str = ''
    dots_distance_dot2_description: str = ''
    dots_distance_mode: str = 'hungarian'
    overlap_threshold: float = 0.5


class CescaleSettings(BaseModel):
    """
    Stores CeSCALE lineage alignment settings.

    Attributes:
        reference_folder (str | None): Path to CeSCALE reference folder. Empty is treated as unset
            (the consuming module falls back to its default).
        reference_dataset (str): CeSCALE reference dataset subfolder to use ('bao' or 'dryad').
        cell_types_path (str | None): Path to the lineage-to-cell-type reference CSV. Empty is treated as
            unset (the consuming module falls back to its default).
        gene_expression_path (str | None): Optional path to a lineage-specific gene expression CSV,
            passed to generate_lineages_df (-g). Empty string is treated as unset.
        tree_fill_color_col (str): Lineage summary column used as node fill color in the lineage tree plot.
        tree_fill_color_palette (str): Plotly colorscale name for node fill color.
        tree_edge_color_col (str | None): Optional column used as node edge color. Empty is treated as unset.
        tree_edge_color_palette (str): Plotly colorscale name for node edge color.
        tree_edge_width (float | None): Optional marker edge line width. Empty is treated as unset.
        tree_size_col (str): Lineage summary column used as node size.
        tree_hover_cols (list[str] | None): Optional columns (and order) shown in hover text.
            Empty is treated as unset.
        tree_format (str): Lineage tree plot format ('horizontal', 'vertical' or 'circular').
            Empty falls back to 'horizontal'.
    """
    reference_folder: str | None = None
    reference_dataset: str
    cell_types_path: str | None = None
    gene_expression_path: str | None = None
    tree_fill_color_col: str = 'cell_count'
    tree_fill_color_palette: str = 'Viridis'
    tree_edge_color_col: str | None = None
    tree_edge_color_palette: str = 'Viridis'
    tree_edge_width: float | None = None
    tree_size_col: str = 'cell_count'
    tree_hover_cols: list[str] | None = None
    tree_format: Literal['horizontal', 'vertical', 'circular'] = 'horizontal'

    @field_validator('reference_folder', 'cell_types_path', 'gene_expression_path', 'tree_edge_color_col',
                     'tree_edge_width', 'tree_hover_cols', mode='before')
    @classmethod
    def empty_to_none(cls, value):
        """Treats empty or whitespace-only strings (and empty lists) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, list) and not value:
            return None
        return value

    @field_validator('tree_format', mode='before')
    @classmethod
    def empty_to_default_tree_format(cls, value):
        """Treats empty/unset tree format as the default ('horizontal')."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return 'horizontal'
        return value


class StageToggleSettings(BaseModel):
    """
    Stores base toggles settings (embryos,
    nuclei, or dots...).

    Attributes:
        image_preprocessing (bool): Enable image preprocessing.
        segmentation (bool): Enable segmentation.
        masks_postprocessing (bool): Enable mask postprocessing.
        create_tables (bool): Enable table creation.
        create_crops (bool): Enable crop creation.
    """
    image_preprocessing: bool = False
    segmentation: bool = False
    masks_postprocessing: bool = False
    create_tables: bool = False
    create_crops: bool = False


class PipelineToggleSettings(BaseModel):
    """
    Stores main toggles settings.

    Attributes:
        initial_preprocessing (bool): Enable initial
            preprocessing.
        generate_final_tables (bool): Generate final tables.
        run_cescale (bool): Run CeSCALE lineage alignment.
        embryos (StageToggleSettings): Embryo stage toggles.
        nuclei (StageToggleSettings): Nuclei stage toggles.
        cytoplasm (StageToggleSettings): Cytoplasm stage toggles.
        dots (dict[str, StageToggleSettings]): Dot stage toggles
            per dot type.
    """
    initial_preprocessing: bool = False
    generate_final_tables: bool = False
    run_cescale: bool = False
    embryos: StageToggleSettings = Field(default_factory=StageToggleSettings)
    nuclei: StageToggleSettings = Field(default_factory=StageToggleSettings)
    cytoplasm: StageToggleSettings = Field(default_factory=StageToggleSettings)
    dots: dict[str, StageToggleSettings] = Field(default_factory=dict)


class RuntimeSettings(BaseModel):
    """
    Stores runtime settings.

    Attributes:
        skip_enter (bool): Skip enter prompts during execution.
        overwrite_output (bool): Overwrite existing output files.
        simulate_run (bool): Simulate run without executing.
        clear_intermediate_files (bool): Delete intermediate
            files after completion.
    """
    skip_enter: bool = False
    overwrite_output: bool = False
    simulate_run: bool = False
    clear_intermediate_files: bool = False


class Settings(BaseModel):
    """
    Stores all pipeline settings.

    Attributes:
        experiment (ExperimentSettings): Experiment settings.
        microscopy (MicroscopySettings): Microscopy settings.
        channels (ChannelsSettings): Channel settings.
        segmentation (SegmentationsSettings): Segmentation
            settings.
        additional_toggles (AdditionalSettings): Additional
            toggle settings.
        cescale (CescaleSettings): CeSCALE settings.
        pipeline_toggles (PipelineToggleSettings): Pipeline toggle
            settings.
        runtime (RuntimeSettings): Runtime settings.
    """
    experiment: ExperimentSettings
    microscopy: MicroscopySettings
    channels: ChannelsSettings
    segmentation: SegmentationsSettings
    additional_toggles: AdditionalSettings
    cescale: CescaleSettings
    pipeline_toggles: PipelineToggleSettings
    runtime: RuntimeSettings

    @classmethod
    def from_yaml(cls, input_path: str) -> "Settings":
        """
        Loads and validates settings from a YAML file.

        Args:
            input_path (str): Path to the YAML settings file.

        Returns:
            Settings: A validated Settings object constructed from the YAML file.
        """
        # defining placeholder value for settings dict
        settings_dict = {}

        # defining read mode
        read_mode = 'r'

        # loading settings file
        with open(input_path, read_mode) as open_file:

            # updating settings dict
            settings_dict = safe_load(open_file)

        # returning updated object
        return cls(**settings_dict)

######################################################################
# end of current module
