"""Unit tests for the top-level pdbuddy classes"""

import unittest

import pdbuddy


class SinkTestCase(unittest.TestCase):

    def setUp(self):
        # Get devices
        pdbs_devices = list(pdbuddy.Sink.get_devices())
        # If there are no devices, skip the test
        if len(pdbs_devices) == 0:
            self.skipTest("No PD Buddy Sink devices found")
        # Open the first device
        self.pdbs = pdbuddy.Sink(pdbs_devices[0])

        self.obj_valid = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=15000, i=3000)
        self.obj_valid_gb = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.GIVEBACK, v=15000, i=3000)

        self.obj_huge_v = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=65536, i=1000)
        self.obj_big_v = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=20001, i=1000)
        self.obj_neg_v = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=-1, i=1000)

        self.obj_huge_i = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=5000, i=65536)
        self.obj_big_i = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=5000, i=5001)
        self.obj_neg_i = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=5000, i=-1)

    def tearDown(self):
        # Close the connection to the PD Buddy Sink
        self.pdbs.close()

    def test_identify(self):
        self.pdbs.identify()

    def test_help(self):
        help_text = self.pdbs.help()
        self.assertTrue(len(help_text) > 0)
        self.assertTrue(len(help_text[0]) > 0)

    def test_license(self):
        license_text = self.pdbs.license()
        self.assertTrue(len(license_text) > 0)
        self.assertTrue(len(license_text[0]) > 0)

    def test_set_tmpcfg_valid(self):
        self.pdbs.set_tmpcfg(self.obj_valid)
        self.assertEqual(self.pdbs.get_tmpcfg(), self.obj_valid)

    def test_set_tmpcfg_valid_gb(self):
        self.pdbs.set_tmpcfg(self.obj_valid_gb)
        self.assertEqual(self.pdbs.get_tmpcfg(), self.obj_valid_gb)

    def test_set_tmpcfg_huge_v(self):
        with self.assertRaises(ValueError):
            self.pdbs.set_tmpcfg(self.obj_huge_v)

    def test_set_tmpcfg_big_v(self):
        with self.assertRaises(ValueError):
            self.pdbs.set_tmpcfg(self.obj_big_v)

    def test_set_tmpcfg_neg_v(self):
        with self.assertRaises(ValueError):
            self.pdbs.set_tmpcfg(self.obj_neg_v)

    def test_set_tmpcfg_huge_i(self):
        with self.assertRaises(ValueError):
            self.pdbs.set_tmpcfg(self.obj_huge_i)

    def test_set_tmpcfg_big_i(self):
        with self.assertRaises(ValueError):
            self.pdbs.set_tmpcfg(self.obj_big_i)

    def test_set_tmpcfg_neg_i(self):
        with self.assertRaises(ValueError):
            self.pdbs.set_tmpcfg(self.obj_neg_i)

    def test_write(self):
        self.test_set_tmpcfg_valid()
        self.pdbs.write()
        self.assertEqual(self.pdbs.get_cfg(), self.obj_valid)

    def test_get_cfg_index(self):
        self.assertIsInstance(self.pdbs.get_cfg(0), pdbuddy.SinkConfig)

    def test_get_cfg_index_bad(self):
        with self.assertRaises(IndexError):
            self.pdbs.get_cfg(-1)

    def test_load(self):
        # Write obj_valid to flash
        self.test_write()
        # Write obj_valid_gb to tmpcfg
        self.test_set_tmpcfg_valid_gb()

        self.assertNotEqual(self.pdbs.get_cfg(), self.pdbs.get_tmpcfg())

        # Load flash to tmpcfg
        self.pdbs.load()

        self.assertEqual(self.pdbs.get_cfg(), self.pdbs.get_tmpcfg())

    def test_erase(self):
        self.pdbs.erase()
        with self.assertRaises(KeyError):
            self.pdbs.load()

    def test_context_manager(self):
        self.pdbs.close()
        with pdbuddy.Sink(list(pdbuddy.Sink.get_devices())[0]) as pdbs:
            # Test something with the conext manager.  For example, this is
            # essentially test_get_cfg_index.
            self.assertIsInstance(pdbs.get_cfg(0), pdbuddy.SinkConfig)

    def test_output(self):
        try:
            self.pdbs.output = False
            self.assertFalse(self.pdbs.output)

            self.pdbs.output = True
            self.assertTrue(self.pdbs.output)
        except KeyError:
            self.skipTest("Command output not supported")
        except ValueError:
            self.skipTest("Unknown value returned by PD Buddy Sink")

    def test_get_source_cap(self):
        self.assertIsInstance(self.pdbs.get_source_cap(), list)

    def test_send_command_invalid(self):
        with self.assertRaises(KeyError):
            self.pdbs.send_command("foo bar")


