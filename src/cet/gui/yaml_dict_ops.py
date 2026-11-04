# yaml dict ops module

# Code destined to defining
# nested dictionary get/set
# helpers used when reading and
# writing PipelineGUI settings YAMLs.

######################################################################
# defining auxiliary functions


def get_nested_val(data: dict,
                   key_path: tuple
                   ):
    """
    Retrieves a nested value from dictionary
    given a key tuple.

    Args:
        data (dict): Dictionary to traverse.
        key_path (tuple): Sequence of keys to traverse.

    Returns:
        The value at the key path, or None if not found.
    """
    # defining base current dict reference
    curr = data

    # iterating over key path elements
    for k in key_path:

        # checking if current element is dict and key exists
        if isinstance(curr, dict) and k in curr:

            # traversing deeper
            curr = curr[k]

        # returning None if key path is missing
        else:

            # returning None
            return None

    # returning nested value
    return curr


def set_nested_val(data: dict,
                   key_path: tuple,
                   value
                   ) -> None:
    """
    Sets a nested value inside dictionary given
    a key tuple, automatically casting types.

    Args:
        data (dict): Dictionary to modify.
        key_path (tuple): Sequence of keys to traverse.
        value: Value to set; strings are auto-cast to bool/int/float if they match those formats.

    Returns:
        None.
    """
    # defining base current dict reference
    curr = data

    # traversing to target parent dictionary
    for k in key_path[:-1]:
        # setting default dict if key missing
        curr = curr.setdefault(k, {})

    # checking if value is string
    if isinstance(value, str):

        # stripping whitespace
        val_strip = value.strip()

        # checking boolean values
        if val_strip.lower() == 'true':
            typed_val = True
        elif val_strip.lower() == 'false':
            typed_val = False

        # parsing numerical or string values
        else:
            try:
                typed_val = int(val_strip)
            except ValueError:
                try:
                    typed_val = float(val_strip)
                except ValueError:
                    typed_val = value

        # setting typed value
        curr[key_path[-1]] = typed_val

    # setting raw value
    else:
        curr[key_path[-1]] = value

######################################################################
# end of current module
