# download ops module

# Code destined to shared streaming download/copy
# helpers, used by cet.setup.download_cescale_data
# and cet.setup.download_cp_models to fetch large
# files with byte-level ModuleProgressTracker
# integration (see cet.progress_tracker.ProgressTracker).

######################################################################
# imports

from cet.constants import ONE_MB
from urllib.request import Request
from urllib.request import urlopen
from os import replace as os_replace

######################################################################
# defining global variables

COPY_CHUNK_SIZE = ONE_MB

######################################################################
# defining auxiliary functions


def get_url_content_length(url: str) -> int:
    """
    Given a url, issues a HEAD request and
    returns its Content-Length header (0 if
    absent/unreliable), without fetching the
    body - used to size a ModuleProgressTracker's
    iterations_num ahead of time.

    Args:
        url (str): The url to issue the HEAD request to.

    Returns:
        int: The url's Content-Length header, or 0 if absent/unreliable.
    """
    # issuing HEAD request (fetches headers only, not the body)
    request = Request(url,
                      method='HEAD')

    # opening remote url
    with urlopen(request) as response:

        # returning content length (0 if header is absent)
        return int(response.headers.get('Content-Length',
                                        0))


def download_file(url: str,
                  output_path: str,
                  progress_tracker
                  ) -> None:
    """
    Downloads url to output_path, streaming in
    fixed-size chunks and advancing
    progress_tracker.current_iteration by each
    chunk's byte count. Writes to a temporary
    "<output_path>.part" file, renamed into
    place only once complete, so a partial/
    interrupted download never leaves a corrupt
    file at output_path (same guarantee
    Cellpose's own download_url_to_file
    provides).

    Args:
        url (str): The url to download from.
        output_path (str): The path to write the downloaded file to.
        progress_tracker: The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting temp output path
    temp_path = f'{output_path}.part'

    # opening remote url
    with urlopen(url) as response:

        # opening temp output file
        with open(file=temp_path,
                  mode='wb') as open_file:

            # iterating over remote content (in fixed-size chunks)
            while True:

                # reading current chunk
                chunk = response.read(COPY_CHUNK_SIZE)

                # checking whether download is complete
                if not chunk:

                    # breaking iteration loop
                    break

                # writing current chunk
                open_file.write(chunk)

                # updating progress tracker attributes
                progress_tracker.current_iteration += len(chunk)

    # moving temp file into place (atomic rename)
    os_replace(temp_path,
               output_path)


def copy_file(source_path: str,
              output_path: str,
              progress_tracker
              ) -> None:
    """
    Copies source_path to output_path,
    streaming in fixed-size chunks and
    advancing progress_tracker.current_iteration
    by each chunk's byte count. Mirrors
    download_file's temp-file-then-rename
    atomicity.

    Args:
        source_path (str): The path to copy from.
        output_path (str): The path to copy to.
        progress_tracker: The current module's progress tracker instance.

    Returns:
        None.
    """
    # getting temp output path
    temp_path = f'{output_path}.part'

    # opening source/temp output files
    with open(file=source_path, mode='rb') as source_file, \
         open(file=temp_path, mode='wb') as output_file:

        # iterating over source content (in fixed-size chunks)
        while True:

            # reading current chunk
            chunk = source_file.read(COPY_CHUNK_SIZE)

            # checking whether copy is complete
            if not chunk:

                # breaking iteration loop
                break

            # writing current chunk
            output_file.write(chunk)

            # updating progress tracker attributes
            progress_tracker.current_iteration += len(chunk)

    # moving temp file into place (atomic rename)
    os_replace(temp_path,
               output_path)

######################################################################
# end of current module
