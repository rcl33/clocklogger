from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from influxdb import client as influxdb
except ImportError:
    influxdb = None


def datetime_to_epoch(d):
    return int((d - datetime(1970, 1, 1)).total_seconds())


class InfluxDBWriter(object):
    def __init__(self, base_key, columns):
        if influxdb is None:
            raise ImportError("Could not import influxdb package")
        self.base_key = base_key
        self.columns = columns
        self.db = influxdb.InfluxDBClient('localhost', 8086,
                                          'clocklogger', 'pendulum', 'clock')
        logger.info("Opened connection to InfluxDB")

    def write(self, data):
        data = dict(data)
        data['time'] = datetime_to_epoch(data['time'])
        points = [
            {
                "name":    "clock",
                "columns": ["%s.%s" % (self.base_key, k) for k in self.columns],
                "points":  [[data[k] for k in self.columns]],
            }
        ]
        self.db.write_points_with_precision(points, 's')