class SinkConfigTestCase(unittest.TestCase):

    def setUp(self):
        self.obj_none = pdbuddy.SinkConfig(status=None, flags=None, v=None,
                i=None)
        self.obj_empty = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.EMPTY,
                flags=None, v=None, i=None)
        self.obj_valid = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=15000, i=3000)
        self.obj_invalid = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.INVALID,
                flags=pdbuddy.SinkFlags.NONE, v=15000, i=3000)
        self.obj_valid_gb = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.GIVEBACK, v=15000, i=3000)
        self.obj_valid_5v = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=5000, i=3000)
        self.obj_valid_1a = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.VALID,
                flags=pdbuddy.SinkFlags.NONE, v=15000, i=1000)

    def test_str_none(self):
        self.assertEqual(str(self.obj_none), "No configuration")

    def test_str_empty(self):
        self.assertEqual(str(self.obj_empty), "status: empty")

    def test_str_valid(self):
        self.assertEqual(str(self.obj_valid),
                "status: valid\nflags: (none)\nv: 15.00 V\ni: 3.00 A")

    def test_str_invalid(self):
        self.assertEqual(str(self.obj_invalid),
                "status: invalid\nflags: (none)\nv: 15.00 V\ni: 3.00 A")

    def test_str_valid_gb(self):
        self.assertEqual(str(self.obj_valid_gb),
                "status: valid\nflags: GiveBack\nv: 15.00 V\ni: 3.00 A")

    def test_str_valid_5v(self):
        self.assertEqual(str(self.obj_valid_5v),
                "status: valid\nflags: (none)\nv: 5.00 V\ni: 3.00 A")

    def test_str_valid_1a(self):
        self.assertEqual(str(self.obj_valid_1a),
                "status: valid\nflags: (none)\nv: 15.00 V\ni: 1.00 A")

    def test_from_text_none(self):
        ft_none = pdbuddy.SinkConfig.from_text([])
        self.assertEqual(ft_none, self.obj_none)

    def test_from_text_empty(self):
        ft_empty = pdbuddy.SinkConfig.from_text([b"status: empty"])
        self.assertEqual(ft_empty, self.obj_empty)

    def test_from_text_valid(self):
        ft_valid = pdbuddy.SinkConfig.from_text([b"status: valid",
                b"flags: (none)",
                b"v: 15.00 V",
                b"i: 3.00 A"])
        self.assertEqual(ft_valid, self.obj_valid)

    def test_from_text_invalid(self):
        ft_invalid = pdbuddy.SinkConfig.from_text([b"status: invalid",
                b"flags: (none)",
                b"v: 15.00 V",
                b"i: 3.00 A"])
        self.assertEqual(ft_invalid, self.obj_invalid)

    def test_from_text_valid_gb(self):
        ft_valid_gb = pdbuddy.SinkConfig.from_text([b"status: valid",
                b"flags: GiveBack",
                b"v: 15.00 V",
                b"i: 3.00 A"])
        self.assertEqual(ft_valid_gb, self.obj_valid_gb)

    def test_from_text_valid_5v(self):
        ft_valid_5v = pdbuddy.SinkConfig.from_text([b"status: valid",
                b"flags: (none)",
                b"v: 5.00 V",
                b"i: 3.00 A"])
        self.assertEqual(ft_valid_5v, self.obj_valid_5v)

    def test_from_text_valid_1a(self):
        ft_valid_1a = pdbuddy.SinkConfig.from_text([b"status: valid",
                b"flags: (none)",
                b"v: 15.00 V",
                b"i: 1.00 A"])
        self.assertEqual(ft_valid_1a, self.obj_valid_1a)

    def test_from_text_invalid_index(self):
        with self.assertRaises(IndexError):
            pdbuddy.SinkConfig.from_text([b"Invalid index"])

    def test_from_text_no_configuration(self):
        ft_no_config = pdbuddy.SinkConfig.from_text([b"No configuration"])
        self.assertEqual(ft_no_config, self.obj_none)

    def test_from_text_valid_extra(self):
        ft_valid = pdbuddy.SinkConfig.from_text([b"status: valid",
                b"flags: (none)",
                b"This is an extra line, which shouldn't hurt anything.",
                b"v: 15.00 V",
                b"i: 3.00 A"])
        self.assertEqual(ft_valid, self.obj_valid)


class UnknownPDOTestCase(unittest.TestCase):

    def setUp(self):
        self.obj_zero = pdbuddy.UnknownPDO(value=0x00000000)
        self.obj_notzero = pdbuddy.UnknownPDO(value=0xFFFFFFFF)

    def test_str_zero(self):
        self.assertEqual(str(self.obj_zero), "00000000")

    def test_str_notzero(self):
        self.assertEqual(str(self.obj_notzero), "FFFFFFFF")


