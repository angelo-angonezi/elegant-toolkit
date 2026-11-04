# metadata module

# Code destined to storing
# shared metadata extraction operations.

######################################################################
# imports

from numpy import generic
from numpy import ndarray
from datetime import date
from datetime import datetime
from cet.config import JAVA_MEMORY
from pims.bioformats import BioformatsReader

######################################################################
# defining auxiliary functions


def to_serializable(value):
    """
    Recursively converts a value into
    something json-serializable (dict keys
    are cast to str, bytes are decoded,
    numpy objects are converted to python
    types, dates to iso strings and any
    unknown type to its str representation).

    Args:
        value: The value to convert.

    Returns:
        The json-serializable version of value.
    """
    # checking for simple types
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    # checking for dicts
    if isinstance(value, dict):
        return {str(to_serializable(key)): to_serializable(item)
                for key, item in value.items()}

    # checking for sequences
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_serializable(item) for item in value]

    # checking for bytes
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode(encoding='utf-8',
                                   errors='replace')

    # checking for numpy arrays and scalars
    if isinstance(value, (ndarray, generic)):
        return to_serializable(value.tolist())

    # checking for dates
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    # falling back to string representation
    return str(value)


def get_java_hashtable_dict(hashtable) -> dict:
    """
    Given a java Hashtable, returns
    it as a {str: str} dict.

    Args:
        hashtable: The java Hashtable to convert.

    Returns:
        dict: The converted hashtable.
    """
    # defining placeholder dict
    hashtable_dict = {}

    # getting hashtable keys
    keys = hashtable.keys()

    # iterating over keys
    while keys.hasMoreElements():

        # getting current key
        key = keys.nextElement()

        # storing current key and value as strings
        current_dict = {str(key): str(hashtable.get(key))}
        hashtable_dict.update(current_dict)

    # returning hashtable dict
    return hashtable_dict


def extract_metadata(input_path: str) -> dict:
    """
    Given a path to a bioformats-readable file (ics/tif/vsi),
    returns all its metadata as a json-serializable dict (no pixel
    data is read). The dict contains:
        - "global_metadata": the reader's global ("original") metadata table.
        - "series_metadata": a list with one metadata table per series.
        - "ome_xml": the full OME-XML string (physical sizes, channels,
          planes, instrument, etc.) as built by bioformats.

    Args:
        input_path (str): The path to the file to extract metadata from.

    Returns:
        dict: The extracted metadata.
    """
    # reading image
    image = BioformatsReader(filename=input_path,
                             java_memory=JAVA_MEMORY)

    # getting global metadata as a dict
    # (get_metadata_raw(form='string') is not used since pims.bioformats builds it by
    # concatenating raw java.lang.String keys onto a python str, which raises
    # "can only concatenate str (not 'java.lang.String') to str")
    global_metadata = get_java_hashtable_dict(image.rdr.getGlobalMetadata())

    # getting the metadata table of each series
    series_metadata = []
    for series in range(int(image.rdr.getSeriesCount())):

        # switching to current series
        image.rdr.setSeries(series)

        # storing current series metadata
        series_metadata.append(get_java_hashtable_dict(image.rdr.getSeriesMetadata()))

    # getting the full OME-XML
    ome_xml = str(image._metadata.dumpXML())

    # manually deleting image from memory
    # (java bridge issues make the image be stored even though it should be overwritten)
    del image

    # building metadata dict
    metadata = {'global_metadata': global_metadata,
                'series_metadata': series_metadata,
                'ome_xml': ome_xml}

    # returning extracted metadata
    return metadata

######################################################################
# end of current module
