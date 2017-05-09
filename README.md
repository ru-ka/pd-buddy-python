# pd-buddy-python

Python library for working with the PD Buddy Sink Serial Console Configuration
Interface

## Features

* Provides a Pythonic interface to the PD Buddy Sink shell commands
* Configuration is represented as a SinkConfig object
* SinkConfig objects can be manipulated locally and written to the device with
  one method call

## Examples

### Open the first PD Buddy Sink device and read its configuration

    >>> import pdbuddy
    >>> pdbs = pdbuddy.Sink(list(pdbuddy.Sink.get_devices())[0])
    >>> pdbs.get_cfg()
    SinkConfig(status=SinkStatus.VALID, flags=SinkFlags.NONE, v=5000, i=3000)

### Locally manipulate a SinkConfig object

    >>> cfg = pdbs.get_cfg()
    >>> cfg.v = 20000
    >>> cfg.i = 2250
    >>> cfg.flags |= pdbuddy.SinkFlags.GIVEBACK
    >>> cfg
    SinkConfig(status=SinkStatus.VALID, flags=SinkFlags.GIVEBACK, v=20000, i=2250)

### Write the SinkConfig object to flash

    >>> pdbs.set_tmpcfg(cfg)
    >>> pdbs.write()
    >>> pdbs.get_cfg()
    SinkConfig(status=SinkStatus.VALID, flags=SinkFlags.GIVEBACK, v=20000, i=2250)

## Requirements

* Python >= 3.4 should work (tested with 3.6)
* pySerial (tested with 3.3)
