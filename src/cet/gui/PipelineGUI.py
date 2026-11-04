# Pipeline GUI module

# Code destined to defining
# PipelineGUI class and
# related GUI attributes/methods.

######################################################################
# imports

import os
import sys
import json
import ctypes
from pathlib import Path
from PyQt6.QtCore import Qt
from ruamel.yaml import YAML
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QWidget
from cet.constants import FONTS_PATH
from cet.constants import ICONS_PATH
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QRadioButton
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QButtonGroup
from cet.gui.theme import DARK_STYLESHEET
from cet.constants import GUI_TOOLTIPS_PATH
from cet.io.Settings import NUCLEI_MASK_NAMES
from cet.constants import REFERENCE_DATA_FOLDER
from cet.constants import DEFAULT_SETTINGS_PATH
from cet.gui.yaml_dict_ops import get_nested_val
from cet.gui.yaml_dict_ops import set_nested_val
from cet.gui.PillSwitchStyle import PillSwitchStyle
from cet.gui.tooltips_lookup import tooltip_for_control
from cet.gui.tooltips_lookup import tooltip_for_key_path
from cet.diagnostics.check_version import get_cet_variant
from cet.diagnostics.check_version import get_cet_version
from cet.gui.VirtualTerminalBuffer import VirtualTerminalBuffer

# supressing Qt SVG buffer warnings on Linux
os.environ["QT_LOGGING_RULES"] = "qt.svg.draw.warning=false"

######################################################################
# constants

# nuclei segmentation toggle that produces each nuclear mask folder a dot can be linked to
# (None means the folder is always available)
NUCLEI_MASK_REQUIRED_TOGGLES = {'nuclei': None,
                                'nuclei_closed': 'close_masks',
                                'nuclei_merged': 'merge_masks',
                                'nuclei_resized': 'resize_masks',
                                'nuclei_eroded': 'create_borders_masks',
                                'nuclei_dilated': 'create_borders_masks'}

# default nuclear mask folder linked to each dot
DEFAULT_DOT_MASK_LINK = 'nuclei'

# default nuclear mask folder used as input of the nuclei objects table
DEFAULT_NUCLEI_MASK_LINK = 'nuclei'

######################################################################
# PipelineGUI definition