class SrcFixedPDOTestCase(unittest.TestCase):

    def setUp(self):
        self.obj_everything = pdbuddy.SrcFixedPDO(True, True, True, True, True,
                3, 20000, 5000)
        self.obj_minimal = pdbuddy.SrcFixedPDO(False, False, False, False,
                False, 0, 5000, 1500)

    def test_str_everything(self):
        self.assertEqual(str(self.obj_everything),
                "fixed\n\tdual_role_pwr: 1\n\tusb_suspend: 1\n"
                "\tunconstrained_pwr: 1\n\tusb_comms: 1\n\tdual_role_data: 1\n"
                "\tpeak_i: 3\n\tv: 20.00 V\n\ti: 5.00 A")

    def test_str_minimal(self):
        self.assertEqual(str(self.obj_minimal),
                "fixed\n\tv: 5.00 V\n\ti: 1.50 A")


class ReadPDOTestCase(unittest.TestCase):

    def setUp(self):
        self.src_fixed_everything = pdbuddy.SrcFixedPDO(True, True, True, True,
                True, 3, 20000, 5000)
        self.src_fixed_minimal = pdbuddy.SrcFixedPDO(False, False, False,
                False, False, 0, 5000, 1500)
        self.unknown_zero = pdbuddy.UnknownPDO(value=0x00000000)
        self.unknown_notzero = pdbuddy.UnknownPDO(value=0xFFFFFFFF)

    def test_read_src_fixed_everything(self):
        rp_src_fixed_everything = pdbuddy.read_pdo([b"PDO 1: fixed",
                b"\tdual_role_pwr: 1",
                b"\tusb_suspend: 1",
                b"\tunconstrained_pwr: 1",
                b"\tusb_comms: 1",
                b"\tdual_role_data: 1",
                b"\tpeak_i: 3",
                b"\tv: 20.00 V",
                b"\ti: 5.00 A"])
        self.assertEqual(self.src_fixed_everything, rp_src_fixed_everything)

    def test_read_src_fixed_minimal(self):
        rp_src_fixed_minimal = pdbuddy.read_pdo([b"PDO 1: fixed",
                b"\tv: 5.00 V",
                b"\ti: 1.50 A"])
        self.assertEqual(self.src_fixed_minimal, rp_src_fixed_minimal)

    def test_read_src_fixed_minimal_no_index(self):
        rp_src_fixed_minimal = pdbuddy.read_pdo([b"fixed",
                b"\tv: 5.00 V",
                b"\ti: 1.50 A"])
        self.assertEqual(self.src_fixed_minimal, rp_src_fixed_minimal)

    def test_read_unknown_zero(self):
        rp_unknown_zero = pdbuddy.read_pdo([b"PDO 1: 00000000"])
        self.assertEqual(self.unknown_zero, rp_unknown_zero)

    def test_read_unknown_notzero(self):
        rp_unknown_notzero = pdbuddy.read_pdo([b"PDO 1: FFFFFFFF"])
        self.assertEqual(self.unknown_notzero, rp_unknown_notzero)


class ReadPDOListTestCase(unittest.TestCase):

    def setUp(self):
        self.src_fixed_everything = pdbuddy.SrcFixedPDO(True, True, True, True,
                True, 3, 20000, 5000)
        self.src_fixed_minimal = pdbuddy.SrcFixedPDO(False, False, False,
                False, False, 0, 5000, 1500)
        self.unknown_zero = pdbuddy.UnknownPDO(value=0x00000000)
        self.unknown_notzero = pdbuddy.UnknownPDO(value=0xFFFFFFFF)

    def test_read_pdo_list(self):
        # It's not a legal list for USB Power Delivery, but it works fine for
        # testing this code
        text = [b"PDO 1: fixed",
                b"\tdual_role_pwr: 1",
                b"\tusb_suspend: 1",
                b"\tunconstrained_pwr: 1",
                b"\tusb_comms: 1",
                b"\tdual_role_data: 1",
                b"\tpeak_i: 3",
                b"\tv: 20.00 V",
                b"\ti: 5.00 A",
                b"PDO 2: fixed",
                b"\tv: 5.00 V",
                b"\ti: 1.50 A",
                b"PDO 3: 00000000",
                b"PDO 4: FFFFFFFF"]
        pdo_list = pdbuddy.read_pdo_list(text)

        self.assertEqual(pdo_list[0], self.src_fixed_everything)
        self.assertEqual(pdo_list[1], self.src_fixed_minimal)
        self.assertEqual(pdo_list[2], self.unknown_zero)
        self.assertEqual(pdo_list[3], self.unknown_notzero)
