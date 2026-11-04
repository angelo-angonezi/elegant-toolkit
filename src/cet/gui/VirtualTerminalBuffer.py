# VirtualTerminalBuffer module

# Code destined to defining
# VirtualTerminalBuffer class and
# related GUI attributes/methods.

######################################################################
# VirtualTerminalBuffer definition


class VirtualTerminalBuffer:
    """
    Simulates a real OS terminal line buffer in
    memory, handling carriage return, backspace,
    and newline characters.
    """
    def __init__(self) -> None:
        """
        Initializes a VirtualTerminalBuffer instance
        and defines class attributes.

        Returns:
            None.
        """
        # defining class attributes
        self.line_chars = []
        self.cursor_pos = 0

    def write_char(self,
                   char: str
                   ) -> list:
        """
        Processes a single character and returns
        a list of completed lines ending in newline.

        Args:
            char (str): The character to process.

        Returns:
            list: The list of completed lines ending in newline.
        """
        # defining completed lines list
        completed_lines = []

        # checking if char is carriage return
        if char == '\r':

            # resetting cursor position to start of line
            self.cursor_pos = 0

        # checking if char is backspace
        elif char == '\b' or char == '\x08':

            # checking if cursor position can move back
            if self.cursor_pos > 0:

                # decrementing cursor position
                self.cursor_pos -= 1

        # checking if char is newline
        elif char == '\n':

            # assembling final line
            final_line = ''.join(self.line_chars).rstrip()

            # appending completed line
            completed_lines.append(f'{final_line}\n')

            # resetting line buffer and cursor position
            self.line_chars = []
            self.cursor_pos = 0

        # handling standard character
        else:

            # checking if character overwrites existing position
            if self.cursor_pos < len(self.line_chars):

                # overwriting char at cursor position
                self.line_chars[self.cursor_pos] = char

            # if character extends line length
            else:

                # appending char to line
                self.line_chars.append(char)

            # incrementing cursor position
            self.cursor_pos += 1

            # dropping stale trailing chars left over from a longer previous line
            del self.line_chars[self.cursor_pos:]

        # returning completed lines
        return completed_lines

    def get_active_line(self) -> str:
        """
        Returns current in-progress line string
        without committing it permanently.

        Returns:
            str: The current in-progress line string.
        """
        # assembling active line string
        active_line = ''.join(self.line_chars).rstrip()

        # returning active line string
        return active_line

######################################################################
# end of current module