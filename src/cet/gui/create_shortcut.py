# create shortcut module

# Code destined to creating
# pipeline gui shortcut.

######################################################################
# imports

from sys import prefix
from sys import platform
from os.path import join
from os.path import dirname
from cet.constants import CET_PATH
from pyshortcuts import get_desktop
from cet.constants import ICONS_PATH
from pyshortcuts import make_shortcut

######################################################################
# defining auxiliary functions


def create_desktop_shortcut():
    """
    Creates a desktop shortcut pointing
    explicitly to the conda environment.

    Returns:
        None.
    """
    # getting current platform
    is_windows = platform.startswith('win')

    # defining paths
    linux_bin_folder = 'bin'
    windows_bin_folder = 'Scripts'
    bin_folder = (windows_bin_folder if is_windows else linux_bin_folder)
    executable_path = join(prefix, bin_folder, 'cet-gui')
    icon_path = str(ICONS_PATH.joinpath('cet.png'))
    base_folder = dirname(dirname(str(CET_PATH)))
    desktop_path = get_desktop()
    working_folder = (base_folder if is_windows else None)

    # checking whether current system is windows
    if is_windows:

        # updating icon path (Windows requires .ico file)
        icon_path = icon_path.replace('.png', '.ico')

    # creating shortcut
    make_shortcut(script=executable_path,
                  name='Elegant-Toolkit',
                  description='CeT Pipeline',
                  working_dir=working_folder,
                  folder=desktop_path,
                  icon=icon_path,
                  terminal=False)

    # printing execution message
    f_string = f'Desktop shortcut created targeting Conda Env: {prefix}'
    print(f_string)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # running create desktop shortcut function
    create_desktop_shortcut()

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module