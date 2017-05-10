"""Unit tests for the top-level pdbuddy classes"""

import unittest

import pdbuddy


class SinkConfigTestCase(unittest.TestCase):

    def setUp(self):
        self.obj_none = pdbuddy.SinkConfig()
        self.obj_empty = pdbuddy.SinkConfig(status=pdbuddy.SinkStatus.EMPTY)
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

    def test_eq_none(self):
        self.assertTrue(self.obj_none == pdbuddy.SinkConfig())

    def test_eq_valid(self):
        # Set invalid object as valid
        self.obj_invalid.status = pdbuddy.SinkStatus.VALID

        self.assertTrue(self.obj_valid == self.obj_invalid)

    def test_eq_wrong_type(self):
        self.assertFalse(self.obj_none == "hello world")

    def test_eq_wrong_status(self):
        self.assertFalse(self.obj_valid == self.obj_invalid)

    def test_eq_wrong_flags(self):
        self.assertFalse(self.obj_valid == self.obj_valid_gb)

    def test_eq_wrong_voltage(self):
        self.assertFalse(self.obj_valid == self.obj_valid_5v)

    def test_eq_wrong_current(self):
        self.assertFalse(self.obj_valid == self.obj_valid_1a)

    def test_ne_none(self):
        self.assertFalse(self.obj_none != pdbuddy.SinkConfig())

    def test_ne_valid(self):
        # Set invalid object as valid
        self.obj_invalid.status = pdbuddy.SinkStatus.VALID

        self.assertFalse(self.obj_valid != self.obj_invalid)

    def test_ne_wrong_type(self):
        self.assertTrue(self.obj_none != "hello world")

    def test_ne_wrong_status(self):
        self.assertTrue(self.obj_valid != self.obj_invalid)

    def test_hash_identical(self):
        self.assertEqual(hash(self.obj_none), hash(pdbuddy.SinkConfig()))

    def test_hash_different(self):
        self.assertNotEqual(hash(self.obj_none), hash(self.obj_valid))

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