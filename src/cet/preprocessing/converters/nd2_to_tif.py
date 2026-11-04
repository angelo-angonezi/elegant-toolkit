# nd2 to tif module

print('initializing...')  # noqa

# Code destined to converting
# nd2 files fields stacks into
# tif files.

######################################################################
# imports

print('importing required libraries...')  # noqa
from numpy import array
from os.path import join
from tifffile import imwrite
from nd2reader import ND2Reader
from argparse import ArgumentParser
from cet.io.files import get_skip_file_bool
from cet.io.files import save_metadata_file
from cet.io.files import get_files_in_folder
from cet.io.formatting import get_number_string
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.preprocessing.converters.metadata import to_serializable
print('all required libraries successfully imported.')  # noqa

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
    description = "nd2 to tif module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # adding arguments to parser

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing input files [.nd2]')

    # output folder param
    parser.add_argument('-o', '--output-folder',
                        dest='output_folder',
                        type=str,
                        required=True,
                        help='defines output folder (folder that will contain converted images [.tif])')

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

        # image
        self.images_num = 0
        self.current_image = 0

        # field
        self.fields_num = 0
        self.current_field = 0

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
        if not self.totals_updated.is_set():

            # updating progress string based on attributes
            progress_string += f'calculating totals...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | images: {self.images_num}'
            progress_string += f' | fields: {self.fields_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'converting files...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_image}/{self.images_num}'
            progress_string += f' | field: {self.current_field}/{self.fields_num}'
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

        # getting images
        images = get_files_in_folder(input_folder=input_folder,
                                     extension='.nd2')

        # iterating over files
        for image in images:

            # updating progress tracker attributes
            self.images_num += 1

            # getting current image path
            file_path = join(input_folder,
                             image)

            try:

                # reading current file
                with ND2Reader(file_path) as open_file:

                    # getting file metadata
                    file_metadata = open_file.metadata

                    # getting fields range
                    fields_range = file_metadata['fields_of_view']

                    # iterating over fields range
                    for _ in fields_range:

                        # updating progress tracker attributes
                        self.fields_num += 1
                        self.iterations_num += 1

            except Exception as e:

                # printing error message
                e_string = f'Unable to load file "{file_path}".\n'
                e_string += f'Error: {e}\n'
                e_string += f'Skipping...'
                print(e_string)
                continue

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.images_num}'
        totals_string += f' | fields: {self.fields_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def extract_metadata(input_path: str) -> dict:
    """
    Given a path to a nd2 file, returns all its metadata
    as a json-serializable dict. The dict contains:
        - "parsed_metadata": nd2reader's curated metadata
          (dimensions, channels, pixel size, z levels, etc.).
        - "raw_metadata": every raw metadata section decoded by nd2reader
          (image attributes, calibration, text info, events, experiment
          loops, per-frame stage positions, camera/grabber settings, etc.).

    Args:
        input_path (str): The path to the nd2 file to extract metadata from.

    Returns:
        dict: The extracted metadata.
    """
    # reading current file
    with ND2Reader(input_path) as open_file:

        # getting curated file metadata
        parsed_metadata = to_serializable(open_file.metadata)

        # getting all raw metadata sections
        raw_metadata = to_serializable(vars(open_file.parser._raw_metadata))

    # building metadata dict
    metadata = {'parsed_metadata': parsed_metadata,
                'raw_metadata': raw_metadata}

    # returning extracted metadata
    return metadata


def get_iter_ax(open_file: ND2Reader) -> str:
    """
    Given an open/parsed nd2 file,
    returns iter ax based on the
    number of fields of view.

    Args:
        open_file (ND2Reader): The open/parsed nd2 file.

    Returns:
        str: The iteration axis ("t" for a single field of view, "v" for multiple).
    """
    # defining placeholder value for iter ax
    iter_ax = 't'  # used if file contains single field of view

    # getting file axes
    axes = open_file.axes

    # getting file is multi field bool
    file_is_multi_field = ('v' in axes)

    # checking if file is multi field
    if file_is_multi_field:

        # updating iter ax
        iter_ax = 'v'  # used if file contains multiple fields of view

    # returning iter ax
    return iter_ax


