# files io module

# Code destined to storing files
# input/output related functions.

######################################################################
# imports

from os import walk
from copy import copy
from json import dump
from os import listdir
from os import makedirs
from os.path import join
from os.path import split
from pandas import Series
from shutil import rmtree
from os.path import exists
from os.path import getsize
from natsort import natsorted
from inspect import currentframe
from cet.io.formatting import get_size_str
from cet.io.formatting import get_number_string

######################################################################
# defining auxiliary functions


def get_files_in_folder(input_folder: str,
                        extension: str = ''
                        ) -> list:
    """
    Given a path to a folder, returns a list
    containing all files in folder that match
    given extension.

    Args:
        input_folder (str): Path to the folder to scan.
        extension (str, optional): File extension filter (e.g., '.txt'). Defaults to '' (all files).

    Returns:
        list: A naturally sorted list of filenames matching the given extension.
    """
    # getting all files in folder
    all_files = listdir(input_folder)

    # getting specific files
    valid_files = [file                          # getting file
                   for file                      # iterating over files
                   in all_files                  # in input folder
                   if file.endswith(extension)]  # only if file matches given extension

    # sorting list
    valid_files = natsorted(valid_files)

    # returning list
    return valid_files


def get_input_folder(row_data: Series,
                     images_folder: str,
                     augmentations_folder: str | None = None
                     ) -> str:
    """
    Given a splits df row data, returns input
    folder, based on presence of augmentations.

    Args:
        row_data (Series): A pandas Series row containing information about whether it is an augmentation.
        images_folder (str): Path to the images folder.
        augmentations_folder (str | None, optional): Path to the augmentations folder, or None if augmentations are not available. Defaults to None.

    Returns:
        str: The path to either the images folder or augmentations folder based on row data.
    """
    # defining placeholder value for input folder
    input_folder = copy(images_folder)

    # checking if augmentations folder is not none
    if augmentations_folder:

        # getting current row info
        row_is_augmentation = row_data['augmentation']

        # checking if current row is augmentation
        if row_is_augmentation:

            # updating input folder
            input_folder = augmentations_folder

    # returning input folder
    return input_folder


def get_crop_name(image_name: str,
                  description: str,
                  object_id: int,
                  digits: int
                  ) -> str:
    """
    Given an object image name, and respective
    id, returns crop name.

    Args:
        image_name (str): The original image filename.
        description (str): The description prefix for the object (e.g., 'embryo', 'nucleus').
        object_id (int): The ID number of the object.
        digits (int): The number of digits to zero-pad the object ID to.

    Returns:
        str: The crop name, either the original image name if it already contains the object string, or a new name with the object information inserted before the extension.
    """
    # getting object id string
    object_id_str = get_number_string(num=object_id,
                                      digits=digits)

    # getting current object string
    object_str = f'{description}{object_id_str}'

    # getting object string in image name bool
    object_str_in_image_name = (object_str in image_name)

    # checking if object string is in image name (image name is already crop name)
    if object_str_in_image_name:

        # returning image name
        return image_name

    # getting old/new extension
    old_ext = '.tif'
    new_ext = f'_{object_str}.tif'

    # getting crop name
    crop_name = image_name.replace(old_ext, new_ext)

    # returning crop name
    return crop_name


def get_image_name_col(model_architecture: str) -> str:
    """
    Given a model architecture, returns
    image name col.

    Args:
        model_architecture (str): The model architecture name (checked against 'nuclei' prefix).

    Returns:
        str: Either 'image_name' for non-nuclei models or 'crop_name' for nuclei-prefixed models.
    """
    # defining placeholder for image name col
    image_name_col = 'image_name'

    # getting model is nuclei bool (matches ImageDataset.py's own startswith('nuclei') convention)
    model_is_nuclei = model_architecture.startswith('nuclei')

    # checking if model is nuclei
    if model_is_nuclei:

        # updating image name col
        image_name_col = 'crop_name'

    # returning image name col
    return image_name_col


def get_image_path(row_data: Series,
                   image_name_col: str = 'image_name',
                   input_folder_col: str = 'input_folder'
                   ) -> str:
    """
    Given a splits df row data,
    returns image path.

    Args:
        row_data (Series): A pandas Series row containing image information.
        image_name_col (str, optional): Column name containing the image name. Defaults to 'image_name'.
        input_folder_col (str, optional): Column name containing the input folder path. Defaults to 'input_folder'.

    Returns:
        str: The full path to the image file.
    """
    # getting current row info
    image_name = row_data[image_name_col]
    input_folder = row_data[input_folder_col]

    # getting current image path
    image_path = join(input_folder,
                      image_name)

    # converting data types
    image_path = str(image_path)

    # returning current image path
    return image_path


