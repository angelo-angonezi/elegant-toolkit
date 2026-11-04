# generate pseudoembryos df module

print('initializing...')  # noqa

# Code destined to generating
# pseudoembryos df (used in pipeline
# when map nuclei to images is true).

######################################################################
# imports

print('importing required libraries...')  # noqa
from pandas import DataFrame
from argparse import ArgumentParser
from cet.io.dataframes import save_df
from cet.io.files import get_crop_name
from cet.io.files import get_skip_file_bool
from cet.measurements.labels import get_uid
from cet.io.files import get_files_in_folder
from cet.io.formatting import get_digits_num
from cet.progress_tracker.ProgressTracker import ProgressTracker
from cet.dataframes.df_ops import filter_pandas_performance_warnings
print('all required libraries successfully imported.')  # noqa

# filtering Pandas Performance Warnings
filter_pandas_performance_warnings()

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
    description = "generate pseudoembryos df module"

    # creating a parser instance
    parser = ArgumentParser(description=description)

    # input folder param
    parser.add_argument('-i', '--input-folder',
                        dest='input_folder',
                        type=str,
                        required=True,
                        help='defines path to folder containing input images [.tif]')

    # output path param
    parser.add_argument('-o', '--output-path',
                        dest='output_path',
                        type=str,
                        required=True,
                        help='defines path to output file [.csv]')

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
            progress_string += f' | images: {self.iterations_num}'
            progress_string += f' | iterations: {self.iterations_num}'
            progress_string += f' | elapsed time: {self.elapsed_time_str}'

        # if total iterations already obtained
        else:

            # updating progress string based on attributes
            progress_string += f'generating dfs...'
            progress_string += f' {self.wheel_symbol}'
            progress_string += f' | image: {self.current_iteration}/{self.iterations_num}'
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
                                     extension='.tif')

        # iterating over files
        for _ in images:

            # updating progress tracker attributes
            self.iterations_num += 1

        # updating totals string
        totals_string = f'totals...'
        totals_string += f' | images: {self.iterations_num}'
        totals_string += f' | iterations: {self.iterations_num}'
        self.totals_string = totals_string

        # signaling totals updated
        self.signal_totals_updated()

######################################################################
# defining auxiliary functions


def get_pseudoembryo_dict(image_name: str,
                          image_index: int,
                          object_digits_num: int
                          ) -> dict:
    """
    Given a path to an image, returns
    its respective pseudoembryo dict.

    Args:
        image_name (str): The name of the image being processed.
        image_index (int): The current image index.
        object_digits_num (int): The number of digits to zero-pad the object id with.

    Returns:
        dict: The image's pseudoembryo dict.
    """
    # defining description
    description = 'emb'

    # defining constant object id (single "pseudoembryo" per image)
    object_id = 1

    # getting object uid
    object_uid = get_uid(image_index=image_index,
                         description=description,
                         object_id=object_id)

    # getting crop name
    crop_name = get_crop_name(image_name=image_name,
                              description=description,
                              object_id=object_id,
                              digits=object_digits_num)

    # defining placeholder value for image dict
    image_dict = {'image_name': image_name,
                  'image_index': image_index,
                  'description': description,
                  'object_id': object_id,
                  'uid': object_uid,
                  'crop_name': crop_name}

    # returning image dict
    return image_dict


def generate_pseudoembryos_df(input_folder: str,
                              output_path: str,
                              overwrite_output: bool,
                              progress_tracker: ModuleProgressTracker
                              ) -> None:
    """
    Given a path to a folder containing
    images, generates a pseudoembryos
    df.

    Args:
        input_folder (str): The path to the folder containing images.
        output_path (str): The path to save the pseudoembryos df to.
        overwrite_output (bool): Whether to overwrite an existing output file.
        progress_tracker (ModuleProgressTracker): The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting skip file bool
    skip_file = get_skip_file_bool(file_path=output_path,
                                   overwrite_output=overwrite_output)

    # checking whether to skip current file
    if skip_file:

        # sleeping
        progress_tracker.wait(0.05)

        # updating progress tracker attributes
        progress_tracker.current_iteration += progress_tracker.iterations_num
        progress_tracker.skipped_iterations += progress_tracker.iterations_num

        # skipping
        return None

    # defining placeholder value for dicts list
    dicts_list = []

    # getting images in input folder
    images = get_files_in_folder(input_folder=input_folder,
                                 extension='.tif')

    # getting object count
    object_digits_num = get_digits_num(items_list=images)

    # iterating over images in input folder
    for image_name in images:

        # updating progress tracker attributes
        progress_tracker.current_iteration += 1

        # getting current image index
        image_index = progress_tracker.current_iteration

        # getting current image dict
        current_image_dict = get_pseudoembryo_dict(image_name=image_name,
                                                   image_index=image_index,
                                                   object_digits_num=object_digits_num)

        # appending current image df to dicts list
        dicts_list.append(current_image_dict)

    # assembling df from dicts list
    final_df = DataFrame(dicts_list)

    # saving df
    save_df(save_path=output_path,
            df=final_df)


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

    # getting output path
    output_path = args_dict['output_path']

    # getting overwrite output
    overwrite_output = args_dict['overwrite_output']

    # running generate_pseudoembryos_df function
    generate_pseudoembryos_df(input_folder=input_folder,
                              output_path=output_path,
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
