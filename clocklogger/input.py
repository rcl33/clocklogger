from __future__ import division
import numpy as np
from datetime import datetime, timedelta
import pyaudio
import logging

logger = logging.getLogger(__name__)


class PrerecordedDataSource(object):
    CHANNEL_TICK = 0
    CHANNEL_PPS  = 1

    def __init__(self, filename):
        self.filename = filename

        logger.info("Loading pre-recorded data from %s...", filename)
        data = np.load(filename)
        self.fs = data['fs']
        self.y = data['signal']
        self.start_time = datetime.fromtimestamp(data['start_time'])
        self.i = 0

    def get_samples(self, num_samples):
        """Return some samples"""
        if self.i >= self.y.shape[0]:
            raise EOFError
        samples = self.y[self.i : (self.i + num_samples)]
        return samples

    def consume(self, num_samples):
        """Mark num_samples as having been used"""
        self.i += num_samples

    @property
    def time(self):
        """Time of first available sample"""
        return self.start_time + timedelta(seconds = self.i / self.fs)

class SoundCardDataSource(object):
    CHANNEL_TICK = 0
    CHANNEL_PPS  = 1

    def __init__(self, sampling_rate=44100):
        self.fs = sampling_rate

        logger.info("Starting PyAudio...")
        self.pyaudio_manager = pyaudio.PyAudio()
        dev = self.pyaudio_manager.get_default_input_device_info()
        if not self.pyaudio_manager.is_format_supported(
                rate=sampling_rate,
                input_device=dev['index'],
                input_channels=2,
                input_format=pyaudio.paInt16):
            raise RuntimeError("Unsupported audio format or rate")

        self.stream = self.pyaudio_manager.open(
            frames_per_buffer=4096,
            format=pyaudio.paInt16, channels=2, rate=sampling_rate, input=True)
        logger.info("PyAudio ready")

        self.buffer = np.empty((0, 2))
        self.buffer_start_time = None

    def __del__(self):
        logger.info("Stopping PyAudio stream")
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio_manager.terminate()

    def read(self, num_samples):
        logger.debug("Trying to read %d samples, %d available...",
                     num_samples, self.stream.get_read_available())
        raw_data = self.stream.read(num_samples)
        samples = (np.frombuffer(raw_data, dtype=np.int16)
                   .reshape((-1, 2))
                   .astype(float)
                   / 2**15)
        logger.debug("Read %d samples, now %d available",
                     samples.shape[0], self.stream.get_read_available())
        return samples

    def get_samples(self, num_samples):
        """Return some samples"""
        num_to_read = num_samples - self.buffer.shape[0]
        if num_to_read > 0:
            new_samples = self.read(num_to_read)
            self.buffer = np.r_[ self.buffer, new_samples ]
            self.buffer_start_time = \
                datetime.utcnow() - timedelta(seconds=self.buffer.shape[0]/self.fs)
        return self.buffer[:num_samples]

    def consume(self, num_samples):
        """Mark num_samples as having been used"""
        num_to_read = num_samples - self.buffer.shape[0]
        if num_to_read > 0:
            self.get_samples(num_to_read)
        assert self.buffer.shape[0] >= num_samples
        self.buffer = self.buffer[num_samples:]

    @property
    def time(self):
        """Time of first available sample"""
        return self.buffer_start_time
