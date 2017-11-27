"""Test a freshly-flashed PD Buddy Sink"""

import argparse
import sys

import pdbuddy


class ExitCode:
    configuration_error = 1
    wrong_output = 2


def write_verify(sink, cfg):
    """Write a SinkConfig to a Sink and verify that it was written"""
    sink.set_tmpcfg(cfg)
    sink.write()

    actual_cfg = sink.get_cfg()
    if actual_cfg != cfg:
        print('Configuration error; expected config:')
        print(cfg)
        print('actual config:')
        print(actual_cfg)
        sys.exit(ExitCode.configuration_error)


def output_verify(sink):
    """Verify that the Sink's output is correct"""
    # Get the configured voltage
    voltage = sink.get_cfg().v
    if voltage is None:
        voltage = 0

    answer = input("Is the Sink's output stable at {:.1f} V [Y,n]? ".format(
        voltage/1000. * sink.output))
    if answer.lower().startswith('n'):
        print('Wrong output, exiting.')
        sys.exit(ExitCode.wrong_output)


def main():
    # Make the argument parser
    parser = argparse.ArgumentParser(description='Test a PD Buddy Sink')
    parser.add_argument('tty', metavar='tty', type=str, help="the Sink's tty")

    # Parse arguments
    args = parser.parse_args()

    # Define configurations for testing
    cfg_20v = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
            flags=pdbuddy.SinkFlags.NONE, v=20000, i=1000)
    cfg_9v = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
            flags=pdbuddy.SinkFlags.NONE, v=9000, i=1000)

    # Run the testing procedure
    with pdbuddy.Sink(args.tty) as sink:
        # Make sure output is disabled to start
        sink.output = False

        # Set initial configuration
        print('Writing 20 V configuration object…')
        write_verify(sink, cfg_20v)
        print('Done.')

        # Turn on the output and ensure that it's correct
        sink.output = True
        output_verify(sink)

        # Turn off the output and ensure that it's off
        sink.output = False
        output_verify(sink)

        # Turn on the output again and ensure that it's back at 20 V
        sink.output = True
        output_verify(sink)

        # Set second configuration
        print('Writing 9 V configuration object…')
        write_verify(sink, cfg_9v)
        print('Done.')

        # Ensure that the output is 9 V now
        output_verify(sink)

        # Erase the sink's configuration
        sink.erase()

        # Ensure there's no output despite it being enabled
        sink.output = True
        output_verify(sink)

    # Congratulations, all tests passed!
    print('Test successful!')

if __name__ == '__main__':
    main()