def get_image_name_from_path(image_path: str) -> str:
    """
    Given an image path,
    returns image name.

    Args:
        image_path (str): The full path to an image file.

    Returns:
        str: The image filename with a standardized .tif extension.
    """
    # splitting image path
    image_name = split(image_path)

    # getting image name
    image_name = image_name[-1]

    # removing old extension
    image_name = image_name[:-4]

    # adding new extension
    image_name = f'{image_name}.tif'

    # returning image name
    return image_name


def get_folder_size(input_folder: str) -> int:
    """
    Given a path to a folder, returns
    full folder size in bytes
    (considering subfiles/subfolders).

    Args:
        input_folder (str): Path to the folder to measure.

    Returns:
        int: The total size of the folder in bytes, including all subdirectories and files.
    """
    # defining placeholder value for folder size
    folder_size = 0

    # getting folder structure
    folders_subfolders_files = walk(input_folder)

    # iterating over folders/subfolders/files
    for item in folders_subfolders_files:

        # getting current folder path/subfolders/files
        folder_path, subfolders, files = item

        # iterating over files
        for file in files:

            # getting current file path
            file_path = join(folder_path, file)

            # getting current file size
            file_size = getsize(filename=file_path)

            # updating total size
            folder_size += file_size

    # returning folder size
    return folder_size


def get_vars_dict() -> dict:
    """
    Returns a dictionary of
    currently loaded local
    variables.

    Returns:
        dict: The local variables dictionary of the calling frame.
    """
    # getting current frame
    current_frame = currentframe()

    # getting parent frame (caller module)
    caller_frame = current_frame.f_back  # noqa

    # getting current variables
    current_vars = caller_frame.f_locals  # noqa

    # returning current variables dict
    return current_vars


def get_var_names(vars_dict: dict) -> list:
    """
    Given a vars dict, returns
    a list of var names.

    Args:
        vars_dict (dict): A dictionary of variables.

    Returns:
        list: A list containing the keys of the input dictionary.
    """
    # getting dict keys
    dict_keys = vars_dict.keys()

    # converting data type
    var_names = list(dict_keys)

    # returning var names
    return var_names


def get_folder_vars(var_names: list) -> list:
    """
    Given a list of variable names, returns
    filtered list containing folder path
    variables only (contains "_FOLDER").

    Args:
        var_names (list): A list of variable names to filter.

    Returns:
        list: A list of variable names that contain the "_FOLDER" substring.
    """
    # defining placeholder value for folder vars
    folder_vars = []

    # iterating over var names
    for var_name in var_names:

        # getting data bools
        var_is_folder = ('_FOLDER' in var_name)

        # checking if current var name contains keyword
        if var_is_folder:

            # appending current var name to folder vars
            folder_vars.append(var_name)

    # returning folder vars
    return folder_vars


def get_subfolders_list(vars_dict: dict,
                        vars_to_skip: list | None = None
                        ) -> list:
    """
    Given a vars dict, returns a list of
    values of variables whose key is
    subfolder.

    Args:
        vars_dict (dict): A dictionary of variables containing folder path variables (with "_FOLDER" in their name).
        vars_to_skip (list | None, optional): Variable names to exclude from the result. Defaults to None.

    Returns:
        list: A list of subfolder paths extracted from the variables dictionary, flattening any nested dictionaries.
    """
    # getting var names
    var_names = get_var_names(vars_dict=vars_dict)

    # getting folder vars
    folder_vars = get_folder_vars(var_names=var_names)

    # checking if vars to skip is not none
    if vars_to_skip:

        # iterating over vars to skip
        for var_to_skip in vars_to_skip:

            # removing base folder from folders vars
            folder_vars.remove(var_to_skip)

    # defining placeholder value for subfolders list
    subfolders_list = []

    # iterating over folder vars
    for folder_var in folder_vars:

        # getting current folder var value
        current_subfolder = vars_dict.get(folder_var)

        # getting current value is dict bool (e.g. a per-dot {dot_key: folder_path} collector)
        current_subfolder_is_dict = isinstance(current_subfolder, dict)

        # checking if current value is a dict of folder paths rather than a bare path
        if current_subfolder_is_dict:

            # flattening dict values into subfolders list
            subfolders_list.extend(current_subfolder.values())

        # checking if current value is set (optional folders left unset are None, e.g. a cescale reference folder)
        elif current_subfolder is not None:

            # appending current subfolder to subfolders list
            subfolders_list.append(current_subfolder)

    # returning subfolders list
    return subfolders_list


