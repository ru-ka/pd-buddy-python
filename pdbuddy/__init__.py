"""Python bindings for PD Buddy Sink configuration"""

from enum import *

import serial
import serial.tools.list_ports


class Sink:
    """Interface for configuring a PD Buddy Sink"""
    vid = 0x1209
    pid = 0x0001

    def __init__(self, sp):
        """Open the serial port to communicate with the PD Buddy Sink
        
        Parameters:
            sp: A serial.tools.list_ports.ListPortInfo object
        """
        self.port = serial.Serial(sp.device, baudrate=115200)

    def send_command(self, cmd):
        """Send a command to the PD Buddy Sink, returning the result
        
        Parameters:
            cmd: A string containing the text to send to the Sink
        
        Returns:
            A list of zero or more bytes objects, each being one line printed
            as a response to the command.
        """
        # Send the command
        self.port.write(bytes(cmd, "utf-8") + b"\r\n")
        self.port.flush()

        # Read the result
        answer = b""
        while not answer.endswith(b"PDBS) "):
            answer += self.port.read(1)
        answer = answer.split(b"\r\n")

        # Remove the echoed command and prompt
        answer = answer[1:-1]
        return answer

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
        
        Raises KeyError if there is no configuration in flash.
        """
        text = self.send_command("load")
        if len(text) > 0 and text[0].startswith(b"No configuration"):
            raise KeyError("no configuration")

    def get_cfg(self, index=None):
        """Reads configuration from flash
         
        Parameters:
            index: Optional index of configuration object in flash to read

        Returns:
            A SinkConfig object
        """
        if index is None:
            cfg = self.send_command("get_cfg")
        else:
            cfg = self.send_command("get_cfg {}".format(index))

        return SinkConfig.from_text(cfg)

    def get_tmpcfg(self):
        """Reads the contents of the configuration buffer

        Returns:
            A SinkConfig object
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
        self.send_command("set_v {}".format(mv))

    def set_i(self, ma):
        """Sets the current of the configuration buffer, in milliamperes"""
        self.send_command("set_i {}".format(ma))

    def identify(self):
        """Blinks the LED quickly"""
        self.send_command("identify")

    def set_tmpcfg(self, sc):
        """Writes a SinkConfig object to the device's configuration buffer
        
        Note: the value of the status field is ignored; it will always be
        SinkStatus.VALID.
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
        
        Returns an iterable of serial.tools.list_ports.ListPortInfo objects.
        """
        return serial.tools.list_ports.grep("{:04X}:{:04X}".format(cls.vid,
            cls.pid))


class SinkConfig:
    """Python representation of a PD Buddy Sink configuration object"""

    def __init__(self, status=None, flags=None, v=None, i=None):
        """Create a SinkConfig object
        
        Parameters:
            status: A SinkStatus value
            flags: Zero or more SinkFlags values
            v: Voltage in millivolts
            i: Current in milliamperes
        """
        self.status = status
        self.flags = flags
        self.v = v
        self.i = i

    def __repr__(self):
        s = type(self).__name__ + "("

        if self.status is not None:
            s += "status={}".format(self.status)

        if self.flags is not None:
            if not s.endswith("("):
                s += ", "
            s += "flags={}".format(self.flags)

        if self.v is not None:
            if not s.endswith("("):
                s += ", "
            s += "v={}".format(self.v)

        if self.i is not None:
            if not s.endswith("("):
                s += ", "
            s += "i={}".format(self.i)

        s += ")"

        return s

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if other.status is not self.status:
                return False
            if other.flags is not self.flags:
                return False
            if other.v != self.v:
                return False
            if other.i != self.i:
                return False
            return True
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))

    @classmethod
    def from_text(cls, text):
        """Creates a SinkConfig from text returned by Sink.send_command
        
        Returns a new SinkConfig object.

        Raises IndexError if the configuration reads "Invalid index".
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
                return cls()
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


class SinkStatus(Enum):
    """Status field of a PD Buddy Sink configuration object"""
    EMPTY = 1
    VALID = 2
    INVALID = 3


class SinkFlags(Flag):
    """Flags field of a PD Buddy Sink configuration object"""
    NONE = 0
    GIVEBACK = auto()