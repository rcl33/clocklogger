import unittest
from mock import Mock, call
import numpy as np
from numpy.testing import assert_allclose
from clocklogger.input import SoundCardDataSource


class TestSoundCardDataSource(unittest.TestCase):
    def _mock_read_func(self, num):
        samples = self._counter * np.ones(2 * num, np.int16)
        samples[0::2] += np.arange(num)
        samples[1::2] += np.arange(num)
        self._counter += num
        return samples

    def setUp(self):
        self._counter = 0
        self.source = SoundCardDataSource()
        self.mock_read = Mock(side_effect=self._mock_read_func)
        self.source.stream.read = self.mock_read

    def test_get_samples_returns_correct_number_of_samples(self):
        N = 1430
        samples = self.source.get_samples(N)
        self.assertEqual(samples.shape, (N, 2))

    def test_same_samples_are_returned_if_not_consumed(self):
        N = 15434
        samples1 = self.source.get_samples(N)

        # Should have requested N samples from the sound card
        self.mock_read.assert_called_once_with(N)

        # Asking for the same number of samples again shouldn't go to
        # the sound card again...
        samples2 = self.source.get_samples(N)
        self.assertEqual(self.mock_read.call_count, 1)

        # ...and the same samples are returned again
        assert_allclose(samples1, samples2)
        self.assertTrue(abs(samples1).max() > 0)

    def test_new_samples_are_returned_if_consumed(self):
        # Request 100 samples. Then say we've used 50, which leaves 50
        # available. Then ask for 200 samples, which should be the 50
        # left-over samples plus 150 new samples.
        samples1 = self.source.get_samples(100)
        self.source.consume(50)
        samples2 = self.source.get_samples(200)

        # Should have requested 100 samples, then 150 samples, from the
        # sound card.
        self.assertEqual(self.mock_read.call_args_list,
                         [call(100), call(150)])

        # First 50 samples of samples2 should be same as last of samples1
        assert_allclose(samples2[:50], samples1[50:])

        # Check values are as expected (rescale for convenience)
        samples1 *= 2**15
        samples2 *= 2**15
        assert_allclose(samples1[:, 0], np.arange(0, 100))
        assert_allclose(samples1[:, 1], np.arange(0, 100))
        assert_allclose(samples2[:, 0], np.arange(50, 250))
        assert_allclose(samples2[:, 1], np.arange(50, 250))

        # Consuming 200 samples should get rid of all of them
        self.source.consume(200)
        self.assertEqual(self.source.buffer.shape, (0, 2))

    def test_consume_can_read_new_samples(self):
        self.source.consume(112)
        self.assertEqual(self.mock_read.call_args_list, [call(112)])


if __name__ == '__main__':
    unittest.main()
