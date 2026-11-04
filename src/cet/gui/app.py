# app gui module

# Code destined to running main
# pipeline gui loop.

######################################################################
# imports

import sys
from PyQt6.QtWidgets import QApplication
from cet.gui.PipelineGUI import PipelineGUI

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # initializing qt application instance
    qt_app = QApplication(sys.argv)

    # initializing gui window instance
    gui_window = PipelineGUI()
    gui_window.show()

    # starting main event loop
    sys.exit(qt_app.exec())

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module