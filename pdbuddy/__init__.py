"""Python bindings for PD Buddy Sink configuration"""

from collections import namedtuple

try:
    # Try importing enum from the standard library
    import enum
    # Make sure Flag is available
    enum.Flag
except (ImportError, NameError, AttributeError):
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

    def boot(self):
        """Runs the PD Buddy Sink's DFU bootloader and closes the serial port"""
        self._port.write(b"boot\r\n")
        self._port.flush()
        self.close()

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

    def toggle_hv_preferred(self):
        """Toggles the HV_Preferred flag in the configuration buffer"""
        self.send_command("toggle_hv_preferred")

    def set_v(self, mv):
        """Sets the voltage of the configuration buffer, in millivolts"""
        out = self.send_command("set_v {}".format(mv))
        # If that command gave any output, that indicates an error.  Raise an
        # exception to make that clear.
        if len(out):
            raise ValueError(out[0])

    def set_vrange(self, vmin, vmax):
        """Sets the min and max voltage of the configuration buffer, in millivolts"""
        # First, make sure we're sending numbers to the Sink in all valid cases
        if vmin is None and vmax is None:
            vmin = 0
            vmax = 0
        out = self.send_command("set_vrange {} {}".format(vmin, vmax))
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

    def set_p(self, mw):
        """Sets the power of the configuration buffer, in milliwatts"""
        out = self.send_command("set_p {}".format(mw))
        # If that command gave any output, that indicates an error.  Raise an
        # exception to make that clear.
        if len(out):
            raise ValueError(out[0])

    def set_r(self, mr):
        """Sets the resistance of the configuration buffer, in milliohms"""
        out = self.send_command("set_r {}".format(mr))
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

    def get_source_cap(self):
        """Gets the most recent Source_Capabilities read by the Sink"""
        return read_pdo_list(self.send_command("get_source_cap"))

    def set_tmpcfg(self, sc):
        """Writes a SinkConfig object to the device's configuration buffer
        
        Note: the value of the status field is ignored; it will always be
        `SinkStatus.VALID`.
        """
        # Set flags
        self.clear_flags()
        if sc.flags & SinkFlags.GIVEBACK:
            self.toggle_giveback()
        if sc.flags & SinkFlags.HV_PREFERRED:
            self.toggle_hv_preferred()

        # Set voltage
        self.set_v(sc.v)

        # Set voltage range
        self.set_vrange(sc.vmin, sc.vmax)

        if sc.idim is SinkDimension.CURRENT:
            # Set current
            self.set_i(sc.i)
        elif sc.idim is SinkDimension.POWER:
            # Set power
            self.set_p(sc.i)
        elif sc.idim is SinkDimension.RESISTANCE:
            # Set resistance
            self.set_r(sc.i)

    @classmethod
    def get_devices(cls):
        """Get an iterable of PD Buddy Sink devices
        
        :returns: an iterable of `serial.tools.list_ports.ListPortInfo` objects
        """
        return serial.tools.list_ports.grep("{:04X}:{:04X}".format(cls.vid,
            cls.pid))


