
def _filter_fields(d, fields):
    """Filter field names in dictionary"""
    return dict([item for item in d.items() if item[0] in fields])


def _get_driver_class():
    try:
        from weewx.drivers.ws23xx import WS23xx
        return WS23xx
    except ImportError:
        raise ImportError("WS23xx driver not available")


class WeatherStationDataSource(object):
    def __init__(self, fields=None):
        """Read weather data from weather station"""
        # Fill out required config information
        config = {
            'StdArchive': {
                'record_generation': 'hardware'
            }
        }
        driver_class = _get_driver_class()
        self.driver = driver_class(altitude=0.0, config_dict=config)
        self.fields = fields

    def get_measurements(self):
        for packet in self.driver.genLoopPackets():
            if self.fields is not None:
                packet = _filter_fields(packet, self.fields)
            return packet

