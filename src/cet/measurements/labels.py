# labels measurements module

# Code destined to storing labels
# measurements related operations.

######################################################################
# imports

from cet.config import GPU

# doing conditional imports depending on gpu availability

if GPU:
    from cupy import unique
    from cupy import ndarray
else:
    from numpy import unique
    from numpy import ndarray

######################################################################
# defining auxiliary functions


def get_object_ids(mask: ndarray) -> list:
    """
    Returns a list containing all object
    ids from a segmentation mask.

    Args:
        mask (ndarray): The segmentation mask.

    Returns:
        list: List of object ids.
    """
    # getting current mask unique values
    object_ids = unique(mask)

    # getting positive only values (exclude zeros)
    object_ids = object_ids[object_ids > 0]

    # converting ids to list
    object_ids = object_ids.tolist()

    # sorting list
    object_ids = sorted(object_ids)

    # returning object ids list
    return object_ids


def get_uid(image_index: int,
            description: str,
            object_id: int
            ) -> str:
    """
    Returns a uid (unique string identifier)
    for an object in the current dataset.

    Args:
        image_index (int): The image index.
        description (str): The object description.
        object_id (int): The object id.

    Returns:
        str: The unique identifier string.
    """
    # getting description identifier
    identifier = description[0]

    # assembling current uid
    uid = f'i{image_index}_{identifier}{object_id}'

    # returning uid
    return uid

######################################################################
# end of current module
