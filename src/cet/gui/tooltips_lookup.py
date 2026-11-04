# tooltips lookup module

# Code destined to defining
# hover-tooltip lookup helpers
# used by PipelineGUI.

######################################################################
# imports

import re
import textwrap

# matches dynamically-numbered key_path segments (dot1, dot2, ch0, ch1, ...)
# stripped out when looking up a tooltip so repeated dot/channel blocks share one entry
DYNAMIC_KEY_SEGMENT_PATTERN = re.compile(r'^(dot|ch)\d+$')

# maximum characters per tooltip line (including spaces) before a line break is inserted
TOOLTIP_MAX_LINE_LENGTH = 120

######################################################################
# defining auxiliary functions


def wrap_tooltip(text: str) -> str:
    """
    Inserts '\\n' line breaks at word boundaries
    so no tooltip line exceeds TOOLTIP_MAX_LINE_LENGTH
    characters (including spaces).

    Args:
        text (str): Tooltip text.

    Returns:
        str: Wrapped tooltip text ('' if text is empty).
    """
    return '\n'.join(textwrap.wrap(text, width=TOOLTIP_MAX_LINE_LENGTH))


def tooltip_for_key_path(tooltips: dict,
                         key_path: tuple
                         ) -> str:
    """
    Looks up hover-tooltip text for a parameter
    widget's key_path, normalizing away
    dynamically-numbered segments (dot1, dot2,
    ch0, ch1, ...) so repeated dot/channel blocks
    share one tooltip entry.

    Args:
        tooltips (dict): Loaded tooltips JSON data.
        key_path (tuple): Registry key path to look up.

    Returns:
        str: Tooltip text, or '' if no entry matches.
    """
    normalized = tuple(seg for seg in key_path if not DYNAMIC_KEY_SEGMENT_PATTERN.match(str(seg)))
    lookup_key = '.'.join(normalized)
    return wrap_tooltip(tooltips.get('parameters', {}).get(lookup_key, ''))


def tooltip_for_control(tooltips: dict,
                        control_id: str
                        ) -> str:
    """
    Looks up hover-tooltip text for a
    non-parameter widget (button, section header)
    by its hand-picked control id.

    Args:
        tooltips (dict): Loaded tooltips JSON data.
        control_id (str): Control identifier string.

    Returns:
        str: Tooltip text, or '' if no entry matches.
    """
    return wrap_tooltip(tooltips.get('controls', {}).get(control_id, ''))

######################################################################
# end of current module
