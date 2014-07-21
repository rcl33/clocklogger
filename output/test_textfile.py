import unittest
from mock import patch, mock_open, call, MagicMock
import os
import os.path
from datetime import datetime, timedelta
import numpy as np

from output.textfile import TextFileWriter


class TextFileWriterTestCase(unittest.TestCase):
    PATH = '/tmp/test/path'

    def test_opens_and_closes_file(self):
        writer = TextFileWriter(self.PATH, ['a', 'b'])
        data = {'time': datetime(2014, 2, 3, 10, 30, 23),
                'a': 2.3, 'b': 4.3, 'c': 3.4}

        # Patch with create=True to overwrite buildin open()
        with patch('output.textfile.open', mock_open(), create=True) as m:
            writer.write(data)

        # Check correct filename was opened
        expected_path = os.path.join(self.PATH, '2014/02/clock-2014-02-03.txt')
        m.assert_called_once_with(expected_path, 'at')

        # Check file is closed when writer is deleted
        f = writer.file
        del writer
        f.close.assert_called_once_with()

    def test_changes_file_at_midnight(self):
        writer = TextFileWriter(self.PATH, ['a', 'b'])
        data = {'time': datetime(2014, 2, 3, 23, 59, 0),
                'a': 2.3, 'b': 4.3, 'c': 3.4}

        # Patch with create=True to overwrite buildin open()
        with patch('output.textfile.open', mock_open(), create=True) as m:
            def save_file_name(fn, *args):
                mock_file = MagicMock()
                mock_file.name = fn
                return mock_file
            m.side_effect = save_file_name

            # First write - old file
            writer.write(data)
            f = writer.file
            expected1 = os.path.join(self.PATH, '2014/02/clock-2014-02-03.txt')
            m.assert_called_once_with(expected1, 'at')

            # Next point - still old file
            data['time'] += timedelta(seconds=30)
            writer.write(data)
            self.assertEqual(m.call_count, 1)
            self.assertEqual(f.close.call_count, 0)

            # Next point - midnight - new file
            data['time'] += timedelta(seconds=30)
            expected2 = os.path.join(self.PATH, '2014/02/clock-2014-02-04.txt')
            writer.write(data)
            self.assertEqual(m.call_count, 2)
            m.assert_has_calls([call(expected1, 'at'),
                                call(expected2, 'at')])
            self.assertEqual(f.close.call_count, 1)

            # Next point - still new file
            data['time'] += timedelta(seconds=30)
            writer.write(data)
            self.assertEqual(m.call_count, 2)
            self.assertEqual(f.close.call_count, 1)

    def test_output(self):
        writer = TextFileWriter(self.PATH, ['time', 'a', 'b'])
        data1 = {'time': datetime(1970, 1, 1, 0, 0, 0),
                 'a': 2.3, 'b': 4.328392012, 'c': 3.4}
        data2 = {'time': datetime(1970, 1, 1, 13, 0, 4),
                 'a': np.float64(4.1), 'b': 302.1, 'c': 0.1}

        # Patch with create=True to overwrite buildin open()
        with patch('output.textfile.open', mock_open(), create=True) as m:
            def save_file_name(fn, *args):
                mock_file = MagicMock()
                mock_file.name = fn
                return mock_file
            m.side_effect = save_file_name

            # First write - old file
            writer.write(data1)
            writer.write(data2)

        # Check output is as expected
        expected_output = [
            "time	a	b\n",
            "0	2.300000	4.328392\n",
            "46804	4.100000	302.100000\n"
        ]
        writer.file.write.assert_has_calls([
            call(line) for line in expected_output
        ])