class SinkConfig(namedtuple("SinkConfig", "status flags v vmin vmax i idim")):
    """Python representation of a PD Buddy Sink configuration object

    ``status`` should be a `SinkStatus` object.  ``flags`` should be zero or
    more `SinkFlags` values.  ``v``, ``vmin``, and ``vmax`` are voltages in
    millivolts, ``i`` is the value used to set current in the appropriate
    milli- SI unit, and ``idim`` is the dimension of ``i``.  `None` is also
    an acceptible value for any of the fields.
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
                if self.flags & SinkFlags.HV_PREFERRED:
                    s += "HV_Preferred"
            s += "\n"

        if self.v is not None:
            s += "v: {:.3f} V\n".format(self.v / 1000.0)

        if self.vmin is not None:
            s += "vmin: {:.3f} V\n".format(self.vmin / 1000.0)

        if self.vmax is not None:
            s += "vmax: {:.3f} V\n".format(self.vmax / 1000.0)

        if self.i is not None:
            if self.idim is SinkDimension.CURRENT:
                s += "i: {:.2f} A\n".format(self.i / 1000.0)
            if self.idim is SinkDimension.POWER:
                s += "p: {:.2f} W\n".format(self.i / 1000.0)
            if self.idim is SinkDimension.RESISTANCE:
                s += "r: {:.2f} \u03A9\n".format(self.i / 1000.0)

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
        vmin = None
        vmax = None
        i = None
        idim = None

        # Iterate over all lines of text
        for line in text:
            # If the configuration said invalid index, raise an IndexError
            if line.startswith(b"Invalid index"):
                raise IndexError("configuration index out of range")
            # If there is no configuration, return an empty SinkConfig
            elif line.startswith(b"No configuration"):
                return cls(None, None, None, None, None, None, None)
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
                    elif word == b"HV_Preferred":
                        flags |= SinkFlags.HV_PREFERRED
            # If this line is the v field
            elif line.startswith(b"v: "):
                word = line.split()[1]
                v = round(1000*float(word))
            # If this line is the vmin field
            elif line.startswith(b"vmin: "):
                word = line.split()[1]
                vmin = round(1000*float(word))
            # If this line is the vmax field
            elif line.startswith(b"vmax: "):
                word = line.split()[1]
                vmax = round(1000*float(word))
            # If this line is the i field
            elif line.startswith(b"i: "):
                word = line.split()[1]
                i = round(1000*float(word))
                idim = SinkDimension.CURRENT
            # If this line is the p field
            elif line.startswith(b"p: "):
                word = line.split()[1]
                i = round(1000*float(word))
                idim = SinkDimension.POWER
            # If this line is the r field
            elif line.startswith(b"r: "):
                word = line.split()[1]
                i = round(1000*float(word))
                idim = SinkDimension.RESISTANCE

        # Create a new SinkConfig object with the values we just read
        return cls(status=status, flags=flags, v=v, vmin=vmin, vmax=vmax, i=i,
                idim=idim)


class SinkStatus(enum.Enum):
    """Status field of a PD Buddy Sink configuration object"""
    EMPTY = 1
    VALID = 2
    INVALID = 3


class SinkDimension(enum.Enum):
    """Dimension of the value used to set the current requested"""
    CURRENT = 1
    POWER = 2
    RESISTANCE = 3


class SinkFlags(enum.Flag):
    """Flags field of a PD Buddy Sink configuration object"""
    NONE = 0
    GIVEBACK = enum.auto()
    HV_PREFERRED = enum.auto()


class UnknownPDO(namedtuple("UnknownPDO", "value")):
    """A PDO of an unknown type

    ``value`` should be a 32-bit integer representing the PDO exactly as
    transmitted.
    """
    __slots__ = ()

    pdo_type = "unknown"

    def __str__(self):
        """Print the UnknownPDO in the manner of the configuration shell"""
        return "{:08X}".format(self.value)


class SrcFixedPDO(namedtuple("SrcFixedPDO", "dual_role_pwr usb_suspend "
        "unconstrained_pwr usb_comms dual_role_data unchunked_ext_msg peak_i "
        "v i")):
    """A Source Fixed PDO

    ``dual_role_pwr``, ``usb_suspend``, ``unconstrained_pwr``,
    ``usb_comms``, ``dual_role_data``, and ``unchunked_ext_msg`` should be
    booleans.  ``peak_i`` should be an integer in the range [0, 3].  ``v``
    is the voltage in millivolts, and ``i`` is the maximum current in
    milliamperes.
    """
    __slots__ = ()

    pdo_type = "fixed"

    def __str__(self):
        """Print the SrcFixedPDO in the manner of the configuration shell"""
        s = self.pdo_type + "\n"

        if self.dual_role_pwr:
            s += "\tdual_role_pwr: 1\n"

        if self.usb_suspend:
            s += "\tusb_suspend: 1\n"

        if self.unconstrained_pwr:
            s += "\tunconstrained_pwr: 1\n"

        if self.usb_comms:
            s += "\tusb_comms: 1\n"

        if self.dual_role_data:
            s += "\tdual_role_data: 1\n"

        if self.unchunked_ext_msg:
            s += "\tunchunked_ext_msg: 1\n"

        if self.peak_i:
            s += "\tpeak_i: {}\n".format(self.peak_i)

        s += "\tv: {:.2f} V\n".format(self.v / 1000.0)
        s += "\ti: {:.2f} A".format(self.i / 1000.0)

        return s


class SrcPPSAPDO(namedtuple("SrcPPSAPDO", "vmin vmax i")):
    """A Source Programmable Power Supply APDO

    ``vmin`` and ``vmax`` are the minimum and maximum voltage in millivolts,
    respectively, and ``i`` is the maximum current in milliamperes.
    """
    __slots__ = ()

    pdo_type = "pps"

    def __str__(self):
        """Print the SrcPPSAPDO in the manner of the configuration shell"""
        s = self.pdo_type + "\n"

        s += "\tvmin: {:.2f} V\n".format(self.vmin / 1000.0)
        s += "\tvmax: {:.2f} V\n".format(self.vmax / 1000.0)
        s += "\ti: {:.2f} A".format(self.i / 1000.0)

        return s


class TypeCVirtualPDO(namedtuple("TypeCVirtualPDO", "i")):
    """A Type-C Current Virtual PDO

    ``i`` is the advertised current in milliamperes.
    """
    __slots__ = ()

    pdo_type = "typec_virtual"

    def __str__(self):
        """Print the TypeCVirtualPDO in the manner of the configuration shell"""
        s = self.pdo_type + "\n"

        s += "\ti: {:.2f} A".format(self.i / 1000.0)

        return s


def read_pdo(text):
    """Create a PDO object from partial text returned by Sink.send_command"""
    # First, determine the PDO type
    pdo_type = text[0].split(b":")[-1].strip().decode("utf-8")

    if pdo_type == SrcFixedPDO.pdo_type:
        # Set default values (n.b. there are none for v and i)
        dual_role_pwr = False
        usb_suspend = False
        unconstrained_pwr = False
        usb_comms = False
        dual_role_data = False
        unchunked_ext_msg = False
        peak_i = 0

        # Load a SrcFixedPDO
        for line in text[1:]:
            fields = line.split(b":")
            fields[0] = fields[0].strip()
            fields[1] = fields[1].strip()
            if fields[0] == b"dual_role_pwr":
                dual_role_pwr = (fields[1] == b"1")
            elif fields[0] == b"usb_suspend":
                usb_suspend = (fields[1] == b"1")
            elif fields[0] == b"unconstrained_pwr":
                unconstrained_pwr = (fields[1] == b"1")
            elif fields[0] == b"usb_comms":
                usb_comms = (fields[1] == b"1")
            elif fields[0] == b"dual_role_data":
                dual_role_data = (fields[1] == b"1")
            elif fields[0] == b"unchunked_ext_msg":
                unchunked_ext_msg = (fields[1] == b"1")
            elif fields[0] == b"peak_i":
                peak_i = int(fields[1])
            elif fields[0] == b"v":
                v = round(1000*float(fields[1].split()[0]))
            elif fields[0] == b"i":
                i = round(1000*float(fields[1].split()[0]))

        # Make the SrcFixedPDO
        return SrcFixedPDO(
                dual_role_pwr=dual_role_pwr,
                usb_suspend=usb_suspend,
                unconstrained_pwr=unconstrained_pwr,
                usb_comms=usb_comms,
                dual_role_data=dual_role_data,
                unchunked_ext_msg=unchunked_ext_msg,
                peak_i=peak_i,
                v=v,
                i=i)
    elif pdo_type == SrcPPSAPDO.pdo_type:
        # Load a SrcPPSAPDO
        for line in text[1:]:
            fields = line.split(b":")
            fields[0] = fields[0].strip()
            fields[1] = fields[1].strip()
            if fields[0] == b"vmin":
                vmin = round(1000*float(fields[1].split()[0]))
            if fields[0] == b"vmax":
                vmax = round(1000*float(fields[1].split()[0]))
            if fields[0] == b"i":
                i = round(1000*float(fields[1].split()[0]))

        # Make the SrcPPSAPDO
        return SrcPPSAPDO(vmin=vmin, vmax=vmax, i=i)
    elif pdo_type == TypeCVirtualPDO.pdo_type:
        # Load a TypeCVirtualPDO
        for line in text[1:]:
            fields = line.split(b":")
            fields[0] = fields[0].strip()
            fields[1] = fields[1].strip()
            if fields[0] == b"i":
                i = round(1000*float(fields[1].split()[0]))

        # Make the TypeCVirtualPDO
        return TypeCVirtualPDO(i=i)
    elif pdo_type == "No Source_Capabilities":
        return None
    else:
        # Make an UnknownPDO
        return UnknownPDO(value=int(pdo_type, 16))


def read_pdo_list(text):
    """Create a list of PDOs from text returned by Sink.send_command"""
    # Get the lines where PDOs start
    pdo_start_list = []
    for index, line in enumerate(text):
        if not line.startswith(b"\t"):
            pdo_start_list.append(index)
    # Append the number of lines so the last slice will work right
    pdo_start_list.append(len(text))

    # Read the PDOs
    pdo_list = []
    for start, end in zip(pdo_start_list[:-1], pdo_start_list[1:]):
        pdo = read_pdo(text[start:end])
        if pdo is not None:
            pdo_list.append(pdo)

    return pdo_list


def calculate_pdp(pdo_list):
    """Calculate the PDP in watts of a list of PDOs

    The result is only guaranteed to be correct if the power supply follows
    the USB Power Delivery standard.  Since quite a few power supplies
    unfortunately do not, this can really only be considered an estimate.
    """
    max_power = 0

    # The Source Power Rules make it so the PDP can be determined by the
    # highest power available from any fixed supply PDO.
    for pdo in pdo_list:
        if pdo.pdo_type == "fixed":
            max_power = max(max_power, pdo.v / 1000.0 * pdo.i / 1000.0)
        elif pdo.pdo_type == "typec_virtual":
            max_power = max(max_power, 5.0 * pdo.i / 1000.0)

    return max_power


def follows_power_rules(pdo_list):
    """Test whether a list of PDOs follows the Power Rules for PD 3.0

    This function is a false-biased approximation; that is, when it returns
    False it is definitely correct, but when it returns True it might be
    incorrect.
    """
    # First, estimate the PDP assuming the rules are being followed
    pdp = calculate_pdp(pdo_list)

    # If there's a typec_virtual PDO, there's no Power Delivery so the Power
    # Rules cannot be violated.  In truth they're not really being followed
    # either since they only apply to Power Delivery, but returning True here
    # seems like the safer option.
    if pdo_list and pdo_list[0].pdo_type == "typec_virtual":
        return True

    fixed = [p for p in pdo_list if p.pdo_type == "fixed"]
    pps = [p for p in pdo_list if p.pdo_type == "pps"]

    # Make sure nothing exceeds the PDP
    for pdo in fixed:
        if pdp < pdo.v / 1000.0 * pdo.i / 1000.0:
            return False
    # TODO: in the future, there will be more types of PDO checked here
    for pdo in pps:
        # 5V Prog nominal PDO
        if pdo.vmin == 3000 and pdo.vmax == 5900:
            if pdp < 5.0 * pdo.i / 1000.0:
                return False
        # 9V Prog nominal PDO
        elif pdo.vmin == 3000 and pdo.vmax == 11000:
            if pdp < 9.0 * pdo.i / 1000.0:
                return False
        # 15V Prog nominal PDO
        elif pdo.vmin == 3000 and pdo.vmax == 16000:
            if pdp < 15.0 * pdo.i / 1000.0:
                return False
        # 20V Prog nominal PDO
        elif pdo.vmin == 3000 and pdo.vmax == 21000:
            if pdp < 20.0 * pdo.i / 1000.0:
                return False
        # Non-standard programmable PDO
        else:
            if pdp < pdo.vmax / 1000.0 * pdo.i / 1000.0:
                return False

    # Check that the fixed supply PDOs look right
    seen_5v = False
    seen_9v = False
    seen_15v = False
    seen_20v = False
    seen_normative_voltages = False
    if pdp == 0:
        # No power is fine
        seen_normative_voltages = True
    elif pdp <= 15:
        # Below 15 W, make sure the PDP is available at 5 V.
        for pdo in fixed:
            if pdo.v == 5000:
                seen_5v = True
                if pdo.v / 1000.0 * pdo.i / 1000.0 != pdp:
                    return False
        seen_normative_voltages = seen_5v
    elif pdp <= 27:
        # Between 15 and 27 W, make sure at least 3 A is available at 5 V and
        # the PDP is available at 9 V.
        for pdo in fixed:
            if pdo.v == 5000:
                seen_5v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.v == 9000:
                seen_9v = True
                if pdo.v / 1000.0 * pdo.i / 1000.0 != pdp:
                    return False
        seen_normative_voltages = seen_5v and seen_9v
    elif pdp <= 45:
        # Between 27 and 45 W, make sure at least 3 A is available at 5 and
        # 9 V, and the PDP is available at 15 V.
        for pdo in fixed:
            if pdo.v == 5000:
                seen_5v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.v == 9000:
                seen_9v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.v == 15000:
                seen_15v = True
                if pdo.v / 1000.0 * pdo.i / 1000.0 != pdp:
                    return False
        seen_normative_voltages = seen_5v and seen_9v and seen_15v
    else:
        # Above 45 W, make sure at least 3 A is available at 5, 9, and 15 V,
        # and the PDP is available at 20 V.
        for pdo in fixed:
            if pdo.v == 5000:
                seen_5v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.v == 9000:
                seen_9v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.v == 15000:
                seen_15v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.v == 20000:
                seen_20v = True
                if pdo.v / 1000.0 * pdo.i / 1000.0 != pdp:
                    return False
        seen_normative_voltages = seen_5v and seen_9v and seen_15v and seen_20v

    if not seen_normative_voltages:
        return False

    # TODO: there are several things this currently doesn't test, such as
    # variable and battery PDOs.

    # Check that the PPS APDOs look right
    seen_5v = False
    seen_9v = False
    seen_15v = False
    seen_20v = False

    if pdp == 0:
        # No power is fine
        pass
    elif pdp <= 15:
        # Below 15 W, make sure the PDP is available with 5V Prog.
        for pdo in pps:
            if pdo.vmin == 3000 and pdo.vmax == 5900:
                seen_5v = True
                if 5.0 * pdo.i / 1000.0 != pdp:
                    return False
        if pps and not seen_5v:
            return False
    elif pdp <= 27:
        # Between 15 and 27 W, make sure at least 3 A is available at 5V Prog
        # and the PDP is available at 9V Prog.
        for pdo in pps:
            if pdo.vmin == 3000 and pdo.vmax == 5900:
                seen_5v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.vmin == 3000 and pdo.vmax == 11000:
                seen_9v = True
                if 9.0 * pdo.i / 1000.0 != pdp:
                    return False
                # If we're at full power for this range, 5V Prog is optional
                if pdp == 27:
                    seen_5v = True
        if pps and not (seen_5v and seen_9v):
            return False
    elif pdp <= 45:
        # Between 27 and 45 W, make sure at least 3 A is available at 9V Prog,
        # and the PDP is available at 15V Prog.
        for pdo in pps:
            # 5V Prog is optional at this power level
            if pdo.vmin == 3000 and pdo.vmax == 11000:
                seen_9v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.vmin == 3000 and pdo.vmax == 16000:
                seen_15v = True
                if 15.0 * pdo.i / 1000.0 != pdp:
                    return False
                # If we're at full power for this range, 9V Prog is optional
                if pdp == 45:
                    seen_9v = True
        if pps and not (seen_9v and seen_15v):
            return False
    else:
        # Above 45 W, make sure at least 3 A is available at 15V Prog, and the
        # PDP is available at 20V Prog.
        for pdo in pps:
            # 5V and 9V Prog are optional at this power level
            if pdo.vmin == 3000 and pdo.vmax == 16000:
                seen_15v = True
                if pdo.i < 3000.0:
                    return False
            elif pdo.vmin == 3000 and pdo.vmax == 21000:
                seen_20v = True
                if 20.0 * pdo.i / 1000.0 != pdp:
                    return False
                # If we have at least 60 W, 15V Prog is optional
                if pdp >= 60:
                    seen_15v = True
        if pps and not (seen_15v and seen_20v):
            return False

    return True
