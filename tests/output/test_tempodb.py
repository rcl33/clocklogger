import unittest
import mock
from mock import patch
from collections import namedtuple
import os
from datetime import datetime

import clocklogger.output.tempodb
from clocklogger.output.tempodb import TempoDBWriter


MockResponse = namedtuple('MockResponse', ['status', 'error'])


class TempoDBWriterTestCase(unittest.TestCase):
    def _make_writer(self, columns=[]):
        with patch.dict(os.environ,
                        TEMPODB_API_KEY='<<key>>',
                        TEMPODB_API_SECRET='<<secret>>'):
            with patch('clocklogger.output.tempodb.Client') as c:
                writer = TempoDBWriter(columns)
            c.assert_called_once_with('clock', '<<key>>', '<<secret>>')
        return writer

    def test_raises_error_if_secrets_not_specified(self):
        with self.assertRaises(RuntimeError):
            writer = TempoDBWriter([])

    def test_secrets_are_read_from_environ(self):
        DATABASE_ID = 'clock'
        writer = self._make_writer()

    def test_write_method(self):
        writer = self._make_writer(['a', 'b'])
        writer.client.write_multi.return_value = MockResponse(200, 'ok')
        data = {'time': datetime.now(), 'a': 2.3, 'b': 4.3, 'c': 3.4}
        writer.write(data)

        # Compare datapoints, ignoring ordering
        args, kwargs = writer.client.write_multi.call_args
        self.assertEqual(set([point.t for point in args[0]]),
                         set([data['time'], data['time']]))
        self.assertEqual(set([point.v for point in args[0]]),
                         set([data['a'], data['b']]))
        self.assertEqual(set([point.key for point in args[0]]),
                         set(['clock.a', 'clock.b']))

    def test_write_method_raises_exception_on_error(self):
        writer = self._make_writer(['a', 'b'])
        writer.client.write_multi.return_value = MockResponse(404, 'not ok')
        data = {'time': datetime.now(), 'a': 2.3, 'b': 4.3, 'c': 3.4}

        self.assertRaises(Exception, writer.write, data)