def save_fields(file_name: str,
                open_file: ND2Reader,
                output_folder: str,
                overwrite_output: bool,
                progress_tracker: ModuleProgressTracker
                ) -> None:
    """
    Given an open/parsed nd2 file,
    iterates over fields of view and
    saves them in given output folder.

    Args:
        file_name (str): The name of the file being processed.
        open_file (ND2Reader): The open/parsed nd2 file.
        output_folder (str): The path to the folder to save fields to.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting iteration ax
    iter_ax = get_iter_ax(open_file=open_file)

    # updating iteration ax
    open_file.iter_axes = iter_ax

    # getting file metadata
    file_metadata = open_file.metadata

    # getting fields range
    fields_range = file_metadata['fields_of_view']

    # getting fields list
    fields_list = [f for f in fields_range]

    # getting fields num
    fields_num = len(fields_list)

    # updating progress tracker attributes
    progress_tracker.fields_num = fields_num

    # resetting progress tracker attributes
    progress_tracker.current_field = 0

    # iterating over fields in file
    for field_index in fields_range:  # directly iterating over open_file takes a long time even if the file already exists!

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1
        progress_tracker.current_field += 1

        # getting file is multi field bool
        file_is_multi_field = (iter_ax == 'v')

        # defining placeholder value for current save name
        current_save_name = file_name.replace('.nd2', '.tif')

        # checking if file is multi field
        if file_is_multi_field:

            # getting current field index/str
            field_index_str = get_number_string(num=progress_tracker.current_field,
                                                digits=2)
            field_str = f'field{field_index_str}'
            old_ext = '.tif'
            new_ext = f'_{field_str}.tif'

            # updating current save name
            current_save_name = current_save_name.replace(old_ext, new_ext)

        # defining current save path
        current_save_path = join(output_folder,
                                 current_save_name)

        # getting skip file bool
        skip_file = get_skip_file_bool(file_path=current_save_path,
                                       overwrite_output=overwrite_output)

        # checking whether to skip current file
        if skip_file:

            # sleeping
            progress_tracker.wait(0.05)

            # updating progress tracker attributes
            progress_tracker.skipped_iterations += 1

            # skipping to next file
            continue

        # getting current field
        field = open_file[field_index]

        # converting pim object to numpy array
        field = array(field)

        # converting image to 16bit
        field = field.astype('uint16')  # TODO: check if this is an issue when working with deconvolved images

        # saving image
        imwrite(current_save_path,
                field)


def split_file(file_name: str,
               file_path: str,
               output_folder: str,
               overwrite_output: bool,
               progress_tracker: ModuleProgressTracker
               ) -> None:
    """
    Given a path to a nd2 file,
    splits experiment into fields,
    saving each field as a tif stack.

    Args:
        file_name (str): The name of the file being processed.
        file_path (str): The path to the nd2 file to split.
        output_folder (str): The path to the folder to save fields to.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # reading current file
    with ND2Reader(file_path) as open_file:

        # bundling axes (sets axes order)
        open_file.bundle_axes = 'zyxc'

        # saving current file fields
        save_fields(file_name=file_name,
                    open_file=open_file,
                    output_folder=output_folder,
                    overwrite_output=overwrite_output,
                    progress_tracker=progress_tracker)


def nd2_to_tif(input_folder: str,
               output_folder: str,
               overwrite_output: bool,
               progress_tracker: ModuleProgressTracker
               ) -> None:
    """
    Given a path to a folder containing
    nd2 files, splits each experiment
    into fields, saving each field as a
    tif stack.

    Args:
        input_folder (str): The path to the folder containing nd2 files to convert.
        output_folder (str): The path to the folder to save converted tif files to.
        overwrite_output (bool): Whether to overwrite existing files in output folder.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting files in input folder
    files = get_files_in_folder(input_folder=input_folder,
                                extension='.nd2')

    # checking whether there are files to extract metadata from (files in folder are
    # assumed to share virtually identical metadata - only the first one is used)
    if files:

        # getting metadata file path
        metadata_path = join(output_folder,
                             'metadata.json')

        # getting skip metadata file bool
        skip_metadata = get_skip_file_bool(file_path=metadata_path,
                                           overwrite_output=overwrite_output)

        # checking whether to (re-)extract metadata
        if not skip_metadata:

            # getting first file input path
            first_file_path = join(input_folder,
                                   files[0])

            # extracting first file metadata
            metadata = extract_metadata(input_path=first_file_path)

            # saving extracted metadata
            save_metadata_file(output_folder=output_folder,
                               metadata=metadata)

    # iterating over files in input folder
    for file_name in files:

        # updating progress tracker attributes
        progress_tracker.current_image += 1

        # getting current file input path
        input_path = join(input_folder,
                          file_name)

        # trying to convert file
        try:

            # splitting fields for current file
            split_file(file_name=file_name,
                       file_path=input_path,
                       output_folder=output_folder,
                       overwrite_output=overwrite_output,
                       progress_tracker=progress_tracker)

        # handling exception
        except Exception as e:

            # printing error message
            e_string = f'Unable to load file "{input_path}".\n'
            e_string += f'Error: {e}\n'
            e_string += f'Skipping...'
            print(e_string)

            # skipping to next file
            continue


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

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running nd2_to_tif function
    nd2_to_tif(input_folder=input_folder,
               output_folder=output_folder,
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
