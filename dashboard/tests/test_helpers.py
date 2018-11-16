import unittest
from dashboard.helpers import shorten_node_key, get_natural_size, format_duration
from datetime import timedelta


class TestHelpers(unittest.TestCase):
    def test_shorten_node_key_success(self):
        self.assertEqual(
            '0x1234..abcd',
            shorten_node_key('0x123400000000000000000000000000000000abcd')
        )

    def test_shorten_node_key_incorrect_length(self):
        self.assertEqual(
            '0x',
            shorten_node_key('0x')
        )

    def test_shorten_node_key_none(self):
        self.assertEqual(
            None,
            shorten_node_key(None)
        )

    def test_get_natural_size(self):
        self.assertEqual(
            '1 Byte',
            get_natural_size(1)
        )

        self.assertEqual(
            '1.00 KB',
            get_natural_size(1024)
        )

        self.assertEqual(
            '1.00 MB',
            get_natural_size(1024 * 1024)
        )

        self.assertEqual(
            '1.00 GB',
            get_natural_size(1024 * 1024 * 1024)
        )

    def test_format_duration(self):
        self.assertEqual(
            '< 1 minute',
            format_duration(timedelta(seconds=0))
        )

        self.assertEqual(
            '< 1 minute',
            format_duration(timedelta(seconds=59))
        )

        self.assertEqual(
            '1min',
            format_duration(timedelta(seconds=60))
        )

        self.assertEqual(
            '1hr 0min',
            format_duration(timedelta(minutes=60))
        )

        self.assertEqual(
            '100hr 1min',
            format_duration(timedelta(hours=100, minutes=1))
        )
