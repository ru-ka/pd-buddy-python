"""Python bindings for PD Buddy Sink configuration"""

from collections import namedtuple

try:
    # Try importing enum from the standard library
    import enum
    # Make sure Flag is available
    enum.Flag
except (ImportError, NameError):
    # If something above failed, try aenum instead
    import aenum as enum

import serial
import serial.tools.list_ports


class Sink:
    """Interface for configuring a PD Buddy Sink"""
    vid = 0x1209
    pid = 0x9DB5

    def __init__(self, sp):
        """Open a serial port to communicate with the PD Buddy Sink
        
        :param sp: the serial port of the device
        :type sp: str or `serial.tools.list_ports.ListPortInfo`
        """
        try:
            self._port = serial.Serial(sp, baudrate=115200)
        except ValueError:
            self._port = serial.Serial(sp.device, baudrate=115200)

        # Put communications in a known state, cancelling any partially-entered
        # command that may be sitting in the buffer.
        self.send_command("\x04", newline=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._port.close()

    def send_command(self, cmd, newline=True):
        """Send a command to the PD Buddy Sink, returning the result
        
        :param cmd: the text to send to the Sink
        :param newline: whether to append a ``\r\n`` to the command
        :type cmd: str
        :type newline: bool
        
        :returns: a list of zero or more bytes objects, each being one line
            printed as a response to the command.
        """
        # Build the command
        cmd = cmd.encode("utf-8")
        if newline:
            cmd += b"\r\n"

        # Send the command
        self._port.write(cmd)
        self._port.flush()

        # Read the result
        answer = b""
        while not answer.endswith(b"PDBS) "):
            answer += self._port.read(1)
        answer = answer.split(b"\r\n")

        # Remove the echoed command and prompt
        answer = answer[1:-1]

        # Raise an exception if the command wasn't recognized
        if len(answer) and answer[0] == cmd.strip().split()[0] + b" ?":
            raise KeyError("command not found")

        return answer

    def close(self):
        """Close the serial port"""
        self._port.close()

    def help(self):
        """Returns the help text from the PD Buddy Sink"""
        return self.send_command("help")

    def license(self):
        """Returns the license text from the PD Buddy Sink"""
        return self.send_command("license")

    def erase(self):
        """Synchronously erases all stored configuration from flash"""
        self.send_command("erase")

    def write(self):
        """Synchronously writes the contents of the configuration buffer to flash"""
        self.send_command("write")

    def load(self):
        """Loads the current configuration from flash into the buffer
        
        :raises: KeyError
        """
        text = self.send_command("load")
        if len(text) > 0 and text[0].startswith(b"No configuration"):
            raise KeyError("no configuration")

    def get_cfg(self, index=None):
        """Reads configuration from flash
         
        :param index: optional index of configuration object in flash to read

        :returns: a `SinkConfig` object
        """
        if index is None:
            cfg = self.send_command("get_cfg")
        else:
            cfg = self.send_command("get_cfg {}".format(index))

        return SinkConfig.from_text(cfg)

    def get_tmpcfg(self):
        """Reads the contents of the configuration buffer

        :returns: a `SinkConfig` object
        """
        cfg = self.send_command("get_tmpcfg")

        return SinkConfig.from_text(cfg)

    def clear_flags(self):
        """Clears all the flags in the configuration buffer"""
        self.send_command("clear_flags")

    def toggle_giveback(self):
        """Toggles the GiveBack flag in the configuration buffer"""
        self.send_command("toggle_giveback")

    def set_v(self, mv):
        """Sets the voltage of the configuration buffer, in millivolts"""
        out = self.send_command("set_v {}".format(mv))
        # If that command gave any output, that indicates an error.  Raise an
        # exception to make that clear.
        if len(out):
            raise ValueError(out[0])

    def set_i(self, ma):
        """Sets the current of the configuration buffer, in milliamperes"""
        out = self.send_command("set_i {}".format(ma))
        # If that command gave any output, that indicates an error.  Raise an
        # exception to make that clear.
        if len(out):
            raise ValueError(out[0])

    def identify(self):
        """Blinks the LED quickly"""
        self.send_command("identify")

    @property
    def output(self):
        """The state of the Sink's output

        Raises KeyError if the ``output`` command is not available on the Sink.
        Raises ValueError if an invalid output is read.
        """
        value = self.send_command("output")
        if value[0] == b"enabled":
            return True
        elif value[0] == b"disabled":
            return False
        else:
            # If unexpected text is returned, raise an exception indicating a
            # firmware error
            raise ValueError("unknown output state")

    @output.setter
    def output(self, state):
        if state:
            self.send_command("output enable")
        else:
            self.send_command("output disable")


    def set_tmpcfg(self, sc):
        """Writes a SinkConfig object to the device's configuration buffer
        
        Note: the value of the status field is ignored; it will always be
        `SinkStatus.VALID`.
        """
        # Set flags
        self.clear_flags()
        if sc.flags & SinkFlags.GIVEBACK:
            self.toggle_giveback()

        # Set voltage
        self.set_v(sc.v)
        
        # Set current
        self.set_i(sc.i)

    @classmethod
    def get_devices(cls):
        """Get an iterable of PD Buddy Sink devices
        
        :returns: an iterable of `serial.tools.list_ports.ListPortInfo` objects
        """
        return serial.tools.list_ports.grep("{:04X}:{:04X}".format(cls.vid,
            cls.pid))


class SinkConfig(namedtuple("SinkConfig", "status flags v i")):
    """Python representation of a PD Buddy Sink configuration object

    ``status`` should be a `SinkStatus` object.  ``flags`` should be zero or
    more `SinkFlags` values.  ``v`` is the voltage in millivolts, and ``i``
    is the current in milliamperes.  `None` is also an acceptible value for
    any of the fields.
    """
    __slots__ = ()

    def __str__(self):
        """Print the SinkStatus in the manner of the configuration shell"""
        s = ""

        if self.status is not None:
            s += "status: "
            if self.status is SinkStatus.EMPTY:
                s += "empty"
            elif self.status is SinkStatus.VALID:
                s += "valid"
            elif self.status is SinkStatus.INVALID:
                s += "invalid"
            s += "\n"

        if self.flags is not None:
            s += "flags: "
            if self.flags is SinkFlags.NONE:
                s += "(none)"
            else:
                if self.flags & SinkFlags.GIVEBACK:
                    s += "GiveBack"
            s += "\n"

        if self.v is not None:
            s += "v: {:.2f} V\n".format(self.v / 1000)

        if self.i is not None:
            s += "i: {:.2f} A\n".format(self.i / 1000)

        # Return all but the last character of s to remove the trailing newline
        if s:
            return s[:-1]
        else:
            return "No configuration"

    @classmethod
    def from_text(cls, text):
        """Creates a SinkConfig from text returned by Sink.send_command

        :param text: the text to load
        :type text: a list of bytes objects
        :returns: a new `SinkConfig` object.

        :raises: IndexError
        """
        # Assume the parameters will all be None
        status = None
        flags = None
        v = None
        i = None

        # Iterate over all lines of text
        for line in text:
            # If the configuration said invalid index, raise an IndexError
            if line.startswith(b"Invalid index"):
                raise IndexError("configuration index out of range")
            # If there is no configuration, return an empty SinkConfig
            elif line.startswith(b"No configuration"):
                return cls(None, None, None, None)
            # If this line is the status field
            elif line.startswith(b"status: "):
                line = line.split()[1:]
                if line[0] == b"empty":
                    status = SinkStatus.EMPTY
                elif line[0] == b"valid":
                    status = SinkStatus.VALID
                elif line[0] == b"invalid":
                    status = SinkStatus.INVALID
            # If this line is the flags field
            elif line.startswith(b"flags: "):
                line = line.split()[1:]
                flags = SinkFlags.NONE
                for word in line:
                    if word == b"(none)":
                        # If there are no flags set, stop looking
                        break
                    elif word == b"GiveBack":
                        flags |= SinkFlags.GIVEBACK
            # If this line is the v field
            elif line.startswith(b"v: "):
                word = line.split()[1]
                v = round(1000*float(word))
            # If this line is the i field
            elif line.startswith(b"i: "):
                word = line.split()[1]
                i = round(1000*float(word))

        # Create a new SinkConfig object with the values we just read
        return cls(status=status, flags=flags, v=v, i=i)


class SinkStatus(enum.Enum):
    """Status field of a PD Buddy Sink configuration object"""
    EMPTY = 1
    VALID = 2
    INVALID = 3


class SinkFlags(enum.Flag):
    """Flags field of a PD Buddy Sink configuration object"""
    NONE = 0
    GIVEBACK = enum.auto()