def create_subfolders(base_folder: str,
                      subfolders_list: list
                      ) -> None:
    """
    Given a path to a base folder and
    a list of subfolders, creates subfolders
    in base folder, if they don't already exist.

    Args:
        base_folder (str): The base folder path where subfolders will be created.
        subfolders_list (list): A list of subfolder paths to create (may be absolute or relative paths).

    Returns:
        None

    Raises:
        Exception: If the base folder does not exist.
    """
    # getting base folder exists bool
    base_folder_exists = exists(base_folder)

    # checking if base folder exists
    if not base_folder_exists:

        # defining error message
        e_string = f'Base folder "{base_folder}" does not exist.\n'
        e_string += f'Please, check and try again.'

        # quitting
        raise Exception(e_string)

    # iterating over subfolders list
    for subfolder in subfolders_list:

        # creating subfolder (and any missing parents) if it does not already exist
        makedirs(name=subfolder,
                 exist_ok=True)


def delete_subfolders(subfolders_list: list) -> None:
    """
    Given a list of subfolders, deletes
    subfolders after user confirmation.

    Args:
        subfolders_list (list): A list of subfolder paths to delete.

    Returns:
        None
    """
    # defining placeholder value for total folder size
    total_size = 0

    # printing execution message
    f_string = f'These are the intermediate folders safe to be deleted:'
    print(f_string)

    # scanning folder sizes
    for folder_path in subfolders_list:

        # getting current folder size
        current_size = get_folder_size(input_folder=folder_path)

        # getting current size str
        current_size_str = get_size_str(size_in_bytes=current_size)

        # printing execution message
        f_string = f'{folder_path} ({current_size_str})'
        print(f_string)

        # updating total size
        total_size += current_size

    # getting size string
    total_size_str = get_size_str(size_in_bytes=total_size)

    # printing execution message
    f_string = f'Are you sure you wish to delete these intermediate folders?\n'
    f_string += f'A total of {total_size_str} will be cleared.\n'
    f_string += f'press "Ctrl+C" to abort or "Enter" to continue'
    print(f_string)

    # waiting for user input
    input()

    # deleting subfolders
    for folder_path in subfolders_list:

        # deleting folder
        rmtree(path=folder_path)


def get_skip_file_bool(file_path: str,
                       overwrite_output: bool
                       ) -> bool:
    """
    Given a file path, and conditional
    bools, returns True if file should
    be skipped, or False otherwise.

    Args:
        file_path (str): The path to the file to check.
        overwrite_output (bool): If False, the function will return True if the file already exists (skip it). If True, the function will return False (do not skip).

    Returns:
        bool: True if the file should be skipped, False otherwise.
    """
    # defining placeholder for skip file bool
    skip_file_bool = False

    # getting skip existing output bool
    skip_existing_output = (not overwrite_output)

    # checking whether to skip existing output
    if skip_existing_output:

        # getting file exists bool
        file_exists = exists(file_path)

        # checking if current output file already exists
        if file_exists:

            # updating skip file bool
            skip_file_bool = True

    # returning skip file bool
    return skip_file_bool


def save_metadata_file(output_folder: str,
                       metadata: dict
                       ) -> None:
    """
    Given an output folder and a metadata
    dict (json-serializable), writes it to a
    "metadata.json" file inside output_folder,
    creating/overwriting it as needed.

    Args:
        output_folder (str): The folder to save metadata.json into.
        metadata (dict): The metadata content to save.

    Returns:
        None.
    """
    # getting metadata file path
    metadata_path = join(output_folder,
                         'metadata.json')

    # defining read mode
    read_mode = 'w'

    # defining encoding
    encoding = 'utf-8'

    # writing metadata dict to metadata file
    with open(file=metadata_path,
              mode=read_mode,
              encoding=encoding) as open_file:

        # writing metadata content
        dump(obj=metadata,
             fp=open_file,
             indent=2,
             ensure_ascii=False)

######################################################################
# end of current module
