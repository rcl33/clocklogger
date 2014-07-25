import unittest
from mock import patch, MagicMock
from clocklogger.source.weather import WeatherStationDataSource


class TestWeatherStationDataSource(unittest.TestCase):
    def _make_source(self, return_value, *args, **kwargs):
        station = MagicMock()
        station.return_value.genLoopPackets.return_value = iter([return_value])
        with patch('clocklogger.source.weather._get_driver_class',
                   lambda: station):
            source = WeatherStationDataSource(*args, **kwargs)
        return source

    def test_it_gets_measurements(self):
        measurements = {'temperature': 1.0, 'pressure': 3.2, 'humidity': 93}
        source = self._make_source(measurements)
        result = source.get_measurements()
        self.assertEqual(result, measurements)

    def test_it_only_returns_requested_fields(self):
        measurements = {'temperature': 1.0, 'pressure': 3.2, 'humidity': 93}
        source = self._make_source(measurements,
                                   fields=['temperature', 'humidity'])
        result = source.get_measurements()
        self.assertEqual(result, {'temperature': 1.0, 'humidity': 93})

if __name__ == '__main__':
    unittest.main()
