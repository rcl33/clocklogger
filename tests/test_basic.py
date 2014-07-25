import unittest
from clocklogger import logger


class TestLogger(unittest.TestCase):
    def test_it_runs(self):
        self.assertIsNotNone(logger)


if __name__ == '__main__':
    unittest.main()
