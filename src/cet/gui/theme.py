# theme module

# Code destined to defining
# PipelineGUI's dark-mode
# stylesheet constants.

######################################################################
# defining global stylesheet

# Console output colors
CONSOLE_BG = '#000000'
CONSOLE_TEXT = '#ffffff'

# appearance stylesheet
DARK_STYLESHEET = f'''
QWidget {{
    background-color: #242424;
    color: #ffffff;
}}
QFrame {{
    border: none;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}
QLineEdit {{
    background-color: #343638;
    border: 1px solid #565b5e;
    border-radius: 4px;
    padding: 3px 6px;
    color: #ffffff;
}}
QPushButton {{
    background-color: #1f538d;
    border-radius: 4px;
    padding: 5px 10px;
    color: #ffffff;
}}
QPushButton:hover {{
    background-color: #14375e;
}}
QPushButton:disabled {{
    background-color: #565b5e;
    color: #a0a0a0;
}}

/* Pill Toggle Checkbox Layout */
QCheckBox {{
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 38px;
    height: 20px;
}}

/* High contrast Console Execution Output Text */
QTextEdit {{
    background-color: {CONSOLE_BG};
    border: 1px solid #565b5e;
    border-radius: 4px;
    color: {CONSOLE_TEXT};
    selection-background-color: #1f538d;
    selection-color: #ffffff;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #565b5e;
    background-color: transparent;
}}
QRadioButton::indicator:checked {{
    background-color: #1f538d;
    border: 2px solid #1f538d;
}}

/* Hover tooltips */
QToolTip {{
    background-color: #1f2223;
    color: #ffffff;
    border: 1px solid #565b5e;
    padding: 4px 6px;
    border-radius: 3px;
}}
'''

######################################################################
# end of current module
