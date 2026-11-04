# list commands module

print('initializing...')  # noqa

# Code destined to listing all installed
# "cet-*" commands (console scripts), grouped
# by category, with a short description each.
# Stdlib-only, so it runs instantly (no torch,
# no cet imports).

######################################################################
# imports

print('importing required libraries...')  # noqa
from importlib.metadata import entry_points
print('all required libraries successfully imported.')  # noqa

######################################################################
# defining global variables

# prefix shared by all of this package's console scripts
COMMAND_PREFIX = 'cet-'

# category shown for installed commands missing from COMMANDS
OTHER_CATEGORY = 'Other'

# categories, in display order
CATEGORY_ORDER = ['GUI',
                  'Diagnostics',
                  'Setup',
                  OTHER_CATEGORY]

# command descriptions (command name: (category, description)) -
# kept by hand, add a row here when registering a new entry point
# in pyproject.toml's [project.scripts]
COMMANDS = {'cet-gui': ('GUI', 'launches the pipeline gui'),
            'cet-create_shortcut': ('GUI', 'creates a desktop shortcut for the pipeline gui'),
            'cet-napari': ('GUI', 'launches a napari viewer with image/mask loading buttons'),
            'cet-check_imports': ('Diagnostics', 'checks all imports done in the project tree'),
            'cet-check_gpu': ('Diagnostics', 'checks gpu availability'),
            'cet-version': ('Diagnostics', 'reports installed package version and cpu/gpu extra'),
            'cet-check_java': ('Diagnostics', 'checks java (jdk/jvm) home'),
            'cet-test_gpu': ('Diagnostics', 'tests gpu'),
            'cet-options': ('Diagnostics', 'lists all cet-* commands (this command)'),
            'cet-download_cp_models': ('Setup', 'downloads cellpose model weights'),
            'cet-download_jdk': ('Setup', 'installs a jdk into a conda env'),
            'cet-download_loci_jar': ('Setup', 'downloads bio-formats loci_tools.jar'),
            'cet-download_pycudadecon': ('Setup', 'installs pycudadecon into a conda env'),
            'cet-update': ('Setup', 'updates this package from a versioned local update folder'),
            'cet-build_update_folder': ('Setup', 'builds a new versioned, full snapshot of the repository')}

######################################################################
# defining auxiliary functions


def get_installed_commands() -> dict:
    """
    Returns all installed console scripts
    starting with the "cet-" prefix.

    Returns:
        dict: A dictionary mapping command names to their "module:function" targets.
    """
    # initializing installed commands dict
    installed_commands = {}

    # getting console scripts entry points
    console_scripts = entry_points(group='console_scripts')

    # iterating over console scripts
    for console_script in console_scripts:

        # getting current command info
        command_name = console_script.name
        command_target = console_script.value

        # skipping non cet commands
        if not command_name.startswith(COMMAND_PREFIX):

            # skipping
            continue

        # assembling current dict
        current_dict = {command_name: command_target}

        # updating installed commands dict
        installed_commands.update(current_dict)

    # returning installed commands
    return installed_commands


def group_commands(installed_commands: dict) -> dict:
    """
    Given installed commands, groups
    them by category (keeping the display
    order), each as a (name, description)
    list sorted by name.

    Args:
        installed_commands (dict): A dictionary mapping command names to their "module:function" targets.

    Returns:
        dict: A dictionary mapping categories to lists of (name, description) tuples.
    """
    # initializing grouped commands dict (in display order)
    grouped_commands = {}

    # iterating over categories
    for category in CATEGORY_ORDER:

        # assembling current dict
        current_dict = {category: []}

        # updating grouped commands dict
        grouped_commands.update(current_dict)

    # iterating over installed commands (sorted by name)
    for command_name in sorted(installed_commands):

        # getting current command info
        command_target = installed_commands[command_name]
        command_info = COMMANDS.get(command_name)

        # checking if command is missing from commands dict
        if command_info is None:

            # using other category and module target as description
            category = OTHER_CATEGORY
            description = command_target

        # if command is described
        else:

            # unpacking command info
            category, description = command_info

        # adding command to its category
        grouped_commands[category].append((command_name, description))

    # returning grouped commands
    return grouped_commands


def print_commands(grouped_commands: dict) -> None:
    """
    Given grouped commands, prints them
    one category at a time, with aligned
    descriptions.

    Args:
        grouped_commands (dict): A dictionary mapping categories to lists of (name, description) tuples.

    Returns:
        None.
    """
    # getting longest command name
    all_names = [name for commands in grouped_commands.values() for name, _ in commands]
    name_width = max(len(name) for name in all_names)

    # getting dict items
    dict_items = grouped_commands.items()

    # iterating over categories
    for category_item in dict_items:

        # getting current category/commands
        category, commands = category_item

        # skipping empty categories
        if not commands:

            # skipping
            continue

        # printing category heading
        print(f'\n{category}')

        # iterating over category commands
        for command_name, description in commands:

            # printing current command
            print(f'  {command_name.ljust(name_width)}  {description}')

    # printing footer
    print('\nrun "<command> -h" to see a command\'s options.')


def list_commands() -> None:
    """
    Lists all installed "cet-*"
    commands, grouped by category.

    Returns:
        None.
    """
    # getting installed commands
    installed_commands = get_installed_commands()

    # checking if no commands were found
    if not installed_commands:

        # printing message
        print('no "cet-*" commands found (is the package installed? try "pip install -e .").')

        # returning
        return None

    # grouping commands
    grouped_commands = group_commands(installed_commands=installed_commands)

    # printing commands
    print_commands(grouped_commands=grouped_commands)

######################################################################
# defining main function


def main():
    """
    Runs main code.
    """
    # running list commands function
    list_commands()

######################################################################
# running main function


if __name__ == '__main__':
    main()

######################################################################
# end of current module
