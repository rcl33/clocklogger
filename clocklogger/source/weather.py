import logging

logger = logging.getLogger(__name__)


def _filter_fields(d, fields):
    """Filter field names in dictionary"""
    return dict([item for item in d.items() if item[0] in fields])


def _get_driver_class():
    try:
        from weewx.drivers import ws23xx

        # Patch logging functions to use normal logger not syslog
        ws23xx.logdbg = lambda msg: logger.debug("WS23xx: %s", msg)
        ws23xx.loginf = lambda msg: logger.info("WS23xx: %s", msg)
        ws23xx.logerr = lambda msg: logger.error("WS23xx: %s", msg)
        ws23xx.logcrt = lambda msg: logger.critical("WS23xx: %s", msg)

        return ws23xx.WS23xx
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

