import unittest
from mock import patch, mock_open, call, MagicMock
import os
import os.path
from tempfile import mkdtemp
import shutil
from datetime import datetime, timedelta
import numpy as np

from clocklogger.output.textfile import TextFileWriter


class TextFileWriterTestCase(unittest.TestCase):
    def setUp(self):
        self.path = mkdtemp()
        self.writer = TextFileWriter(self.path, ['time', 'a', 'b'])

    def tearDown(self):
        shutil.rmtree(self.path)

    def test_opens_and_closes_file(self):
        data = {'time': datetime(2014, 2, 3, 10, 30, 23),
                'a': 2.3, 'b': 4.3, 'c': 3.4}

        # Check correct filename was opened
        expected_path = os.path.join(self.path, '2014/02/clock-2014-02-03.txt')
        self.assertFalse(os.path.exists(expected_path))
        self.writer.write(data)
        self.assertTrue(os.path.exists(expected_path))
        self.assertFalse(self.writer.file.closed)

        # Check file is closed when writer is deleted
        f = self.writer.file
        del self.writer
        self.assertTrue(f.closed)

    def test_changes_file_at_midnight(self):
        data = {'time': datetime(2014, 2, 3, 23, 59, 0),
                'a': 2.3, 'b': 4.3, 'c': 3.4}

        # First write - old file
        expected1 = os.path.join(self.path, '2014/02/clock-2014-02-03.txt')
        self.assertFalse(os.path.exists(expected1))
        self.writer.write(data)
        self.assertTrue(os.path.exists(expected1))
        self.assertFalse(self.writer.file.closed)

        # Next point - still old file
        data['time'] += timedelta(seconds=30)
        file1 = self.writer.file
        self.writer.write(data)
        self.assertEqual(self.writer.file, file1)

        # Next point - midnight - new file
        data['time'] += timedelta(seconds=30)
        expected2 = os.path.join(self.path, '2014/02/clock-2014-02-04.txt')
        self.assertFalse(os.path.exists(expected2))
        self.writer.write(data)
        self.assertTrue(os.path.exists(expected2))
        self.assertNotEqual(self.writer.file, file1)
        self.assertTrue(file1.closed)
        self.assertFalse(self.writer.file.closed)

        # Next point - still new file
        data['time'] += timedelta(seconds=30)
        file2 = self.writer.file
        self.writer.write(data)
        self.assertEqual(self.writer.file, file2)

    def test_output(self):
        data1 = {'time': datetime(1970, 1, 1, 0, 0, 0),
                 'a': 2.3, 'b': 4.328392012, 'c': 3.4}
        data2 = {'time': datetime(1970, 1, 1, 13, 0, 4),
                 'a': np.float64(4.1), 'b': 302.1, 'c': 0.1}

        # First write - old file
        self.writer.write(data1)
        self.writer.write(data2)

        # Check output is as expected
        expected_output = [
            "time	a	b\n",
            "0	2.300000	4.328392\n",
            "46804	4.100000	302.100000\n"
        ]
        with open(os.path.join(self.path, '1970/01/clock-1970-01-01.txt')) as f:
            self.assertEqual(f.readlines(), expected_output)