class PipelineGUI(QWidget):
    """
    Main GUI class for the pipeline configuration
    and execution interface.
    """
    def __init__(self) -> None:
        """
        Initializes a PipelineGUI instance and
        defines class attributes and UI widgets.

        Returns:
            None.
        """
        # calling parent constructor
        super().__init__()

        # printing execution message
        print('initializing gui...')

        # explicitly set Windows AppUserModelID so taskbar uses custom application icon instead of Python's default
        if sys.platform == 'win32':
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('cet.pipeline.gui.editor.1.0')
            except Exception as app_id_err:
                print(f'Warning setting AppUserModelID: {app_id_err}')

        # setting window and taskbar icon
        print('loading icons...')
        icon_path = str(ICONS_PATH.joinpath('cet.png'))
        if os.path.exists(icon_path):
            # option A: load custom image file if available
            self.setWindowIcon(QIcon(icon_path))
            print(f'Successfully loaded custom icons from: {ICONS_PATH}')
        else:
            # option B: fallback to standard built-in system theme icon
            print('Using default icon')
            self.setWindowIcon(QIcon.fromTheme('applications-science', QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)))

        # loading font files explicitly into Qt font database via package resources
        print('loading fonts...')
        try:
            regular_font_file = str(FONTS_PATH.joinpath('LiberationSans-Regular.ttf'))
            bold_font_file = str(FONTS_PATH.joinpath('LiberationSans-Bold.ttf'))
            terminal_font_file = str(FONTS_PATH.joinpath('CascadiaMono-Regular.ttf'))

            if os.path.exists(regular_font_file):
                QFontDatabase.addApplicationFont(regular_font_file)
            if os.path.exists(bold_font_file):
                QFontDatabase.addApplicationFont(bold_font_file)
            if os.path.exists(terminal_font_file):
                QFontDatabase.addApplicationFont(terminal_font_file)
            print(f'Successfully loaded custom fonts from: {FONTS_PATH}')
        except Exception as font_err:
            print(f'Warning loading custom fonts: {font_err}')

        # defining custom fonts
        self.font_main = QFont('Liberation Sans', 10)
        self.font_bold = QFont('Liberation Sans', 11, QFont.Weight.Bold)
        self.font_title = QFont('Liberation Sans', 12, QFont.Weight.Bold)

        # defining custom terminal font
        self.font_console = QFont('Cascadia Mono', 11)
        self.font_console.setStyleHint(QFont.StyleHint.Monospace)

        self.setFont(self.font_main)
        self.setStyle(PillSwitchStyle())
        self.setStyleSheet(DARK_STYLESHEET)

        # defining window title
        self.setWindowTitle('Elegant Toolkit')

        # fixed window dimensions (fixed width)
        self.window_width = 1280
        self.window_height = 960

        # screen dimensions
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        # centering coordinates with fallback check for headless/virtual screens
        if self.screen_width > 0 and self.screen_height > 0:
            self.center_x = int((self.screen_width / 2) - (self.window_width / 2))
            self.center_y = int((self.screen_height / 2) - (self.window_height / 2))
            self.setGeometry(self.center_x, self.center_y, self.window_width, self.window_height)
        else:
            self.resize(self.window_width, self.window_height)

        # enforcing fixed window width
        self.setFixedWidth(self.window_width)

        # yaml configuration handler
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

        # file attributes
        self.config_data = {}
        self.file_path = ''
        self.is_default_loaded = False

        # registries
        self.switch_registry = {}
        self.entry_registry = {}
        self.measurement_registry = {}
        self.filter_registry = {}

        # dynamic dot widgets tracker
        self.dot_blocks = []

        # nuclei mask link radio state (built with the nuclei card)
        self.nuc_mask_state = None

        # containers for measurements UI widgets
        self.emb_meas_container = None
        self.nuc_meas_container = None

        # section visibility and content tracker for collapsing
        self.sections_tracker = {}

        # image extension radio button variable tracking
        self.image_ext_btn_group = QButtonGroup(self)
        self.image_ext_var = '.vsi'

        # cescale reference dataset radio button variable tracking
        self.cescale_dataset_btn_group = QButtonGroup(self)
        self.cescale_dataset_var = 'bao'

        # cescale lineage tree plot entries: (settings key, label, default text)
        self.cescale_tree_entries_spec = [('tree_fill_color_col', 'Fill Color Column:', 'cell_count'),
                                          ('tree_fill_color_palette', 'Fill Color Palette:', 'Viridis'),
                                          ('tree_edge_color_col', 'Edge Color Column:', ''),
                                          ('tree_edge_color_palette', 'Edge Color Palette:', 'Viridis'),
                                          ('tree_edge_width', 'Edge Width:', ''),
                                          ('tree_size_col', 'Size Column:', 'cell_count'),
                                          ('tree_hover_cols', 'Hover Columns:', ''),
                                          ('tree_format', 'Format:', 'horizontal')]
        self.cescale_tree_entries = {}

        # dots distance mode radio button variable tracking
        self.dots_distance_mode_btn_group = QButtonGroup(self)
        self.dots_distance_mode_var = 'hungarian'

        # execution subprocess tracking attribute
        self.running_process = None
        self.running_job_type = None

        # loading hover-tooltip text (missing/invalid file just means no tooltips)
        print('loading tooltips...')
        self.tooltips = {'parameters': {}, 'controls': {}}
        if os.path.exists(GUI_TOOLTIPS_PATH):
            try:
                with open(GUI_TOOLTIPS_PATH, encoding='utf-8') as tooltips_file:
                    self.tooltips = json.load(tooltips_file)
                print(f'Successfully loaded tooltips from: {GUI_TOOLTIPS_PATH}')
            except Exception as tooltips_err:
                print(f'Warning loading tooltips: {tooltips_err}')
        else:
            print('No tooltips file found - continuing without tooltips')

        # log processing and terminal attributes
        self.term_buffer = VirtualTerminalBuffer()

        # UI elements attributes
        self.lbl_file = None
        self.scroll_frame = None
        self.scroll_layout = None
        self.lbl_folder_path = None
        self.dots_param_container = None
        self.dots_toggle_container = None
        self.dots_add_toggle_container = None
        self.txt_console = None
        self.lbl_status = None
        self.btn_save_run = None
        self.btn_enter = None
        self.btn_abort = None

        # building interface widgets
        self.build_ui()

        # checking if default file exists
        if os.path.exists(self.file_path):
            # loading yaml configuration
            self.load_yaml(path=self.file_path)

    def tooltip_for_key_path(self, key_path: tuple) -> str:
        """
        Looks up hover-tooltip text for a parameter
        widget's key_path, normalizing away
        dynamically-numbered segments (dot1, dot2,
        ch0, ch1, ...) so repeated dot/channel blocks
        share one tooltip entry.

        Args:
            key_path (tuple): Registry key path to look up.

        Returns:
            str: Tooltip text, or '' if no entry matches.
        """
        return tooltip_for_key_path(self.tooltips, key_path)

    def tooltip_for_control(self, control_id: str) -> str:
        """
        Looks up hover-tooltip text for a
        non-parameter widget (button, section header)
        by its hand-picked control id.

        Args:
            control_id (str): Control identifier string.

        Returns:
            str: Tooltip text, or '' if no entry matches.
        """
        return tooltip_for_control(self.tooltips, control_id)

    def set_all_sections_state(self, expand: bool = True) -> None:
        """
        Expands or collapses all registered sections
        at once.

        Args:
            expand (bool): True to expand, False to collapse.

        Returns:
            None.
        """
        # getting dict items
        dict_items = self.sections_tracker.items()

        # iterating over sections
        for section_item in dict_items:

            # getting current section key/info
            section_key, section_info = section_item

            if expand:
                if not section_info['is_open']:
                    section_info['container'].setVisible(True)
                    section_info['arrow_btn'].setText('▼')
                    section_info['is_open'] = True
            else:
                if section_info['is_open']:
                    section_info['container'].setVisible(False)
                    section_info['arrow_btn'].setText('►')
                    section_info['is_open'] = False

    def add_section_header(self,
                           title: str,
                           section_key: str,
                           master_key: str | None = None
                           ) -> QFrame:
        """
        Adds a collapsible section header inside its
        own isolated wrapper frame.

        Args:
            title (str): Display text for the section.
            section_key (str): Unique key for this section.
            master_key (str | None): Optional key for master toggle switch.

        Returns:
            QFrame: Content container for sub-widgets.
        """
        # top level wrapper frame for entire section
        section_wrapper = QFrame()
        section_layout = QVBoxLayout(section_wrapper)
        section_layout.setContentsMargins(0, 5, 0, 5)
        self.scroll_layout.addWidget(section_wrapper)

        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 5, 0, 2)
        section_layout.addWidget(header_frame)

        # arrow toggle button
        arrow_btn = QPushButton('▼')
        arrow_btn.setFixedSize(25, 25)
        arrow_btn.setFont(self.font_bold)
        arrow_btn.setStyleSheet("background-color: transparent; border: none;")
        arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        arrow_btn.clicked.connect(lambda _, k=section_key: self.toggle_section_visibility(k))
        header_layout.addWidget(arrow_btn)

        # creating section header label
        header_lbl = QLabel(title)
        header_lbl.setFont(self.font_title)
        header_lbl.setToolTip(self.tooltip_for_control(f'section_{section_key}'))
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()

        # allow clicking label to toggle section as well
        header_lbl.mousePressEvent = lambda e, k=section_key: self.toggle_section_visibility(k)

        # adding master switch if master key provided
        if master_key:
            master_sw = QCheckBox('Toggle All')
            master_sw.setFont(self.font_bold)
            master_sw.setToolTip(self.tooltip_for_control('master_toggle_all'))
            master_sw.stateChanged.connect(lambda state, k=master_key: self.toggle_section_master(section_prefix=k,
                                                                                                  target_state=state == Qt.CheckState.Checked.value))
            header_layout.addWidget(master_sw)

            # store reference to master switch using key
            setattr(self, f'master_sw_{master_key}', master_sw)

        # creating separator line frame
        separator = QFrame()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #555555;")
        section_layout.addWidget(separator)

        # content container frame inside wrapper
        content_container = QFrame()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 5, 0, 0)
        section_layout.addWidget(content_container)

        # registering section state
        self.sections_tracker[section_key] = {
            'is_open': True,
            'arrow_btn': arrow_btn,
            'container': content_container
        }

        return content_container

    def toggle_section_visibility(self, section_key: str) -> None:
        """
        Toggles the visibility (collapse/expand) of a
        section's content container inside its
        wrapper.

        Args:
            section_key (str): Section identifier key.

        Returns:
            None.
        """
        section_info = self.sections_tracker.get(section_key)
        if not section_info:
            return

        is_open = section_info['is_open']
        section_info['container'].setVisible(not is_open)
        section_info['arrow_btn'].setText('►' if is_open else '▼')
        section_info['is_open'] = not is_open

    def toggle_section_master(self, section_prefix: str, target_state: bool) -> None:
        """
        Sets all switches whose key starts with
        section_prefix to state of master switch.

        Args:
            section_prefix (str): Prefix to match in switch registry keys.
            target_state (bool): State to set for matched switches.

        Returns:
            None.
        """
        # getting dict items
        dict_items = self.switch_registry.items()

        # iterating over switches
        for switch_item in dict_items:

            # getting current switch key path/switch
            key_path, switch = switch_item

            if len(key_path) > 0 and key_path[0] == section_prefix:
                switch.setChecked(target_state)

    @staticmethod
    def add_subsection_separator(container: QFrame) -> None:
        """
        Adds a thin horizontal line separator
        between subsections.

        Args:
            container (QFrame): Container to add separator to.

        Returns:
            None.
        """
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #3e4245; margin-top: 8px; margin-bottom: 8px;")
        container.layout().addWidget(separator)

    def add_switch_to_container(self,
                                container: QFrame,
                                label_text: str,
                                key_path: tuple,
                                inline: bool = False
                                ) -> None:
        """
        Adds a QCheckBox pill widget with custom
        drawn circular handle to container.

        Args:
            container (QFrame): Container to add switch to.
            label_text (str): Display text for the switch.
            key_path (tuple): Registry key path.
            inline (bool): True for inline layout, False for row layout.

        Returns:
            None.
        """
        # creating switch widget
        switch = QCheckBox(label_text)
        switch.setFont(self.font_main)
        switch.setToolTip(self.tooltip_for_key_path(key_path))

        if inline:
            container.layout().addWidget(switch)
        else:
            row_frame = QFrame()
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 3, 0, 3)
            row_layout.addWidget(switch)
            row_layout.addStretch()
            container.layout().addWidget(row_frame)

        # registering switch
        self.switch_registry[key_path] = switch

        # refreshing dots' mask link options when a nuclei toggle they depend on changes
        if (len(key_path) == 3 and key_path[:2] == ('segmentation', 'nuclei')
                and key_path[2] in NUCLEI_MASK_REQUIRED_TOGGLES.values()):
            switch.toggled.connect(lambda _checked: self.update_dot_mask_options())

    def add_entry_field(self,
                        container: QFrame,
                        label_text: str,
                        key_path: tuple,
                        width: int = 150
                        ) -> None:
        """
        Adds a single labeled QLineEdit field on its
        own vertical row and registers it in
        entry_registry.

        Args:
            container (QFrame): Container to add field to.
            label_text (str): Label text for the field.
            key_path (tuple): Registry key path.
            width (int): Fixed width of entry widget.

        Returns:
            None.
        """
        row_frame = QFrame()
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 3, 0, 3)

        # creating field label
        lbl = QLabel(label_text)
        lbl.setFont(self.font_main)
        lbl.setFixedWidth(160)
        entry_tooltip = self.tooltip_for_key_path(key_path)
        lbl.setToolTip(entry_tooltip)
        row_layout.addWidget(lbl)

        # creating entry input widget
        entry = QLineEdit()
        entry.setFixedWidth(width)
        entry.setFont(self.font_main)
        entry.setToolTip(entry_tooltip)
        if key_path[0] == 'channels' and key_path[2] == 'name':
            entry.textChanged.connect(self.update_all_measurements_ui)
        row_layout.addWidget(entry)
        row_layout.addStretch()

        container.layout().addWidget(row_frame)

        # registering entry widget
        self.entry_registry[key_path] = entry

    def add_entry_field_compact(self,
                                container: QFrame,
                                label_text: str,
                                key_path: tuple,
                                width: int = 100
                                ) -> None:
        """
        Adds a compact labeled QLineEdit field
        within stacked channel columns.

        Args:
            container (QFrame): Container to add field to.
            label_text (str): Label text for the field.
            key_path (tuple): Registry key path.
            width (int): Fixed width of entry widget.

        Returns:
            None.
        """
        row_frame = QFrame()
        row_layout = QVBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 2, 0, 4)

        lbl = QLabel(label_text)
        lbl.setFont(self.font_main)
        entry_tooltip = self.tooltip_for_key_path(key_path)
        lbl.setToolTip(entry_tooltip)
        row_layout.addWidget(lbl)

        entry = QLineEdit()
        entry.setFixedWidth(width)
        entry.setFont(self.font_main)
        entry.setToolTip(entry_tooltip)
        if key_path[0] == 'channels':
            entry.setPlaceholderText('Not set')
        if key_path[0] == 'channels' and key_path[2] == 'name':
            entry.textChanged.connect(self.update_all_measurements_ui)
        row_layout.addWidget(entry)

        container.layout().addWidget(row_frame)

        # registering entry widget
        self.entry_registry[key_path] = entry

    def create_toggle_group(self,
                            parent_container: QFrame,
                            group_title: str,
                            toggles: list
                            ) -> None:
        """
        Creates a card container containing multiple
        switches stacked vertically.

        Args:
            parent_container (QFrame): Container to add card to.
            group_title (str): Card title text.
            toggles (list): List of (label, key_path) tuples.

        Returns:
            None.
        """
        # creating card container frame
        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 10)
        parent_container.layout().addWidget(card)

        # creating card title label
        lbl = QLabel(group_title)
        lbl.setFont(self.font_bold)
        card_layout.addWidget(lbl)

        # iterating over toggle tuples
        for label_text, key_path in toggles:
            # adding switch to container
            self.add_switch_to_container(container=card,
                                         label_text=label_text,
                                         key_path=key_path)

    def get_active_channels(self) -> list:
        """
        Retrieves active channel names and keys from
        Channels subsection, excluding channels with
        no name set (blank Name box).

        Returns:
            list: List of (ch_key, ch_name) tuples.
        """
        active_channels = []
        for ch_num in range(4):
            ch_key = f'ch{ch_num}'
            entry_key = ('channels', ch_key, 'name')
            ch_name = ''
            if entry_key in self.entry_registry:
                ch_name = self.entry_registry[entry_key].text().strip()
            elif self.config_data:
                ch_data = get_nested_val(data=self.config_data, key_path=entry_key)
                if ch_data:
                    ch_name = str(ch_data).strip()
            if ch_name:
                active_channels.append((ch_key, ch_name))
        return active_channels

    def build_measurements_subpanel(self,
                                    container: QFrame,
                                    obj_type: str,
                                    dot_key: str | None = None
                                    ) -> None:
        """
        Populates a container with channel-related
        measurement toggles (Intensity and Texture)
        for non-empty channels.

        Args:
            container (QFrame): Container to populate.
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            None.
        """
        # clear existing layout inside container
        while container.layout().count():
            item = container.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        active_channels = self.get_active_channels()
        if not active_channels:
            return

        lbl_meas = QLabel('Channel Measurements:')
        lbl_meas.setFont(self.font_bold)
        container.layout().addWidget(lbl_meas)

        meas_grid = QFrame()
        meas_grid_layout = QHBoxLayout(meas_grid)
        meas_grid_layout.setContentsMargins(0, 2, 0, 2)
        container.layout().addWidget(meas_grid)

        for ch_key, ch_name in active_channels:
            ch_box = QFrame()
            ch_box_layout = QVBoxLayout(ch_box)
            ch_box_layout.setContentsMargins(5, 2, 5, 2)

            ch_title = f'{ch_key} ({ch_name}):' if ch_name else f'{ch_key}:'
            lbl_ch_title = QLabel(ch_title)
            lbl_ch_title.setFont(self.font_bold)
            ch_box_layout.addWidget(lbl_ch_title)

            sw_int = QCheckBox('Intensity')
            sw_int.setFont(self.font_main)
            sw_int.setToolTip(self.tooltip_for_control('measurement_intensity'))
            ch_box_layout.addWidget(sw_int)

            sw_tex = QCheckBox('Texture')
            sw_tex.setFont(self.font_main)
            sw_tex.setToolTip(self.tooltip_for_control('measurement_texture'))
            ch_box_layout.addWidget(sw_tex)

            meas_grid_layout.addWidget(ch_box)

            reg_key = (obj_type, dot_key, ch_key) if dot_key else (obj_type, ch_key)
            self.measurement_registry[reg_key] = {
                'intensity': sw_int,
                'texture': sw_tex
            }

        meas_grid_layout.addStretch()

    def build_filters_subpanel(self,
                               container: QFrame,
                               obj_type: str,
                               dot_key: str | None = None
                               ) -> None:
        """
        Appends a 'Filters' subpanel (title, rows area
        and 'Add Filter' button) to a container and
        registers it in filter_registry.

        Args:
            container (QFrame): Container to populate.
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            None.
        """
        reg_key = (obj_type, dot_key) if dot_key else (obj_type,)

        # title
        lbl_filters = QLabel('Filters:')
        lbl_filters.setFont(self.font_bold)
        lbl_filters.setToolTip(self.tooltip_for_control('filter_condition'))
        container.layout().addWidget(lbl_filters)

        # rows area
        rows_container = QFrame()
        rows_layout = QVBoxLayout(rows_container)
        rows_layout.setContentsMargins(0, 2, 0, 2)
        container.layout().addWidget(rows_container)

        # add filter button
        btn_row = QFrame()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 2, 0, 2)
        container.layout().addWidget(btn_row)
        btn_row_layout.addStretch()

        btn_add = QPushButton(' Add Filter')
        plus_icon_path = str(ICONS_PATH.joinpath('plus.png'))
        if os.path.exists(plus_icon_path):
            btn_add.setIcon(QIcon(plus_icon_path))
        btn_add.setFixedSize(105, 26)
        btn_add.setFont(self.font_main)
        btn_add.setToolTip(self.tooltip_for_control('btn_add_filter'))
        btn_add.clicked.connect(lambda _checked=False: self.add_filter_row(obj_type=obj_type, dot_key=dot_key))
        btn_row_layout.addWidget(btn_add)

        # registering subpanel
        self.filter_registry[reg_key] = {'rows_container': rows_container, 'rows': []}

    def add_filter_row(self,
                       obj_type: str,
                       dot_key: str | None = None,
                       column: str = '',
                       condition: str = ''
                       ) -> None:
        """
        Adds one filter row (column entry, condition
        entry and remove button) to an object's
        filters subpanel.

        Args:
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.
            column (str): Initial column name.
            condition (str): Initial condition (e.g. '>= 2000').

        Returns:
            None.
        """
        reg_key = (obj_type, dot_key) if dot_key else (obj_type,)
        subpanel = self.filter_registry[reg_key]

        row_frame = QFrame()
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 2, 0, 2)

        # column entry
        key_entry = QLineEdit()
        key_entry.setPlaceholderText('column')
        key_entry.setFixedWidth(200)
        key_entry.setFont(self.font_main)
        key_entry.setToolTip(self.tooltip_for_control('filter_column'))
        key_entry.setText(str(column))
        row_layout.addWidget(key_entry)

        # condition entry
        cond_entry = QLineEdit()
        cond_entry.setPlaceholderText('> 0')
        cond_entry.setFixedWidth(100)
        cond_entry.setFont(self.font_main)
        cond_entry.setToolTip(self.tooltip_for_control('filter_condition'))
        cond_entry.setText(str(condition))
        row_layout.addWidget(cond_entry)

        # row dict (shared with the remove button)
        row = {'frame': row_frame, 'key_entry': key_entry, 'cond_entry': cond_entry}

        # remove button
        btn_remove = QPushButton(' Remove')
        remove_icon_path = str(ICONS_PATH.joinpath('remove.png'))
        if os.path.exists(remove_icon_path):
            btn_remove.setIcon(QIcon(remove_icon_path))
        btn_remove.setStyleSheet("background-color: #c0392b; color: white;")
        btn_remove.setFixedSize(90, 24)
        btn_remove.setFont(self.font_main)
        btn_remove.setToolTip(self.tooltip_for_control('btn_remove_filter'))
        btn_remove.clicked.connect(lambda _checked=False: self.remove_filter_row(reg_key=reg_key, row=row))
        row_layout.addWidget(btn_remove)
        row_layout.addStretch()

        subpanel['rows_container'].layout().addWidget(row_frame)
        subpanel['rows'].append(row)

    def remove_filter_row(self, reg_key: tuple, row: dict) -> None:
        """
        Removes a single filter row from an object's
        filters subpanel.

        Args:
            reg_key (tuple): Key of the subpanel in filter_registry.
            row (dict): Row dict to remove.

        Returns:
            None.
        """
        subpanel = self.filter_registry.get(reg_key)
        if subpanel is None or row not in subpanel['rows']:
            return

        subpanel['rows'].remove(row)
        row['frame'].setParent(None)
        row['frame'].deleteLater()

    def clear_filter_rows(self, reg_key: tuple) -> None:
        """
        Removes every filter row from an object's
        filters subpanel.

        Args:
            reg_key (tuple): Key of the subpanel in filter_registry.

        Returns:
            None.
        """
        subpanel = self.filter_registry.get(reg_key)
        if subpanel is None:
            return

        for row in list(subpanel['rows']):
            self.remove_filter_row(reg_key=reg_key, row=row)

    def get_filters_dict(self, obj_type: str, dot_key: str | None = None) -> dict:
        """
        Collects an object's filter rows into a
        {column: condition} dict. Rows with a blank
        column are skipped.

        Args:
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            dict: Filters dict.

        Raises:
            ValueError: If a column is duplicated or a condition is blank.
        """
        reg_key = (obj_type, dot_key) if dot_key else (obj_type,)
        subpanel = self.filter_registry.get(reg_key, {'rows': []})

        filters = {}
        for row in subpanel['rows']:
            column = row['key_entry'].text().strip()
            condition = row['cond_entry'].text().strip()

            # skipping blank rows
            if not column:
                continue

            # validating row
            label = f'{obj_type} {dot_key}' if dot_key else obj_type
            if column in filters:
                raise ValueError(f"duplicate filter column '{column}' in {label} (one condition per column)")
            if not condition:
                raise ValueError(f"missing condition for filter column '{column}' in {label}")

            current_dict = {column: condition}
            filters.update(current_dict)

        return filters

    def load_filters_from_yaml(self,
                               obj_type: str,
                               filters_dict: dict | None,
                               dot_key: str | None = None
                               ) -> None:
        """
        Replaces an object's filter rows with the
        entries of a YAML filters dict.

        Args:
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            filters_dict (dict | None): Filters dict from YAML, or None.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            None.
        """
        reg_key = (obj_type, dot_key) if dot_key else (obj_type,)
        if reg_key not in self.filter_registry:
            return

        self.clear_filter_rows(reg_key=reg_key)

        if not isinstance(filters_dict, dict):
            return

        # getting dict items
        dict_items = filters_dict.items()

        # iterating over filters
        for filter_item in dict_items:

            # getting current column/condition
            column, condition = filter_item

            self.add_filter_row(obj_type=obj_type, dot_key=dot_key, column=str(column), condition=str(condition))

    def update_all_measurements_ui(self) -> None:
        """
        Rebuilds measurement UI panels for embryos,
        nuclei, and all dots when channels are
        updated.

        Returns:
            None.
        """
        # save current measurement states before rebuilding UI
        saved_states = {}

        # getting measurement registry dict items
        registry_dict_items = self.measurement_registry.items()

        # iterating over measurement registry items
        for registry_item in registry_dict_items:

            # getting current registry key/switches
            reg_key, switches = registry_item

            saved_states[reg_key] = {
                'intensity': switches['intensity'].isChecked(),
                'texture': switches['texture'].isChecked()
            }

        self.measurement_registry.clear()

        if self.emb_meas_container:
            self.build_measurements_subpanel(container=self.emb_meas_container, obj_type='embryos')
        if self.nuc_meas_container:
            self.build_measurements_subpanel(container=self.nuc_meas_container, obj_type='nuclei')

        for block in self.dot_blocks:
            if 'meas_container' in block:
                self.build_measurements_subpanel(container=block['meas_container'],
                                                 obj_type='dots',
                                                 dot_key=block['dot_key'])

        # getting saved states dict items
        saved_states_dict_items = saved_states.items()

        # restoring saved states to newly constructed UI elements
        for saved_state_item in saved_states_dict_items:

            # getting current registry key/states
            reg_key, states = saved_state_item

            if reg_key in self.measurement_registry:
                self.measurement_registry[reg_key]['intensity'].setChecked(states['intensity'])
                self.measurement_registry[reg_key]['texture'].setChecked(states['texture'])

    def add_dot_block(self) -> None:
        """
        Dynamically appends a new Dot parameter
        block and corresponding toggle cards.

        Returns:
            None.
        """
        # calculating new dot index
        dot_idx = len(self.dot_blocks) + 1
        dot_key = f'dot{dot_idx}'

        # separator before adding new dot block if not the first
        if self.dot_blocks:
            self.add_subsection_separator(container=self.dots_param_container)
            self.add_subsection_separator(container=self.dots_toggle_container)
            self.add_subsection_separator(container=self.dots_add_toggle_container)

        # --- 1. Parameter Card ---
        param_card = QFrame()
        param_layout = QVBoxLayout(param_card)
        param_layout.setContentsMargins(10, 8, 10, 10)
        self.dots_param_container.layout().addWidget(param_card)

        header_row = QFrame()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.addWidget(header_row)

        lbl_title = QLabel(f'Dot {dot_idx} Parameters')
        lbl_title.setFont(self.font_bold)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        # remove button
        btn_remove = QPushButton(' Remove')
        remove_icon_path = str(ICONS_PATH.joinpath('remove.png'))
        if os.path.exists(remove_icon_path):
            btn_remove.setIcon(QIcon(remove_icon_path))
        btn_remove.setStyleSheet("background-color: #c0392b; color: white;")
        btn_remove.setFixedSize(90, 24)
        btn_remove.setFont(self.font_main)
        btn_remove.setToolTip(self.tooltip_for_control('btn_remove_dot'))
        btn_remove.clicked.connect(lambda: self.remove_dot_block(dot_idx))
        header_layout.addWidget(btn_remove)

        self.add_entry_field(container=param_card,
                             label_text='Description:',
                             key_path=('segmentation', 'dots', dot_key, 'description'),
                             width=240)

        # Segmentation Settings subsection toggles placed in a single inline row
        dot_sw_row = QFrame()
        dot_sw_layout = QHBoxLayout(dot_sw_row)
        dot_sw_layout.setContentsMargins(0, 4, 0, 4)
        param_card.layout().addWidget(dot_sw_row)

        self.add_switch_to_container(container=dot_sw_row,
                                     label_text='Deconvolve',
                                     key_path=('segmentation', 'dots', dot_key, 'deconvolve'),
                                     inline=True)
        self.add_switch_to_container(container=dot_sw_row,
                                     label_text='DoG (Difference of Gaussians)',
                                     key_path=('segmentation', 'dots', dot_key, 'dog'),
                                     inline=True)
        dot_sw_layout.addStretch()

        self.add_entry_field(container=param_card,
                             label_text='Channel:',
                             key_path=('segmentation', 'dots', dot_key, 'segmentation_channel'),
                             width=100)
        self.add_entry_field(container=param_card,
                             label_text='Sigma Low:',
                             key_path=('segmentation', 'dots', dot_key, 'blur_sigma_low'),
                             width=100)
        self.add_entry_field(container=param_card,
                             label_text='Sigma High:',
                             key_path=('segmentation', 'dots', dot_key, 'blur_sigma_high'),
                             width=100)
        self.add_entry_field(container=param_card,
                             label_text='Lower Thresh:',
                             key_path=('segmentation', 'dots', dot_key, 'lower_threshold'),
                             width=100)

        # nuclear mask link radio buttons (which nuclei* mask folder this dot is measured against)
        mask_state = {'value': DEFAULT_DOT_MASK_LINK, 'radios': {}, 'group': QButtonGroup(param_card)}
        mask_row = QFrame()
        mask_row_layout = QGridLayout(mask_row)
        mask_row_layout.setContentsMargins(0, 4, 0, 4)
        param_card.layout().addWidget(mask_row)

        lbl_mask_link = QLabel('Link to masks:')
        lbl_mask_link.setFont(self.font_main)
        lbl_mask_link.setToolTip(self.tooltip_for_control('radio_dot_mask_link'))
        mask_row_layout.addWidget(lbl_mask_link, 0, 0)

        for i, mask_name in enumerate(NUCLEI_MASK_NAMES):
            rb = QRadioButton(mask_name)
            rb.setFont(self.font_main)
            rb.setToolTip(self.tooltip_for_control('radio_dot_mask_link'))
            rb.toggled.connect(lambda checked, v=mask_name, s=mask_state: s.update(value=v) if checked else None)
            if mask_name == mask_state['value']:
                rb.setChecked(True)
            mask_state['group'].addButton(rb)
            mask_state['radios'][mask_name] = rb
            mask_row_layout.addWidget(rb, 1 + i // 3, i % 3)

        # Measurements subpanel container for dot
        meas_container = QFrame()
        meas_layout = QVBoxLayout(meas_container)
        meas_layout.setContentsMargins(0, 5, 0, 5)
        param_card.layout().addWidget(meas_container)
        self.build_measurements_subpanel(container=meas_container, obj_type='dots', dot_key=dot_key)

        # Filters subpanel for dot
        self.build_filters_subpanel(container=param_card, obj_type='dots', dot_key=dot_key)

        # --- 2. Toggle Card ---
        toggle_card = QFrame()
        toggle_layout = QVBoxLayout(toggle_card)
        toggle_layout.setContentsMargins(10, 8, 10, 8)
        self.dots_toggle_container.layout().addWidget(toggle_card)

        toggle_lbl = QLabel(f'Dot {dot_idx} Toggles')
        toggle_lbl.setFont(self.font_bold)
        toggle_layout.addWidget(toggle_lbl)

        self.add_switch_to_container(container=toggle_card,
                                     label_text='Image Preprocessing',
                                     key_path=('pipeline_toggles', 'dots', dot_key, 'image_preprocessing'))
        self.add_switch_to_container(container=toggle_card,
                                     label_text='Segmentation',
                                     key_path=('pipeline_toggles', 'dots', dot_key, 'segmentation'))
        self.add_switch_to_container(container=toggle_card,
                                     label_text='Masks Postprocessing',
                                     key_path=('pipeline_toggles', 'dots', dot_key, 'masks_postprocessing'))
        self.add_switch_to_container(container=toggle_card,
                                     label_text='Create Tables',
                                     key_path=('pipeline_toggles', 'dots', dot_key, 'create_tables'))

        # --- 3. Additional Toggle Card ---
        add_toggle_card = QFrame()
        add_toggle_layout = QVBoxLayout(add_toggle_card)
        add_toggle_layout.setContentsMargins(10, 8, 10, 8)
        self.dots_add_toggle_container.layout().addWidget(add_toggle_card)

        add_toggle_lbl = QLabel(f'Dot {dot_idx} Additional Settings')
        add_toggle_lbl.setFont(self.font_bold)
        add_toggle_layout.addWidget(add_toggle_lbl)

        self.add_switch_to_container(container=add_toggle_card,
                                     label_text='Pairwise Distances',
                                     key_path=('additional_toggles', 'dots', dot_key, 'pairwise_distances'))
        self.add_switch_to_container(container=add_toggle_card,
                                     label_text='Border Distances',
                                     key_path=('additional_toggles', 'dots', dot_key, 'border_distances'))

        # storing references
        self.dot_blocks.append({
            'index': dot_idx,
            'param_card': param_card,
            'toggle_card': toggle_card,
            'add_toggle_card': add_toggle_card,
            'meas_container': meas_container,
            'mask_state': mask_state,
            'dot_key': dot_key
        })

        # greying out mask options unavailable with current nuclei settings
        self.update_dot_mask_options()

    def set_dot_mask_link(self, block: dict, mask_name: str) -> None:
        """
        Selects the nuclear mask folder radio button
        for a dot block (falls back to the default
        if the name is unknown).

        Args:
            block (dict): Entry of self.dot_blocks.
            mask_name (str): Nuclear mask folder name (see NUCLEI_MASK_NAMES).

        Returns:
            None.
        """
        mask_state = block['mask_state']
        if mask_name not in mask_state['radios']:
            mask_name = DEFAULT_DOT_MASK_LINK
        mask_state['radios'][mask_name].setChecked(True)

    def update_dot_mask_options(self) -> None:
        """
        Enables/greys out every dot's mask link radio
        buttons according to the nuclei segmentation
        toggles (close/merge/resize/borders masks). A
        selected option that becomes unavailable falls
        back to the default one.

        Returns:
            None.
        """
        # collecting every mask link radio group with its tooltip key and fallback option
        targets = [(block['mask_state'], 'radio_dot_mask_link', DEFAULT_DOT_MASK_LINK) for block in self.dot_blocks]
        if self.nuc_mask_state is not None:
            targets.append((self.nuc_mask_state, 'radio_nuclei_mask_link', DEFAULT_NUCLEI_MASK_LINK))

        for mask_state, tooltip_key, fallback in targets:

            # getting radios dict items
            radios_dict_items = mask_state['radios'].items()

            # enabling/disabling each option
            for radio_item in radios_dict_items:

                # getting current mask name/radio button
                mask_name, rb = radio_item

                toggle_name = NUCLEI_MASK_REQUIRED_TOGGLES.get(mask_name)
                switch = self.switch_registry.get(('segmentation', 'nuclei', toggle_name)) if toggle_name else None
                available = toggle_name is None or (switch is not None and switch.isChecked())
                rb.setEnabled(available)
                rb.setToolTip(self.tooltip_for_control(tooltip_key) if available
                              else f'Unavailable: enable nuclei "{toggle_name}" to produce this mask.')

            # falling back to default if current selection is now unavailable
            if not mask_state['radios'][mask_state['value']].isEnabled():
                mask_state['radios'][fallback].setChecked(True)

    def collect_dots_cache(self) -> list:
        """
        Collects current GUI widget state for all
        dots to preserve input values across
        deletions/rebuilds.

        Returns:
            list: Cached state data for each dot block.
        """
        cached_dots = []
        for block in self.dot_blocks:
            dot_key = block['dot_key']
            dot_data = {'entries': {}, 'switches': {}, 'measurements': {}, 'mask_link': block['mask_state']['value']}

            # getting entry registry dict items
            entry_dict_items = self.entry_registry.items()

            # gathering active entries for this dot_key
            for entry_item in entry_dict_items:

                # getting current entry key/entry
                k, entry = entry_item

                if len(k) >= 3 and k[0] == 'segmentation' and k[1] == 'dots' and k[2] == dot_key:
                    dot_data['entries'][k[3]] = entry.text()

            # getting switch registry dict items
            switch_dict_items = self.switch_registry.items()

            # gathering active switches for this dot_key
            for switch_item in switch_dict_items:

                # getting current switch key/switch
                k, switch = switch_item

                if len(k) >= 3 and k[0] == 'segmentation' and k[1] == 'dots' and k[2] == dot_key:
                    dot_data['switches'][('segmentation', k[3])] = switch.isChecked()
                elif len(k) >= 3 and k[0] == 'pipeline_toggles' and k[1] == 'dots' and k[2] == dot_key:
                    dot_data['switches'][('pipeline_toggles', k[3])] = switch.isChecked()
                elif len(k) >= 3 and k[0] == 'additional_toggles' and k[1] == 'dots' and k[2] == dot_key:
                    dot_data['switches'][('additional_toggles', k[3])] = switch.isChecked()

            # getting measurement registry dict items
            registry_dict_items = self.measurement_registry.items()

            # gathering active measurements for this dot_key
            for registry_item in registry_dict_items:

                # getting current registry key/switches
                reg_key, switches = registry_item

                if len(reg_key) == 3 and reg_key[0] == 'dots' and reg_key[1] == dot_key:
                    dot_data['measurements'][reg_key[2]] = {
                        'intensity': switches['intensity'].isChecked(),
                        'texture': switches['texture'].isChecked()
                    }

            # gathering filter rows for this dot_key
            filters_state = self.filter_registry.get(('dots', dot_key), {'rows': []})
            dot_data['filters'] = [(row['key_entry'].text(), row['cond_entry'].text()) for row in filters_state['rows']]

            cached_dots.append(dot_data)

        return cached_dots

    def apply_dots_cache(self, cached_dots: list) -> None:
        """
        Restores cached values to newly created dot
        GUI elements after re-indexing.

        Args:
            cached_dots (list): Cached state data from collect_dots_cache().

        Returns:
            None.
        """
        for i, dot_data in enumerate(cached_dots):
            if i >= len(self.dot_blocks):
                break

            target_key = self.dot_blocks[i]['dot_key']

            # getting entries dict items
            entries_dict_items = dot_data['entries'].items()

            # restore entry values
            for entry_item in entries_dict_items:

                # getting current field name/value
                field_name, value = entry_item

                full_key = ('segmentation', 'dots', target_key, field_name)
                if full_key in self.entry_registry:
                    self.entry_registry[full_key].setText(str(value))

            # getting switches dict items
            switches_dict_items = dot_data['switches'].items()

            # restore switch states
            for switch_item in switches_dict_items:

                # getting current category/field name and state
                (category, field_name), state = switch_item

                full_key = (category, 'dots', target_key, field_name)
                if full_key in self.switch_registry:
                    self.switch_registry[full_key].setChecked(bool(state))

            # getting measurements dict items
            measurements_dict_items = dot_data['measurements'].items()

            # restore measurement states
            for measurement_item in measurements_dict_items:

                # getting current channel key/measurement states
                ch_key, meas_states = measurement_item

                reg_key = ('dots', target_key, ch_key)
                if reg_key in self.measurement_registry:
                    self.measurement_registry[reg_key]['intensity'].setChecked(meas_states['intensity'])
                    self.measurement_registry[reg_key]['texture'].setChecked(meas_states['texture'])

            # restore filter rows
            self.clear_filter_rows(reg_key=('dots', target_key))
            for column, condition in dot_data['filters']:
                self.add_filter_row(obj_type='dots', dot_key=target_key, column=column, condition=condition)

            # restore nuclear mask link
            self.set_dot_mask_link(block=self.dot_blocks[i], mask_name=dot_data['mask_link'])

    def remove_dot_block(self, target_idx: int) -> None:
        """
        Removes a dot block, preserves remaining
        field values, and re-indexes cleanly.

        Args:
            target_idx (int): 1-based index of dot to remove.

        Returns:
            None.
        """
        # preventing removal if only 1 dot left
        if len(self.dot_blocks) <= 1:
            return

        # collecting cache before destroying any UI elements
        cached_dots = self.collect_dots_cache()

        # removing the targeted dot from cache
        target_list_idx = target_idx - 1
        if 0 <= target_list_idx < len(cached_dots):
            cached_dots.pop(target_list_idx)

        # clearing existing GUI blocks
        for b in self.dot_blocks:
            b['param_card'].setParent(None)
            b['param_card'].deleteLater()
            b['toggle_card'].setParent(None)
            b['toggle_card'].deleteLater()
            b['add_toggle_card'].setParent(None)
            b['add_toggle_card'].deleteLater()

        self.dot_blocks.clear()

        # cleaning registries for all dot keys
        self.switch_registry = {k: v for k, v in self.switch_registry.items() if 'dots' not in k or len(k) < 3}
        self.entry_registry = {k: v for k, v in self.entry_registry.items() if 'dots' not in k or len(k) < 3}
        self.measurement_registry = {k: v for k, v in self.measurement_registry.items() if k[0] != 'dots'}
        self.filter_registry = {k: v for k, v in self.filter_registry.items() if k[0] != 'dots'}

        # re-adding dot blocks for remaining count
        for _ in range(len(cached_dots)):
            self.add_dot_block()

        # re-applying saved values to remaining dots
        self.apply_dots_cache(cached_dots)

    def rebuild_all_dots(self, count: int | None = None) -> None:
        """
        Clears existing dot cards and rebuilds
        'count' number of dot blocks cleanly.

        Args:
            count (int | None): Number of dot blocks to create; if None, use current count.

        Returns:
            None.
        """
        target_count = count if count is not None else len(self.dot_blocks)

        # clearing existing cards
        for b in self.dot_blocks:
            b['param_card'].setParent(None)
            b['param_card'].deleteLater()
            b['toggle_card'].setParent(None)
            b['toggle_card'].deleteLater()
            b['add_toggle_card'].setParent(None)
            b['add_toggle_card'].deleteLater()

        self.dot_blocks.clear()

        # removing stale dot keys from registries
        self.switch_registry = {k: v for k, v in self.switch_registry.items() if 'dots' not in k or len(k) < 3}
        self.entry_registry = {k: v for k, v in self.entry_registry.items() if 'dots' not in k or len(k) < 3}
        self.measurement_registry = {k: v for k, v in self.measurement_registry.items() if k[0] != 'dots'}
        self.filter_registry = {k: v for k, v in self.filter_registry.items() if k[0] != 'dots'}

        # re-adding dots
        for _ in range(target_count):
            self.add_dot_block()

    def build_ui(self) -> None:
        """
        Builds complete GUI layout and widgets.

        Returns:
            None.
        """
        main_layout = QVBoxLayout(self)

        # top file frame
        file_frame = QFrame()
        file_frame_layout = QVBoxLayout(file_frame)
        file_frame_layout.setContentsMargins(15, 15, 15, 5)
        main_layout.addWidget(file_frame)

        # button row
        button_row = QFrame()
        file_layout = QHBoxLayout(button_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_frame_layout.addWidget(button_row)

        btn_load_default = QPushButton(' Load Default Settings')
        load_default_settings_icon_path = str(ICONS_PATH.joinpath('load_default_settings.png'))
        if os.path.exists(load_default_settings_icon_path):
            btn_load_default.setIcon(QIcon(load_default_settings_icon_path))
        btn_load_default.setStyleSheet("background-color: #34495e;")
        btn_load_default.setFixedWidth(170)
        btn_load_default.setFont(self.font_main)
        btn_load_default.setToolTip(self.tooltip_for_control('btn_load_default_settings'))
        btn_load_default.clicked.connect(self.load_default_yaml)
        file_layout.addWidget(btn_load_default)

        btn_load = QPushButton(' Open Settings File...')
        open_settings_icon_path = str(ICONS_PATH.joinpath('open_settings.png'))
        if os.path.exists(open_settings_icon_path):
            btn_load.setIcon(QIcon(open_settings_icon_path))
        btn_load.setFixedWidth(170)
        btn_load.setFont(self.font_main)
        btn_load.setToolTip(self.tooltip_for_control('btn_open_settings_file'))
        btn_load.clicked.connect(self.browse_yaml_file)
        file_layout.addWidget(btn_load)
        file_layout.addStretch()

        # package version (same output as cet-version), left of update button
        self.lbl_version = QLabel()
        self.lbl_version.setFont(self.font_bold)
        file_layout.addWidget(self.lbl_version)
        self.refresh_version_label()

        self.btn_update_codes = QPushButton(' Update Codes')
        update_codes_icon_path = str(ICONS_PATH.joinpath('update.png'))
        if os.path.exists(update_codes_icon_path):
            self.btn_update_codes.setIcon(QIcon(update_codes_icon_path))
        self.btn_update_codes.setStyleSheet("background-color: #34495e;")
        self.btn_update_codes.setFixedWidth(170)
        self.btn_update_codes.setFont(self.font_main)
        self.btn_update_codes.setToolTip(self.tooltip_for_control('btn_update_codes'))
        self.btn_update_codes.clicked.connect(self.run_update_codes)
        file_layout.addWidget(self.btn_update_codes)

        # settings-file path row (below buttons)
        self.lbl_file = QLabel('Settings File: None Loaded')
        self.lbl_file.setFont(self.font_bold)
        file_frame_layout.addWidget(self.lbl_file)

        # main scrollable settings container
        self.scroll_frame = QScrollArea()
        self.scroll_frame.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_frame, stretch=1)

        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_frame.setWidget(scroll_widget)

        # ---------------- 0. Global Section Control Bar ----------------
        global_ctrl_frame = QFrame()
        global_ctrl_layout = QHBoxLayout(global_ctrl_frame)
        global_ctrl_layout.setContentsMargins(0, 0, 0, 5)
        self.scroll_layout.addWidget(global_ctrl_frame)

        lbl_global = QLabel('View Controls:')
        lbl_global.setFont(self.font_bold)
        lbl_global.setStyleSheet("color: #b3b3b3;")
        global_ctrl_layout.addWidget(lbl_global)

        btn_collapse_all = QPushButton('▲ Collapse All')
        btn_collapse_all.setStyleSheet("background-color: #34495e;")
        btn_collapse_all.setFixedSize(110, 26)
        btn_collapse_all.setFont(self.font_main)
        btn_collapse_all.setToolTip(self.tooltip_for_control('btn_collapse_all'))
        btn_collapse_all.clicked.connect(lambda: self.set_all_sections_state(expand=False))
        global_ctrl_layout.addWidget(btn_collapse_all)

        btn_expand_all = QPushButton('▼ Expand All')
        btn_expand_all.setStyleSheet("background-color: #34495e;")
        btn_expand_all.setFixedSize(110, 26)
        btn_expand_all.setFont(self.font_main)
        btn_expand_all.setToolTip(self.tooltip_for_control('btn_expand_all'))
        btn_expand_all.clicked.connect(lambda: self.set_all_sections_state(expand=True))
        global_ctrl_layout.addWidget(btn_expand_all)
        global_ctrl_layout.addStretch()

        # ---------------- 1. Experiment Settings ----------------
        exp_container = self.add_section_header(title='Experiment Settings', section_key='exp')
        exp_card = QFrame()
        exp_layout = QVBoxLayout(exp_card)
        exp_layout.setContentsMargins(10, 0, 10, 10)
        exp_container.layout().addWidget(exp_card)

        self.lbl_folder_path = QLabel('Base Folder: Not set')
        self.lbl_folder_path.setFont(self.font_main)
        self.lbl_folder_path.setStyleSheet("color: #b3b3b3;")
        exp_layout.addWidget(self.lbl_folder_path)

        folder_row = QFrame()
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 4, 0, 8)
        exp_layout.addWidget(folder_row)

        btn_browse_folder = QPushButton(' Select Base Folder')
        open_folder_icon_path = str(ICONS_PATH.joinpath('open_folder.png'))
        if os.path.exists(open_folder_icon_path):
            btn_browse_folder.setIcon(QIcon(open_folder_icon_path))
        btn_browse_folder.setFixedWidth(160)
        btn_browse_folder.setFont(self.font_main)
        btn_browse_folder.setToolTip(self.tooltip_for_control('btn_select_base_folder'))
        btn_browse_folder.clicked.connect(self.browse_base_folder)
        folder_layout.addWidget(btn_browse_folder)
        folder_layout.addStretch()

        # radio buttons container for image extension on its own vertical row
        ext_frame = QFrame()
        ext_layout = QVBoxLayout(ext_frame)
        ext_layout.setContentsMargins(0, 4, 0, 4)
        exp_layout.addWidget(ext_frame)

        lbl_ext = QLabel('Image Extension:')
        lbl_ext.setFont(self.font_main)
        lbl_ext.setToolTip(self.tooltip_for_control('radio_image_extension'))
        ext_layout.addWidget(lbl_ext)

        ext_row_frame = QFrame()
        ext_row_layout = QHBoxLayout(ext_row_frame)
        ext_row_layout.setContentsMargins(0, 2, 0, 2)
        ext_layout.addWidget(ext_row_frame)

        # image extensions list
        extensions = ['.vsi', '.nd2', '.ics', '.tif']

        # creating radio buttons
        for ext in extensions:
            rb = QRadioButton(ext)
            rb.setFont(self.font_main)
            rb.setToolTip(self.tooltip_for_control('radio_image_extension'))
            rb.toggled.connect(lambda checked, text=ext: self.set_image_ext(text, checked))
            if ext == self.image_ext_var:
                rb.setChecked(True)
            self.image_ext_btn_group.addButton(rb)
            ext_row_layout.addWidget(rb)

        ext_row_layout.addStretch()

        # ---------------- 2. Microscopy Settings ----------------
        mic_container = self.add_section_header(title='Microscopy Settings', section_key='mic')
        mic_card = QFrame()
        mic_layout = QVBoxLayout(mic_card)
        mic_layout.setContentsMargins(10, 0, 10, 10)
        mic_container.layout().addWidget(mic_card)

        self.add_entry_field(container=mic_card,
                             label_text='Numerical Aperture:',
                             key_path=('microscopy', 'numerical_aperture'),
                             width=120)
        self.add_entry_field(container=mic_card,
                             label_text='Refractive Index:',
                             key_path=('microscopy', 'refractive_index'),
                             width=120)
        self.add_entry_field(container=mic_card,
                             label_text='XY Scale (µm):',
                             key_path=('microscopy', 'xy_scale'),
                             width=120)
        self.add_entry_field(container=mic_card,
                             label_text='Z Scale (µm):',
                             key_path=('microscopy', 'z_scale'),
                             width=120)
        self.add_entry_field(container=mic_card,
                             label_text='Z Axis:',
                             key_path=('microscopy', 'z_axis'),
                             width=120)

        # ---------------- 3. Channels Settings (4 Columns, Transparent Background) ----------------
        ch_container = self.add_section_header(title='Channels Settings', section_key='channels')

        ch_cards_container = QFrame()
        ch_cards_layout = QHBoxLayout(ch_cards_container)
        ch_cards_layout.setContentsMargins(0, 0, 0, 10)
        ch_container.layout().addWidget(ch_cards_container)

        # helper to construct channels matching main background color
        def build_channel_card(parent_layout, ch_num):
            ch_card = QFrame()
            ch_card.setStyleSheet("background-color: transparent;")
            ch_layout = QVBoxLayout(ch_card)
            ch_layout.setContentsMargins(10, 10, 10, 10)
            parent_layout.addWidget(ch_card)

            lbl_ch = QLabel(f'Channel {ch_num} (ch{ch_num})')
            lbl_ch.setFont(self.font_bold)
            ch_layout.addWidget(lbl_ch)

            self.add_entry_field_compact(container=ch_card,
                                         label_text='Name:',
                                         key_path=('channels', f'ch{ch_num}', 'name'),
                                         width=180)
            self.add_entry_field_compact(container=ch_card,
                                         label_text='Wavelength (nm):',
                                         key_path=('channels', f'ch{ch_num}', 'wavelength'),
                                         width=180)

        for i in range(4):
            build_channel_card(ch_cards_layout, i)

        # ---------------- 4. Segmentation Object Parameters ----------------
        seg_container = self.add_section_header(title='Segmentation Object Parameters', section_key='segmentation')

        btn_add_dot_row = QFrame()
        btn_add_dot_layout = QHBoxLayout(btn_add_dot_row)
        btn_add_dot_layout.setContentsMargins(0, 0, 0, 5)
        seg_container.layout().addWidget(btn_add_dot_row)

        btn_add_dot_layout.addStretch()
        btn_add_dot = QPushButton(' Add Dot')
        plus_icon_path = str(ICONS_PATH.joinpath('add.png'))
        if os.path.exists(plus_icon_path):
            btn_add_dot.setIcon(QIcon(plus_icon_path))
        btn_add_dot.setFixedSize(95, 26)
        btn_add_dot.setFont(self.font_main)
        btn_add_dot.setToolTip(self.tooltip_for_control('btn_add_dot'))
        btn_add_dot.clicked.connect(self.add_dot_block)
        btn_add_dot_layout.addWidget(btn_add_dot)

        # embryos parameters
        emb_card = QFrame()
        emb_layout = QVBoxLayout(emb_card)
        emb_layout.setContentsMargins(10, 8, 10, 10)
        seg_container.layout().addWidget(emb_card)

        lbl_emb = QLabel('Embryos Parameters')
        lbl_emb.setFont(self.font_bold)
        emb_layout.addWidget(lbl_emb)

        # Segmentation Settings subsection toggles placed in a single inline row
        emb_sw_row = QFrame()
        emb_sw_layout = QHBoxLayout(emb_sw_row)
        emb_sw_layout.setContentsMargins(0, 4, 0, 4)
        emb_card.layout().addWidget(emb_sw_row)

        self.add_switch_to_container(container=emb_sw_row,
                                     label_text='Deconvolve',
                                     key_path=('segmentation', 'embryos', 'deconvolve'),
                                     inline=True)
        self.add_switch_to_container(container=emb_sw_row,
                                     label_text='Blur',
                                     key_path=('segmentation', 'embryos', 'blur'),
                                     inline=True)
        self.add_switch_to_container(container=emb_sw_row,
                                     label_text='Close Masks',
                                     key_path=('segmentation', 'embryos', 'close_masks'),
                                     inline=True)
        self.add_switch_to_container(container=emb_sw_row,
                                     label_text='Merge Masks',
                                     key_path=('segmentation', 'embryos', 'merge_masks'),
                                     inline=True)
        self.add_switch_to_container(container=emb_sw_row,
                                     label_text='Resize Masks',
                                     key_path=('segmentation', 'embryos', 'resize_masks'),
                                     inline=True)
        self.add_switch_to_container(container=emb_sw_row,
                                     label_text='Create Borders Masks',
                                     key_path=('segmentation', 'embryos', 'create_borders_masks'),
                                     inline=True)
        emb_sw_layout.addStretch()

        self.add_entry_field(container=emb_card,
                             label_text='Channel:',
                             key_path=('segmentation', 'embryos', 'segmentation_channel'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Blur Sigma:',
                             key_path=('segmentation', 'embryos', 'blur_sigma'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Diameter:',
                             key_path=('segmentation', 'embryos', 'diameter'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Closing Dist:',
                             key_path=('segmentation', 'embryos', 'closing_distance'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Merge Solidity Thresh:',
                             key_path=('segmentation', 'embryos', 'merge_solidity_threshold'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Merge Touch Margin:',
                             key_path=('segmentation', 'embryos', 'merge_touch_margin'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Dilation:',
                             key_path=('segmentation', 'embryos', 'dilation'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Smooth Iterations:',
                             key_path=('segmentation', 'embryos', 'smooth_iterations'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Borders Thickness:',
                             key_path=('segmentation', 'embryos', 'borders_thickness'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Borders Description:',
                             key_path=('segmentation', 'embryos', 'borders_description'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Margin:',
                             key_path=('segmentation', 'embryos', 'margin'),
                             width=120)
        self.add_entry_field(container=emb_card,
                             label_text='Batch Size:',
                             key_path=('segmentation', 'embryos', 'batch_size'),
                             width=120)

        self.add_entry_field(container=emb_card,
                             label_text='Min Size:',
                             key_path=('segmentation', 'embryos', 'min_size'),
                             width=120)

        # Measurements subpanel for Embryos
        self.emb_meas_container = QFrame()
        emb_meas_layout = QVBoxLayout(self.emb_meas_container)
        emb_meas_layout.setContentsMargins(0, 5, 0, 5)
        emb_card.layout().addWidget(self.emb_meas_container)
        self.build_measurements_subpanel(container=self.emb_meas_container, obj_type='embryos')

        # Filters subpanel for Embryos
        self.build_filters_subpanel(container=emb_card, obj_type='embryos')

        # subsection separator between embryos and nuclei
        self.add_subsection_separator(container=seg_container)

        # nuclei parameters
        nuc_card = QFrame()
        nuc_layout = QVBoxLayout(nuc_card)
        nuc_layout.setContentsMargins(10, 8, 10, 10)
        seg_container.layout().addWidget(nuc_card)

        lbl_nuc = QLabel('Nuclei Parameters')
        lbl_nuc.setFont(self.font_bold)
        nuc_layout.addWidget(lbl_nuc)

        # Segmentation Settings subsection toggles placed in a single inline row
        nuc_sw_row = QFrame()
        nuc_sw_layout = QHBoxLayout(nuc_sw_row)
        nuc_sw_layout.setContentsMargins(0, 4, 0, 4)
        nuc_card.layout().addWidget(nuc_sw_row)

        self.add_switch_to_container(container=nuc_sw_row,
                                     label_text='Deconvolve',
                                     key_path=('segmentation', 'nuclei', 'deconvolve'),
                                     inline=True)
        self.add_switch_to_container(container=nuc_sw_row,
                                     label_text='Blur',
                                     key_path=('segmentation', 'nuclei', 'blur'),
                                     inline=True)
        self.add_switch_to_container(container=nuc_sw_row,
                                     label_text='Close Masks',
                                     key_path=('segmentation', 'nuclei', 'close_masks'),
                                     inline=True)
        self.add_switch_to_container(container=nuc_sw_row,
                                     label_text='Merge Masks',
                                     key_path=('segmentation', 'nuclei', 'merge_masks'),
                                     inline=True)
        self.add_switch_to_container(container=nuc_sw_row,
                                     label_text='Resize Masks',
                                     key_path=('segmentation', 'nuclei', 'resize_masks'),
                                     inline=True)
        self.add_switch_to_container(container=nuc_sw_row,
                                     label_text='Create Borders Masks',
                                     key_path=('segmentation', 'nuclei', 'create_borders_masks'),
                                     inline=True)
        nuc_sw_layout.addStretch()

        self.add_entry_field(container=nuc_card,
                             label_text='Channel:',
                             key_path=('segmentation', 'nuclei', 'segmentation_channel'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Blur Sigma:',
                             key_path=('segmentation', 'nuclei', 'blur_sigma'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Diameter:',
                             key_path=('segmentation', 'nuclei', 'diameter'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Closing Dist:',
                             key_path=('segmentation', 'nuclei', 'closing_distance'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Merge Solidity Thresh:',
                             key_path=('segmentation', 'nuclei', 'merge_solidity_threshold'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Merge Touch Margin:',
                             key_path=('segmentation', 'nuclei', 'merge_touch_margin'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Dilation:',
                             key_path=('segmentation', 'nuclei', 'dilation'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Smooth Iterations:',
                             key_path=('segmentation', 'nuclei', 'smooth_iterations'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Borders Thickness:',
                             key_path=('segmentation', 'nuclei', 'borders_thickness'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Borders Description:',
                             key_path=('segmentation', 'nuclei', 'borders_description'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Margin:',
                             key_path=('segmentation', 'nuclei', 'margin'),
                             width=120)
        self.add_entry_field(container=nuc_card,
                             label_text='Batch Size:',
                             key_path=('segmentation', 'nuclei', 'batch_size'),
                             width=120)

        self.add_entry_field(container=nuc_card,
                             label_text='Min Size:',
                             key_path=('segmentation', 'nuclei', 'min_size'),
                             width=120)

        # nuclear mask link radio buttons (optional: which nuclei* mask folder is the input of the nuclei objects table)
        self.nuc_mask_state = {'value': DEFAULT_NUCLEI_MASK_LINK, 'radios': {}, 'group': QButtonGroup(nuc_card)}
        nuc_mask_row = QFrame()
        nuc_mask_row_layout = QGridLayout(nuc_mask_row)
        nuc_mask_row_layout.setContentsMargins(0, 4, 0, 4)
        nuc_card.layout().addWidget(nuc_mask_row)

        lbl_nuc_mask_link = QLabel('Link to masks:')
        lbl_nuc_mask_link.setFont(self.font_main)
        lbl_nuc_mask_link.setToolTip(self.tooltip_for_control('radio_nuclei_mask_link'))
        nuc_mask_row_layout.addWidget(lbl_nuc_mask_link, 0, 0)

        for i, mask_name in enumerate(NUCLEI_MASK_NAMES):
            rb = QRadioButton(mask_name)
            rb.setFont(self.font_main)
            rb.setToolTip(self.tooltip_for_control('radio_nuclei_mask_link'))
            rb.toggled.connect(lambda checked, v=mask_name, s=self.nuc_mask_state: s.update(value=v) if checked else None)
            if mask_name == self.nuc_mask_state['value']:
                rb.setChecked(True)
            self.nuc_mask_state['group'].addButton(rb)
            self.nuc_mask_state['radios'][mask_name] = rb
            nuc_mask_row_layout.addWidget(rb, 1 + i // 3, i % 3)

        # Measurements subpanel for Nuclei
        self.nuc_meas_container = QFrame()
        nuc_meas_layout = QVBoxLayout(self.nuc_meas_container)
        nuc_meas_layout.setContentsMargins(0, 5, 0, 5)
        nuc_card.layout().addWidget(self.nuc_meas_container)
        self.build_measurements_subpanel(container=self.nuc_meas_container, obj_type='nuclei')

        # Filters subpanel for Nuclei
        self.build_filters_subpanel(container=nuc_card, obj_type='nuclei')

        # subsection separator between nuclei and dots
        self.add_subsection_separator(container=seg_container)

        # dynamic dots parameter container
        self.dots_param_container = QFrame()
        self.dots_param_container_layout = QVBoxLayout(self.dots_param_container)
        self.dots_param_container_layout.setContentsMargins(0, 0, 0, 10)
        seg_container.layout().addWidget(self.dots_param_container)

        # ---------------- 5. Additional Settings ----------------
        add_settings_container = self.add_section_header(title='Additional Settings',
                                                         section_key='additional_toggles',
                                                         master_key='additional_toggles')

        self.create_toggle_group(parent_container=add_settings_container,
                                 group_title='General Image Processing',
                                 toggles=[('Map Nuclei to Images', ('additional_toggles', 'map_nuclei_to_images'))])
        self.add_subsection_separator(container=add_settings_container)

        self.create_toggle_group(parent_container=add_settings_container,
                                 group_title='Signal Measurements Toggles',
                                 toggles=[('Embryos Border Signal',
                                           ('additional_toggles', 'signal_measurements', 'embryos_border_signal')),
                                          ('Nuclei Border Signal',
                                           ('additional_toggles', 'signal_measurements', 'nuclei_border_signal'))])
        self.add_subsection_separator(container=add_settings_container)

        self.create_toggle_group(parent_container=add_settings_container,
                                 group_title='Nuclei Additional Toggles',
                                 toggles=[
                                     ('Pairwise Distances', ('additional_toggles', 'nuclei', 'pairwise_distances')),
                                     ('Border Distances', ('additional_toggles', 'nuclei', 'border_distances'))])
        self.add_subsection_separator(container=add_settings_container)

        # dynamic dots additional toggles container
        self.dots_add_toggle_container = QFrame()
        self.dots_add_toggle_container_layout = QVBoxLayout(self.dots_add_toggle_container)
        self.dots_add_toggle_container_layout.setContentsMargins(0, 0, 0, 10)
        add_settings_container.layout().addWidget(self.dots_add_toggle_container)

        self.add_subsection_separator(container=add_settings_container)

        # general dots settings card
        dots_add_card = QFrame()
        dots_add_layout = QVBoxLayout(dots_add_card)
        dots_add_layout.setContentsMargins(10, 8, 10, 10)
        add_settings_container.layout().addWidget(dots_add_card)

        lbl_dots_gen = QLabel('General Dots Settings')
        lbl_dots_gen.setFont(self.font_bold)
        dots_add_layout.addWidget(lbl_dots_gen)

        self.add_switch_to_container(container=dots_add_card,
                                     label_text='Calculate Dots Distances',
                                     key_path=('additional_toggles', 'calculate_dots_distances'))

        self.add_entry_field(container=dots_add_card,
                             label_text='Overlap Threshold:',
                             key_path=('additional_toggles', 'overlap_threshold'),
                             width=120)

        self.add_entry_field(container=dots_add_card,
                             label_text='Dot1 Description:',
                             key_path=('additional_toggles', 'dots_distance_dot1_description'),
                             width=120)

        self.add_entry_field(container=dots_add_card,
                             label_text='Dot2 Description:',
                             key_path=('additional_toggles', 'dots_distance_dot2_description'),
                             width=120)

        # radio buttons for dots distance mode, on its own row
        lbl_dots_distance_mode = QLabel('Dots Distance Mode:')
        lbl_dots_distance_mode.setFont(self.font_main)
        lbl_dots_distance_mode.setToolTip(self.tooltip_for_control('radio_dots_distance_mode'))
        dots_add_layout.addWidget(lbl_dots_distance_mode)

        dots_distance_mode_row = QFrame()
        dots_distance_mode_layout = QHBoxLayout(dots_distance_mode_row)
        dots_distance_mode_layout.setContentsMargins(0, 2, 0, 2)
        dots_add_layout.addWidget(dots_distance_mode_row)

        dots_distance_modes = [('Hungarian', 'hungarian'), ('Legacy', 'legacy')]

        for label, value in dots_distance_modes:
            rb = QRadioButton(label)
            rb.setFont(self.font_main)
            rb.setToolTip(self.tooltip_for_control('radio_dots_distance_mode'))
            rb.toggled.connect(lambda checked, v=value: self.set_dots_distance_mode(v, checked))
            if value == self.dots_distance_mode_var:
                rb.setChecked(True)
            self.dots_distance_mode_btn_group.addButton(rb)
            dots_distance_mode_layout.addWidget(rb)

        dots_distance_mode_layout.addStretch()

        # ---------------- 6. CeSCALE Settings ----------------
        cescale_container = self.add_section_header(title='CeSCALE Settings', section_key='cescale')
        cescale_card = QFrame()
        cescale_layout = QVBoxLayout(cescale_card)
        cescale_layout.setContentsMargins(10, 0, 10, 10)
        cescale_container.layout().addWidget(cescale_card)

        lbl_cescale_dataset = QLabel('Reference Dataset:')
        lbl_cescale_dataset.setFont(self.font_main)
        lbl_cescale_dataset.setToolTip(self.tooltip_for_control('radio_cescale_reference_dataset'))
        cescale_layout.addWidget(lbl_cescale_dataset)

        cescale_dataset_row = QFrame()
        cescale_dataset_layout = QHBoxLayout(cescale_dataset_row)
        cescale_dataset_layout.setContentsMargins(0, 2, 0, 8)
        cescale_layout.addWidget(cescale_dataset_row)

        # cescale reference datasets list
        cescale_datasets = [('Bao', 'bao'), ('Dryad', 'dryad')]

        # creating radio buttons
        for label, value in cescale_datasets:
            rb = QRadioButton(label)
            rb.setFont(self.font_main)
            rb.setToolTip(self.tooltip_for_control('radio_cescale_reference_dataset'))
            rb.toggled.connect(lambda checked, v=value: self.set_cescale_dataset(v, checked))
            if value == self.cescale_dataset_var:
                rb.setChecked(True)
            self.cescale_dataset_btn_group.addButton(rb)
            cescale_dataset_layout.addWidget(rb)

        cescale_dataset_layout.addStretch()

        # optional gene expression table (passed to generate_lineages_df)
        cescale_gene_expression_row = QFrame()
        cescale_gene_expression_layout = QHBoxLayout(cescale_gene_expression_row)
        cescale_gene_expression_layout.setContentsMargins(0, 3, 0, 3)
        cescale_layout.addWidget(cescale_gene_expression_row)

        lbl_cescale_gene_expression = QLabel('Gene Expression Table:')
        lbl_cescale_gene_expression.setFont(self.font_main)
        lbl_cescale_gene_expression.setFixedWidth(160)
        lbl_cescale_gene_expression.setToolTip(self.tooltip_for_control('entry_cescale_gene_expression_path'))
        cescale_gene_expression_layout.addWidget(lbl_cescale_gene_expression)

        self.cescale_gene_expression_entry = QLineEdit()
        self.cescale_gene_expression_entry.setFont(self.font_main)
        self.cescale_gene_expression_entry.setPlaceholderText('Not set')
        self.cescale_gene_expression_entry.setToolTip(self.tooltip_for_control('entry_cescale_gene_expression_path'))
        self.cescale_gene_expression_entry.setFixedWidth(240)
        cescale_gene_expression_layout.addWidget(self.cescale_gene_expression_entry)

        btn_cescale_gene_expression = QPushButton('Browse')
        btn_cescale_gene_expression.setFont(self.font_main)
        btn_cescale_gene_expression.setToolTip(self.tooltip_for_control('entry_cescale_gene_expression_path'))
        btn_cescale_gene_expression.clicked.connect(self.browse_cescale_gene_expression)
        cescale_gene_expression_layout.addWidget(btn_cescale_gene_expression)
        cescale_gene_expression_layout.addStretch()

        # lineage tree plot settings (passed to plot_lineage_tree)
        for tree_key, tree_label, tree_default in self.cescale_tree_entries_spec:
            tree_row = QFrame()
            tree_row_layout = QHBoxLayout(tree_row)
            tree_row_layout.setContentsMargins(0, 3, 0, 3)
            cescale_layout.addWidget(tree_row)

            lbl_tree = QLabel(tree_label)
            lbl_tree.setFont(self.font_main)
            lbl_tree.setFixedWidth(160)
            lbl_tree.setToolTip(self.tooltip_for_control(f'entry_cescale_{tree_key}'))
            tree_row_layout.addWidget(lbl_tree)

            tree_entry = QLineEdit()
            tree_entry.setFont(self.font_main)
            tree_entry.setText(tree_default)
            tree_entry.setPlaceholderText('Not set' if not tree_default else '')
            tree_entry.setToolTip(self.tooltip_for_control(f'entry_cescale_{tree_key}'))
            tree_entry.setFixedWidth(120)
            tree_row_layout.addWidget(tree_entry)
            tree_row_layout.addStretch()
            self.cescale_tree_entries.update({tree_key: tree_entry})

        # ---------------- 7. Pipeline Toggles ----------------
        pipe_toggles_container = self.add_section_header(title='Pipeline Toggles',
                                                         section_key='pipeline_toggles',
                                                         master_key='pipeline_toggles')

        self.create_toggle_group(parent_container=pipe_toggles_container,
                                 group_title='Base Pipeline',
                                 toggles=[('Initial Preprocessing', ('pipeline_toggles', 'initial_preprocessing')),
                                          ('Generate Final Tables', ('pipeline_toggles', 'generate_final_tables')),
                                          ('Run CeSCALE Lineage Alignment', ('pipeline_toggles', 'run_cescale'))])
        self.add_subsection_separator(container=pipe_toggles_container)

        self.create_toggle_group(parent_container=pipe_toggles_container,
                                 group_title='Embryos Toggles',
                                 toggles=[('Image Preprocessing', ('pipeline_toggles', 'embryos', 'image_preprocessing')),
                                          ('Segmentation', ('pipeline_toggles', 'embryos', 'segmentation')),
                                          ('Masks Postprocessing', ('pipeline_toggles', 'embryos', 'masks_postprocessing')),
                                          ('Create Tables', ('pipeline_toggles', 'embryos', 'create_tables')),
                                          ('Create Crops', ('pipeline_toggles', 'embryos', 'create_crops'))])
        self.add_subsection_separator(container=pipe_toggles_container)

        self.create_toggle_group(parent_container=pipe_toggles_container,
                                 group_title='Nuclei Toggles',
                                 toggles=[('Image Preprocessing', ('pipeline_toggles', 'nuclei', 'image_preprocessing')),
                                          ('Segmentation', ('pipeline_toggles', 'nuclei', 'segmentation')),
                                          ('Masks Postprocessing', ('pipeline_toggles', 'nuclei', 'masks_postprocessing')),
                                          ('Create Tables', ('pipeline_toggles', 'nuclei', 'create_tables')),
                                          ('Create Crops', ('pipeline_toggles', 'nuclei', 'create_crops'))])
        self.add_subsection_separator(container=pipe_toggles_container)

        self.create_toggle_group(parent_container=pipe_toggles_container,
                                 group_title='Cytoplasm Toggles',
                                 toggles=[('Image Preprocessing', ('pipeline_toggles', 'cytoplasm', 'image_preprocessing')),
                                          ('Segmentation', ('pipeline_toggles', 'cytoplasm', 'segmentation')),
                                          ('Masks Postprocessing', ('pipeline_toggles', 'cytoplasm', 'masks_postprocessing')),
                                          ('Create Tables', ('pipeline_toggles', 'cytoplasm', 'create_tables')),
                                          ('Create Crops', ('pipeline_toggles', 'cytoplasm', 'create_crops'))])
        self.add_subsection_separator(container=pipe_toggles_container)

        # dynamic dots toggle container
        self.dots_toggle_container = QFrame()
        self.dots_toggle_container_layout = QVBoxLayout(self.dots_toggle_container)
        self.dots_toggle_container_layout.setContentsMargins(0, 0, 0, 10)
        pipe_toggles_container.layout().addWidget(self.dots_toggle_container)

        # default init with 2 dots
        self.add_dot_block()
        self.add_dot_block()

        # ---------------- 8. Runtime Options ----------------
        runtime_container = self.add_section_header(title='Runtime Options',
                                                    section_key='runtime',
                                                    master_key='runtime')

        self.create_toggle_group(parent_container=runtime_container,
                                 group_title='Execution Controls',
                                 toggles=[('Skip Enter', ('runtime', 'skip_enter')),
                                          ('Overwrite Output', ('runtime', 'overwrite_output')),
                                          ('Simulate Run', ('runtime', 'simulate_run')),
                                          ('Clear Intermediate Files', ('runtime', 'clear_intermediate_files'))])

        # console output log frame
        console_frame = QFrame()
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(15, 5, 15, 5)
        main_layout.addWidget(console_frame)

        lbl_console = QLabel('Execution Output')
        lbl_console.setFont(self.font_bold)
        console_layout.addWidget(lbl_console)

        self.txt_console = QTextEdit()
        self.txt_console.setFont(self.font_console)
        self.txt_console.setFixedHeight(200)
        self.txt_console.setReadOnly(True)
        console_layout.addWidget(self.txt_console)

        # bottom action bar
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(15, 0, 15, 15)
        main_layout.addWidget(bottom_frame)

        self.lbl_status = QLabel('')
        self.lbl_status.setFont(self.font_main)
        bottom_layout.addWidget(self.lbl_status, stretch=1)

        btn_open_napari = QPushButton(' Open Napari')
        open_napari_icon_path = str(ICONS_PATH.joinpath('open_napari.png'))
        if os.path.exists(open_napari_icon_path):
            btn_open_napari.setIcon(QIcon(open_napari_icon_path))
        btn_open_napari.setFixedWidth(130)
        btn_open_napari.setFont(self.font_main)
        btn_open_napari.setToolTip(self.tooltip_for_control('btn_open_napari'))
        btn_open_napari.clicked.connect(self.launch_napari_viewer)
        bottom_layout.addWidget(btn_open_napari)

        btn_save = QPushButton(' Save Settings')
        save_icon_path = str(ICONS_PATH.joinpath('save.png'))
        if os.path.exists(save_icon_path):
            btn_save.setIcon(QIcon(save_icon_path))
        btn_save.setFixedWidth(130)
        btn_save.setFont(self.font_main)
        btn_save.setToolTip(self.tooltip_for_control('btn_save_settings'))
        btn_save.clicked.connect(self.save_yaml)
        bottom_layout.addWidget(btn_save)

        btn_save_as = QPushButton(' Save As...')
        save_as_icon_path = str(ICONS_PATH.joinpath('save_as.png'))
        if os.path.exists(save_as_icon_path):
            btn_save_as.setIcon(QIcon(save_as_icon_path))
        btn_save_as.setFixedWidth(120)
        btn_save_as.setFont(self.font_main)
        btn_save_as.setToolTip(self.tooltip_for_control('btn_save_as'))
        btn_save_as.clicked.connect(self.save_as_yaml)
        bottom_layout.addWidget(btn_save_as)

        self.btn_abort = QPushButton(' Abort')
        abort_icon_path = str(ICONS_PATH.joinpath('abort.png'))
        if os.path.exists(abort_icon_path):
            self.btn_abort.setIcon(QIcon(abort_icon_path))
        self.btn_abort.setStyleSheet("background-color: #c0392b;")
        self.btn_abort.setFixedWidth(100)
        self.btn_abort.setFont(self.font_main)
        self.btn_abort.setToolTip(self.tooltip_for_control('btn_abort'))
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self.abort_execution)
        bottom_layout.addWidget(self.btn_abort)

        self.btn_enter = QPushButton(' Send Enter')
        enter_icon_path = str(ICONS_PATH.joinpath('enter.png'))
        if os.path.exists(enter_icon_path):
            self.btn_enter.setIcon(QIcon(enter_icon_path))
        self.btn_enter.setFixedWidth(120)
        self.btn_enter.setFont(self.font_main)
        self.btn_enter.setToolTip(self.tooltip_for_control('btn_send_enter'))
        self.btn_enter.setEnabled(False)
        self.btn_enter.clicked.connect(self.send_enter_to_process)
        bottom_layout.addWidget(self.btn_enter)

        self.btn_save_run = QPushButton(' Save && Run')
        play_icon_path = str(ICONS_PATH.joinpath('run.png'))
        if os.path.exists(play_icon_path):
            self.btn_save_run.setIcon(QIcon(play_icon_path))
        self.btn_save_run.setStyleSheet("background-color: #2ba02d;")
        self.btn_save_run.setFixedWidth(120)
        self.btn_save_run.setFont(self.font_main)
        self.btn_save_run.setToolTip(self.tooltip_for_control('btn_save_run'))
        self.btn_save_run.clicked.connect(self.save_and_run)
        bottom_layout.addWidget(self.btn_save_run)

    def set_image_ext(self, text: str, checked: bool) -> None:
        """
        Updates the target image extension variable.

        Args:
            text (str): Image extension string (e.g. '.vsi').
            checked (bool): True if radio button is selected.

        Returns:
            None.
        """
        if checked:
            self.image_ext_var = text

    def set_cescale_dataset(self, value: str, checked: bool) -> None:
        """
        Updates the target CeSCALE reference
        dataset variable.

        Args:
            value (str): Reference dataset value ('bao' or 'dryad').
            checked (bool): True if radio button is selected.

        Returns:
            None.
        """
        if checked:
            self.cescale_dataset_var = value

    def set_dots_distance_mode(self, value: str, checked: bool) -> None:
        """
        Updates the target dots distance
        matching algorithm variable.

        Args:
            value (str): Distance mode value ('hungarian' or 'legacy').
            checked (bool): True if radio button is selected.

        Returns:
            None.
        """
        if checked:
            self.dots_distance_mode_var = value

    def browse_yaml_file(self) -> None:
        """
        Opens file dialog to select YAML file.

        Returns:
            None.
        """
        # opening file selection dialog
        file_selected, _ = QFileDialog.getOpenFileName(self, 'Open YAML', '', 'YAML Files (*.yaml *.yml)')

        # checking if file selected
        if file_selected:
            # loading selected yaml file
            self.load_yaml(path=file_selected)

    def load_default_yaml(self) -> None:
        """
        Loads default YAML settings defined by
        DEFAULT_SETTINGS_PATH constant.

        Returns:
            None.
        """
        if os.path.exists(DEFAULT_SETTINGS_PATH):
            self.load_yaml(path=DEFAULT_SETTINGS_PATH, is_default=True)
        else:
            self.lbl_status.setText(f'Default settings file not found at: {DEFAULT_SETTINGS_PATH}')
            self.lbl_status.setStyleSheet("color: red;")

    def browse_cescale_gene_expression(self) -> None:
        """
        Opens file dialog to select the optional
        lineage-specific gene expression table.

        Returns:
            None.
        """
        # opening file selection dialog
        file_selected, _ = QFileDialog.getOpenFileName(self, 'Select Gene Expression Table', '',
                                                       'CSV Files (*.csv)')

        # updating entry text (formatting backslashes)
        if file_selected:
            self.cescale_gene_expression_entry.setText(file_selected.replace('\\', '/'))

    def browse_base_folder(self) -> None:
        """
        Opens folder dialog to select base
        directory.

        Returns:
            None.
        """
        # opening folder selection dialog
        folder_selected = QFileDialog.getExistingDirectory(self, 'Select Base Folder')

        # checking if folder selected
        if folder_selected:
            # formatting backslashes
            formatted_path = folder_selected.replace('\\', '/')

            # updating label text
            self.lbl_folder_path.setText(formatted_path)
            self.lbl_folder_path.setStyleSheet("color: white;")

    def load_yaml(self,
                  path: str,
                  is_default: bool = False
                  ) -> None:
        """
        Loads YAML file into GUI controls.

        Args:
            path (str): Path to YAML settings file.
            is_default (bool): True if loading default template file.

        Returns:
            None.
        """
        # updating file path attributes
        self.file_path = path
        self.is_default_loaded = is_default

        lbl_prefix = '[DEFAULT] ' if is_default else ''
        self.lbl_file.setText(f'Settings File: {lbl_prefix}{path}')

        # opening and loading file
        try:

            # reading file
            with open(path, 'r', encoding='utf-8') as f:

                # loading config data
                self.config_data = self.yaml.load(f)

            # loading base folder
            base_folder = get_nested_val(data=self.config_data,
                                              key_path=('experiment', 'base_folder'))
            if not base_folder:
                base_folder = 'Not set'
            self.lbl_folder_path.setText(str(base_folder))
            self.lbl_folder_path.setStyleSheet("color: white;")

            # loading cescale reference dataset
            cescale_dataset = get_nested_val(data=self.config_data,
                                                  key_path=('cescale', 'reference_dataset'))
            if cescale_dataset:
                self.cescale_dataset_var = str(cescale_dataset)
            for rb in self.cescale_dataset_btn_group.buttons():
                if rb.text().lower() == self.cescale_dataset_var:
                    rb.setChecked(True)

            # loading cescale gene expression path (empty if unset)
            cescale_gene_expression = get_nested_val(data=self.config_data,
                                                     key_path=('cescale', 'gene_expression_path'))
            self.cescale_gene_expression_entry.setText(str(cescale_gene_expression)
                                                       if cescale_gene_expression else '')

            # loading cescale lineage tree plot settings (unset values fall back to the default text)
            for tree_key, _, tree_default in self.cescale_tree_entries_spec:
                tree_val = get_nested_val(data=self.config_data, key_path=('cescale', tree_key))
                if isinstance(tree_val, list):
                    tree_text = ' '.join(str(item) for item in tree_val)
                elif tree_val is None:
                    tree_text = tree_default
                else:
                    tree_text = str(tree_val)
                self.cescale_tree_entries[tree_key].setText(tree_text)

            # loading dots distance mode
            dots_distance_mode = get_nested_val(data=self.config_data,
                                                     key_path=('additional_toggles', 'dots_distance_mode'))
            if dots_distance_mode:
                self.dots_distance_mode_var = str(dots_distance_mode)
            for rb in self.dots_distance_mode_btn_group.buttons():
                if rb.text().lower() == self.dots_distance_mode_var:
                    rb.setChecked(True)

            # loading image extension value
            img_ext = get_nested_val(data=self.config_data,
                                          key_path=('experiment', 'image_extension'))
            if img_ext:
                self.image_ext_var = str(img_ext)
                for rb in self.image_ext_btn_group.buttons():
                    if rb.text() == self.image_ext_var:
                        rb.setChecked(True)

            # detecting number of dots in YAML file
            dots_in_yaml = get_nested_val(data=self.config_data,
                                               key_path=('segmentation', 'dots'))
            if isinstance(dots_in_yaml, dict):
                num_dots = len(dots_in_yaml)
                if num_dots > 0:
                    self.rebuild_all_dots(count=num_dots)

            # getting entry registry dict items
            entry_dict_items = self.entry_registry.items()

            # loading text entry values with signals temporarily blocked
            for entry_item in entry_dict_items:

                # getting current entry key path/entry
                key_path, entry = entry_item

                entry.blockSignals(True)

                # getting nested value
                val = get_nested_val(data=self.config_data,
                                          key_path=key_path)

                # updating entry widget
                entry.clear()
                if val is not None:
                    entry.setText(str(val))

                entry.blockSignals(False)

            # getting switch registry dict items
            switch_dict_items = self.switch_registry.items()

            # loading switches states
            for switch_item in switch_dict_items:

                # getting current switch key path/switch
                key_path, switch = switch_item

                # getting nested value
                val = get_nested_val(data=self.config_data,
                                          key_path=key_path)

                # setting switch state
                if val:
                    switch.setChecked(True)
                else:
                    switch.setChecked(False)

            # updating measurement UI panels to match loaded channels
            self.update_all_measurements_ui()

            # loading measurement toggles from yaml configuration
            self.load_measurements_from_yaml(obj_type='embryos',
                                             meas_dict=get_nested_val(self.config_data, ('segmentation', 'embryos', 'measurements')))
            self.load_measurements_from_yaml(obj_type='nuclei',
                                             meas_dict=get_nested_val(self.config_data, ('segmentation', 'nuclei', 'measurements')))

            # loading nuclear mask link (the nuclei* key in the nuclei measurements, default if absent)
            nuc_meas = get_nested_val(self.config_data, ('segmentation', 'nuclei', 'measurements'))
            nuc_mask_keys = [k for k in nuc_meas if k in NUCLEI_MASK_NAMES] if isinstance(nuc_meas, dict) else []
            self.nuc_mask_state['radios'][
                nuc_mask_keys[0] if len(nuc_mask_keys) == 1 else DEFAULT_NUCLEI_MASK_LINK].setChecked(True)

            # loading filters from yaml configuration
            self.load_filters_from_yaml(obj_type='embryos',
                                        filters_dict=get_nested_val(self.config_data, ('segmentation', 'embryos', 'filters')))
            self.load_filters_from_yaml(obj_type='nuclei',
                                        filters_dict=get_nested_val(self.config_data, ('segmentation', 'nuclei', 'filters')))

            if isinstance(dots_in_yaml, dict):
                for dot_key in dots_in_yaml:
                    dot_meas = get_nested_val(self.config_data, ('segmentation', 'dots', dot_key, 'measurements'))
                    self.load_measurements_from_yaml(obj_type='dots', dot_key=dot_key, meas_dict=dot_meas)
                    self.load_filters_from_yaml(obj_type='dots',
                                                dot_key=dot_key,
                                                filters_dict=get_nested_val(self.config_data,
                                                                            ('segmentation', 'dots', dot_key, 'filters')))

                    # loading nuclear mask link (the nuclei* key in the dot's measurements)
                    mask_keys = [k for k in dot_meas if k in NUCLEI_MASK_NAMES] if isinstance(dot_meas, dict) else []
                    block = next((b for b in self.dot_blocks if b['dot_key'] == dot_key), None)
                    if block is not None:
                        self.set_dot_mask_link(block=block,
                                               mask_name=mask_keys[0] if len(mask_keys) == 1 else DEFAULT_DOT_MASK_LINK)

            # greying out mask options unavailable with the loaded nuclei settings
            self.update_dot_mask_options()

            # updating status label
            self.lbl_status.setText('Settings loaded successfully!')
            self.lbl_status.setStyleSheet("color: #2fa572;")

        # handling loading exceptions
        except Exception as exception:

            # updating status label with error
            self.lbl_status.setText(f'Error loading file: {exception}')
            self.lbl_status.setStyleSheet("color: red;")

    def load_measurements_from_yaml(self,
                                    obj_type: str,
                                    meas_dict: dict | None,
                                    dot_key: str | None = None
                                    ) -> None:
        """
        Loads intensity/texture measurement switch
        states from YAML structure.

        Args:
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            meas_dict (dict | None): Measurements dict from YAML, or None.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            None.
        """
        if not isinstance(meas_dict, dict):
            return

        for ch_key in range(4):
            ch_name_key = f'ch{ch_key}'
            reg_key = (obj_type, dot_key, ch_name_key) if dot_key else (obj_type, ch_name_key)

            if reg_key in self.measurement_registry:
                ch_meas_list = meas_dict.get(ch_name_key, [])
                if isinstance(ch_meas_list, list):
                    self.measurement_registry[reg_key]['intensity'].setChecked('intensity' in ch_meas_list)
                    self.measurement_registry[reg_key]['texture'].setChecked('texture' in ch_meas_list)

    def sync_dots_yaml_structure(self) -> None:
        """
        Re-synchronizes segmentation.dots,
        pipeline_toggles.dots, and
        additional_toggles.dots dictionaries in
        self.config_data with active dot blocks in
        GUI.

        Returns:
            None.
        """
        active_dot_keys = [b['dot_key'] for b in self.dot_blocks]

        # 1. Sync segmentation -> dots
        seg_dots = get_nested_val(data=self.config_data, key_path=('segmentation', 'dots'))
        if seg_dots is not None:
            stale_keys = [k for k in seg_dots if k not in active_dot_keys]
            for k in stale_keys:
                del seg_dots[k]

        # 2. Sync pipeline_toggles -> dots
        toggle_dots = get_nested_val(data=self.config_data, key_path=('pipeline_toggles', 'dots'))
        if toggle_dots is not None:
            stale_keys = [k for k in toggle_dots if k not in active_dot_keys]
            for k in stale_keys:
                del toggle_dots[k]

        # 2b. Dropping legacy filter_tables toggles (filters list now always applies)
        toggles_dict = get_nested_val(data=self.config_data, key_path=('pipeline_toggles',))
        if isinstance(toggles_dict, dict):
            for stage_dict in list(toggles_dict.values()) + list((toggle_dots or {}).values()):
                if isinstance(stage_dict, dict):
                    stage_dict.pop('filter_tables', None)

        # 3. Sync additional_toggles -> dots
        add_dots = get_nested_val(data=self.config_data, key_path=('additional_toggles', 'dots'))
        if add_dots is not None:
            stale_keys = [k for k in add_dots if k not in active_dot_keys]
            for k in stale_keys:
                del add_dots[k]

    def save_measurements_to_yaml(self,
                                  target_dict: dict,
                                  obj_type: str,
                                  dot_key: str | None = None
                                  ) -> None:
        """
        Saves measurements toggle states back into
        YAML structure preserving non-channel
        entries, and ensures non-GUI default
        measurements (embryos_crops and the selected
        nuclear mask link) exist for dots.

        Args:
            target_dict (dict): Object dict to update.
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            None.
        """
        meas_dict = target_dict.setdefault('measurements', {})

        # preserve existing non-channel keys (e.g. embryos_crops, nuclei mask link)
        preserved_non_channels = {k: v for k, v in meas_dict.items() if not (k.startswith('ch') and k[2:].isdigit())}
        meas_dict.clear()
        meas_dict.update(preserved_non_channels)

        # set initial default non-GUI measurements for dot objects if missing
        if dot_key:
            if 'embryos_crops' not in meas_dict:
                meas_dict['embryos_crops'] = ['id']

            # relinking the dot to the selected nuclear mask (keeping the measurements list of the previous link)
            block = next(b for b in self.dot_blocks if b['dot_key'] == dot_key)
            selected_mask = block['mask_state']['value']
            previous_mask_keys = [k for k in meas_dict if k in NUCLEI_MASK_NAMES]
            mask_measurements = meas_dict[previous_mask_keys[0]] if previous_mask_keys else ['id']
            for k in previous_mask_keys:
                del meas_dict[k]
            meas_dict[selected_mask] = mask_measurements

        # relinking nuclei to the selected nuclear mask
        elif obj_type == 'nuclei':
            for k in [k for k in meas_dict if k in NUCLEI_MASK_NAMES]:
                del meas_dict[k]
            meas_dict[self.nuc_mask_state['value']] = ['id']

        # getting dict items
        dict_items = self.measurement_registry.items()

        # iterating over measurement registry items
        for registry_item in dict_items:

            # getting current registry key/switches
            reg_key, switches = registry_item

            if dot_key:
                if len(reg_key) == 3 and reg_key[0] == obj_type and reg_key[1] == dot_key:
                    ch_key = reg_key[2]
                    active_list = []
                    if switches['intensity'].isChecked():
                        active_list.append('intensity')
                    if switches['texture'].isChecked():
                        active_list.append('texture')
                    if active_list:
                        meas_dict[ch_key] = active_list
            else:
                if len(reg_key) == 2 and reg_key[0] == obj_type:
                    ch_key = reg_key[1]
                    active_list = []
                    if switches['intensity'].isChecked():
                        active_list.append('intensity')
                    if switches['texture'].isChecked():
                        active_list.append('texture')
                    if active_list:
                        meas_dict[ch_key] = active_list

    def save_filters_to_yaml(self,
                             target_dict: dict,
                             obj_type: str,
                             dot_key: str | None = None
                             ) -> None:
        """
        Saves the object's filters back into YAML
        structure (after 'measurements') and drops
        the legacy fixed filter keys from older files.

        Args:
            target_dict (dict): Object dict to update.
            obj_type (str): Object type: 'embryos', 'nuclei', or 'dots'.
            dot_key (str | None): Dot key if obj_type is 'dots', None otherwise.

        Returns:
            None.
        """
        # writing filters
        target_dict['filters'] = self.get_filters_dict(obj_type=obj_type, dot_key=dot_key)

        # removing legacy fixed filter keys (min_size stays for embryos/nuclei since Cellpose uses it)
        legacy_keys = ['min_intensity', 'embryo_id', 'nucleus_id']
        if obj_type == 'dots':
            legacy_keys.append('min_size')
        for legacy_key in legacy_keys:
            target_dict.pop(legacy_key, None)

    def save_as_yaml(self) -> bool:
        """
        Prompts user to select a folder and
        filename to save settings as a new YAML
        file.

        Returns:
            bool: True if save succeeded, False otherwise.
        """
        if not self.config_data:
            self.lbl_status.setText('No configuration file loaded!')
            self.lbl_status.setStyleSheet("color: red;")
            return False

        # opening save as file dialog
        new_file_path, _ = QFileDialog.getSaveFileName(self, 'Save Settings As...', '', 'YAML Files (*.yaml *.yml)')

        # checking if user selected a file destination
        if new_file_path:
            self.file_path = new_file_path
            self.is_default_loaded = False
            self.lbl_file.setText(f'Settings File: {new_file_path}')
            return self.save_yaml()
        else:
            self.lbl_status.setText('Save operation cancelled by user.')
            self.lbl_status.setStyleSheet("color: #e67e22;")
            return False

    def save_yaml(self) -> bool:
        """
        Saves current GUI settings to active YAML
        file. Prompts for Save-As destination if
        defaults are loaded to prevent overwriting
        default package settings.

        Returns:
            bool: True if save succeeded, False otherwise.
        """
        # checking if configuration data is loaded
        if not self.config_data:
            # updating status label
            self.lbl_status.setText('No configuration file loaded!')
            self.lbl_status.setStyleSheet("color: red;")

            # returning false
            return False

        # checking if currently loaded file is default template
        is_default_file = (self.is_default_loaded or
                           (bool(self.file_path) and os.path.abspath(self.file_path) == os.path.abspath(
                               DEFAULT_SETTINGS_PATH)))

        if is_default_file or not self.file_path:

            # prompting user to choose destination file path
            new_file_path, _ = QFileDialog.getSaveFileName(self, 'Save Settings As...', '', 'YAML Files (*.yaml *.yml)')

            # aborting save if user cancelled file dialog
            if not new_file_path:
                self.lbl_status.setText('Save operation cancelled by user.')
                self.lbl_status.setStyleSheet("color: #e67e22;")
                return False

            # updating file path attributes
            self.file_path = new_file_path
            self.is_default_loaded = False
            self.lbl_file.setText(f'Settings File: {new_file_path}')

        # attempting save operation
        try:

            # synchronizing active dots in YAML memory structure
            self.sync_dots_yaml_structure()

            # updating base folder
            folder_text = self.lbl_folder_path.text()
            if folder_text != 'Not set':
                self.config_data['experiment']['base_folder'] = folder_text

            # updating cescale reference folder/dataset (set_nested_val, unlike base_folder's direct
            # dict assignment above, since an older loaded YAML may not have a "cescale" key yet) -
            # reference_folder is a fixed convention folder (under CET_HOME), not user-editable, so it's
            # always (re)written here rather than read from a UI widget
            set_nested_val(data=self.config_data,
                                key_path=('cescale', 'reference_folder'),
                                value=REFERENCE_DATA_FOLDER)
            set_nested_val(data=self.config_data,
                                key_path=('cescale', 'reference_dataset'),
                                value=self.cescale_dataset_var)
            # gene_expression_path is optional: empty entry is stored as None
            set_nested_val(data=self.config_data,
                                key_path=('cescale', 'gene_expression_path'),
                                value=self.cescale_gene_expression_entry.text().strip() or None)

            # updating cescale lineage tree plot settings (empty optional entries are stored as None)
            for tree_key, _, tree_default in self.cescale_tree_entries_spec:
                tree_text = self.cescale_tree_entries[tree_key].text().strip()
                if tree_key == 'tree_edge_width':
                    try:
                        tree_value = float(tree_text) if tree_text else None
                    except ValueError:
                        tree_value = None
                elif tree_key == 'tree_hover_cols':
                    tree_value = tree_text.split() or None
                elif tree_key == 'tree_edge_color_col':
                    tree_value = tree_text or None
                else:
                    tree_value = tree_text or tree_default
                set_nested_val(data=self.config_data,
                                    key_path=('cescale', tree_key),
                                    value=tree_value)

            # updating dots distance mode
            set_nested_val(data=self.config_data,
                                key_path=('additional_toggles', 'dots_distance_mode'),
                                value=self.dots_distance_mode_var)

            # updating image extension value
            set_nested_val(data=self.config_data,
                                key_path=('experiment', 'image_extension'),
                                value=self.image_ext_var)

            # getting switch registry dict items
            switch_dict_items = self.switch_registry.items()

            # updating switch values
            for switch_item in switch_dict_items:

                # getting current switch key path/switch
                key_path, switch = switch_item

                set_nested_val(data=self.config_data,
                                    key_path=key_path,
                                    value=bool(switch.isChecked()))

            # getting entry registry dict items
            entry_dict_items = self.entry_registry.items()

            # updating entry values
            for entry_item in entry_dict_items:

                # getting current entry key path/entry
                key_path, entry = entry_item

                entry_value = entry.text()

                # converting channel entries (blank means not set/unused channel)
                if key_path[0] == 'channels' and len(key_path) == 3:
                    entry_value = entry_value.strip() or None
                    if key_path[2] == 'wavelength' and entry_value is not None:
                        try:
                            entry_value = int(entry_value)
                        except ValueError:
                            raise ValueError(f'{key_path[1]} wavelength must be an integer, got "{entry_value}"')

                set_nested_val(data=self.config_data,
                                    key_path=key_path,
                                    value=entry_value)

            # saving measurement toggles to YAML configuration
            emb_dict = self.config_data.setdefault('segmentation', {}).setdefault('embryos', {})
            self.save_measurements_to_yaml(target_dict=emb_dict, obj_type='embryos')
            self.save_filters_to_yaml(target_dict=emb_dict, obj_type='embryos')

            nuc_dict = self.config_data.setdefault('segmentation', {}).setdefault('nuclei', {})
            self.save_measurements_to_yaml(target_dict=nuc_dict, obj_type='nuclei')
            self.save_filters_to_yaml(target_dict=nuc_dict, obj_type='nuclei')

            dots_dict = self.config_data.setdefault('segmentation', {}).setdefault('dots', {})
            for block in self.dot_blocks:
                dot_key = block['dot_key']
                single_dot_dict = dots_dict.setdefault(dot_key, {})
                self.save_measurements_to_yaml(target_dict=single_dot_dict, obj_type='dots', dot_key=dot_key)
                self.save_filters_to_yaml(target_dict=single_dot_dict, obj_type='dots', dot_key=dot_key)

            # writing config data to yaml file
            with open(self.file_path, 'w', encoding='utf-8') as f:
                self.yaml.dump(self.config_data, f)

            # updating status label
            self.lbl_status.setText('Settings saved successfully!')
            self.lbl_status.setStyleSheet("color: #2fa572;")

            # returning true
            return True

        # handling save exceptions
        except Exception as exception:

            # updating status label with error
            self.lbl_status.setText(f'Error saving file: {exception}')
            self.lbl_status.setStyleSheet("color: red;")

            # returning false
            return False

    def save_and_run(self) -> None:
        """
        Saves configuration and launches pipeline
        process, isolated in its own process group
        on Unix/Linux platforms so the background
        tree can be killed together.

        Returns:
            None.
        """
        # preventing concurrent runs against an already-running job (e.g. code update)
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            # returning None
            return None

        # saving settings
        saved_successfully = self.save_yaml()

        # checking if save succeeded
        if not saved_successfully:
            # returning None
            return None

        # resetting console text
        self.txt_console.clear()
        self.lbl_status.setText('Running pipeline...')
        self.lbl_status.setStyleSheet("color: #3B82F6;")

        # toggling button controls state
        self.btn_save_run.setEnabled(False)
        self.btn_update_codes.setEnabled(False)
        self.btn_enter.setEnabled(True)
        self.btn_abort.setEnabled(True)

        # tracking currently running job type for finish-handler messaging
        self.running_job_type = 'pipeline'

        # initializing virtual terminal buffer
        self.term_buffer = VirtualTerminalBuffer()

        # executing native QProcess
        python_executable = sys.executable
        cmd_args = ['-u', '-m', 'cet.pipelines.pipeline', self.file_path]

        # assembling header string
        header_str = f'Executing: {python_executable} {" ".join(cmd_args)}\n'
        header_str += ('_' * 50) + '\n'

        # pushing header directly
        for char in header_str:
            completed_lines = self.term_buffer.write_char(char=char)
            for completed in completed_lines:
                self.commit_line(text=completed)
        self.update_active_bottom_line(text=self.term_buffer.get_active_line())

        # running subprocess asynchronously
        self.running_process = QProcess(self)
        self.running_process.readyReadStandardOutput.connect(self.process_stdout)
        self.running_process.readyReadStandardError.connect(self.process_stderr)
        self.running_process.finished.connect(self.process_finished)

        # creating new process group on Unix/Linux to ensure background tree can be killed together
        if hasattr(os, 'setsid'):
            try:
                params = QProcess.UnixProcessParameters()
                params.flags = params.flags | QProcess.UnixProcessFlag.CreateNewSession
                self.running_process.setUnixProcessParameters(params)
            except (AttributeError, TypeError, ImportError):
                pass

        self.running_process.start(python_executable, cmd_args)

    def run_update_codes(self) -> None:
        """
        Updates the cet package from the most recent version in the
        updates folder (followed by pip install -e .), via the
        "cet.setup.update" module, streaming output into the same
        console/terminal buffer used by pipeline runs.

        Returns:
            None.
        """
        # preventing concurrent runs against an already-running job (e.g. pipeline)
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            # returning None
            return None

        # resetting console text
        self.txt_console.clear()
        self.lbl_status.setText('Updating package...')
        self.lbl_status.setStyleSheet("color: #3B82F6;")

        # toggling button controls state
        self.btn_save_run.setEnabled(False)
        self.btn_update_codes.setEnabled(False)
        self.btn_enter.setEnabled(False)
        self.btn_abort.setEnabled(True)

        # tracking currently running job type for finish-handler messaging
        self.running_job_type = 'update_codes'

        # initializing virtual terminal buffer
        self.term_buffer = VirtualTerminalBuffer()

        # executing native QProcess from repository root (where pyproject.toml lives)
        python_executable = sys.executable
        cmd_args = ['-u', '-m', 'cet.setup.update']
        repo_root = Path(__file__).resolve().parents[3]

        # assembling header string
        header_str = f'Executing: {python_executable} {" ".join(cmd_args)}\n'
        header_str += ('_' * 50) + '\n'

        # pushing header directly
        for char in header_str:
            completed_lines = self.term_buffer.write_char(char=char)
            for completed in completed_lines:
                self.commit_line(text=completed)
        self.update_active_bottom_line(text=self.term_buffer.get_active_line())

        # running subprocess asynchronously
        self.running_process = QProcess(self)
        self.running_process.setWorkingDirectory(str(repo_root))
        self.running_process.readyReadStandardOutput.connect(self.process_stdout)
        self.running_process.readyReadStandardError.connect(self.process_stderr)
        self.running_process.finished.connect(self.process_finished)
        self.running_process.start(python_executable, cmd_args)

    def launch_napari_viewer(self) -> None:
        """
        Launches the napari mask/image viewer
        (cet-napari) as an independent, detached
        background process, decoupled from the
        pipeline run/Abort/Send Enter state machine.

        Returns:
            None.
        """
        # executing napari loader as a detached process (fire-and-forget)
        python_executable = sys.executable
        cmd_args = ['-u', '-m', 'cet.gui.viewer.napari_loader']
        started = QProcess.startDetached(python_executable, cmd_args)

        # updating status label on launch failure
        if not started:
            self.lbl_status.setText('Failed to launch napari viewer')
            self.lbl_status.setStyleSheet("color: #c0392b;")

    def send_enter_to_process(self) -> None:
        """
        Sends an Enter signal (newline) to standard
        input of running subprocess and forces a
        line commit in the virtual terminal buffer.

        Returns:
            None.
        """
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            try:
                # 1. Send newline to process input
                self.running_process.write(b'\n')

                # 2. Echo the Enter press to the virtual terminal buffer
                completed_lines = self.term_buffer.write_char(char='\n')
                for completed in completed_lines:
                    self.commit_line(text=completed)

                # 3. Clear active bottom line display
                self.update_active_bottom_line(text='')
            except Exception as e:
                self.commit_line(text=f'[Failed to send Enter signal: {e}]\n')

    def abort_execution(self) -> None:
        """
        Kills currently executing pipeline
        subprocess without terminating the parent
        GUI application.

        Returns:
            None.
        """
        # checking if process exists and is running
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            # terminating standard QProcess cleanly
            self.running_process.kill()

            # updating status label
            self.lbl_status.setText('Execution aborted by user!')
            self.lbl_status.setStyleSheet("color: #e67e22;")

            # committing log message
            self.commit_line(text='[Execution killed by user]\n')

        # resetting controls
        self.btn_save_run.setEnabled(True)
        self.btn_update_codes.setEnabled(True)
        self.btn_enter.setEnabled(False)
        self.btn_abort.setEnabled(False)

    def process_stdout(self) -> None:
        """
        Reads raw bytes from process stdout,
        updates virtual terminal, and renders active
        line to GUI console.

        Returns:
            None.
        """
        active_changed = False
        data = self.running_process.readAllStandardOutput()

        try:
            # decoding bytes to string
            text = bytes(data).decode('utf-8')

            # feeding character by character to term buffer
            for char in text:
                completed_lines = self.term_buffer.write_char(char=char)
                for completed in completed_lines:
                    self.commit_line(text=completed)
                active_changed = True
        except UnicodeDecodeError:
            pass

        # checking if active line changed
        if active_changed:
            # getting active line from virtual buffer
            active_line = self.term_buffer.get_active_line()

            # updating GUI console active line
            self.update_active_bottom_line(text=active_line)

    def process_stderr(self) -> None:
        """
        Delegates to process_stdout so stderr
        output goes through the same virtual-terminal
        rendering path as stdout.

        Returns:
            None.
        """
        self.process_stdout()

    def process_finished(self,
                         exit_code: int,
                         exit_status: QProcess.ExitStatus
                         ) -> None:
        """
        Handles post-execution cleanup natively
        upon QProcess finish.

        Args:
            exit_code (int): Process exit code.
            exit_status (QProcess.ExitStatus): Exit status (normal or crash).

        Returns:
            None.
        """
        # resetting button states
        self.btn_save_run.setEnabled(True)
        self.btn_update_codes.setEnabled(True)
        self.btn_enter.setEnabled(False)
        self.btn_abort.setEnabled(False)

        # picking job-appropriate label for status/console messages
        finished_job_type = self.running_job_type
        job_label = 'Package update' if finished_job_type == 'update_codes' else 'Pipeline'

        if exit_status == QProcess.ExitStatus.CrashExit:
            self.lbl_status.setText(f'{job_label} process aborted or crashed.')
            self.lbl_status.setStyleSheet("color: #e67e22;")
            self.commit_line(text='\n[Process exited unexpectedly]\n')
        elif exit_code == 0:
            self.lbl_status.setText(f'{job_label} finished successfully!')
            self.lbl_status.setStyleSheet("color: #2fa572;")
            self.commit_line(text='\n[Process completed successfully]\n')
        else:
            self.lbl_status.setText(f'{job_label} failed (code {exit_code})')
            self.lbl_status.setStyleSheet("color: red;")
            self.commit_line(text=f'\n[Process exited with error code {exit_code}]\n')

        # clearing process reference
        self.running_process = None
        self.running_job_type = None

        # offering to restart GUI so any GUI-side code changes actually take effect
        if finished_job_type == 'update_codes' and exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit:
            self.refresh_version_label()
            self.prompt_restart_after_update()

    def refresh_version_label(self) -> None:
        """
        Sets version label text to the same
        string cet-version prints, e.g.
        'cet 0.0.1.dev0 (CPU)'.

        Returns:
            None.
        """
        cet_version = get_cet_version()
        cet_variant = get_cet_variant()
        self.lbl_version.setText(f'Version: cet {cet_version} ({cet_variant})')

    def prompt_restart_after_update(self) -> None:
        """
        Asks user whether to restart GUI immediately
        after a successful code update, since a
        running process keeps old GUI code loaded
        in memory even after reinstall.

        Returns:
            None.
        """
        reply = QMessageBox.question(
            self,
            'Update Complete',
            'Package updated successfully.\n\nRestart the GUI now to load the new version?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # launching fresh, fully independent GUI instance first (detached process
            # survives on its own regardless of what happens to this one afterward)
            python_executable = sys.executable
            cmd_args = ['-u', '-m', 'cet.gui.app']
            QProcess.startDetached(python_executable, cmd_args)

            # hard-terminating current (stale) process outright so its owning terminal is
            # freed immediately (no pipeline can be running at this point, since the
            # Update Codes button is disabled while one is - see save_and_run/run_update_codes)
            os._exit(0)

    def commit_line(self,
                    text: str
                    ) -> None:
        """
        Appends a permanent finalized line into
        console text box.

        Args:
            text (str): Text line to append.

        Returns:
            None.
        """
        # replacing active bottom line securely
        cursor = self.txt_console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()

        # inserting text
        cursor.insertText(text)

        # scrolling to end
        self.txt_console.setTextCursor(cursor)
        self.txt_console.ensureCursorVisible()

    def update_active_bottom_line(self,
                                  text: str
                                  ) -> None:
        """
        Replaces active bottom line in text box
        with virtual terminal state.

        Args:
            text (str): Text to display on active line.

        Returns:
            None.
        """
        # deleting active line
        cursor = self.txt_console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()

        # inserting updated active line
        cursor.insertText(text)

        # scrolling to end
        self.txt_console.setTextCursor(cursor)
        self.txt_console.ensureCursorVisible()

######################################################################
# end of current module
