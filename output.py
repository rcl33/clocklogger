import os, os.path
from datetime import datetime, timedelta
import numpy as np


def datetime_to_epoch(d):
    return int((d - datetime(1970, 1, 1)).total_seconds())


class TextFileWriter(object):
    def __init__(self, path, columns=None):
        self.path = path
        self.columns = columns
        self.pattern = "%Y/%m/clock-%Y-%m-%d.txt"
        self.file = None

    def __del__(self):
        if self.file is not None:
            self.file.close()

    def write(self, data):
        cols = self.columns or sorted(data)
        formats = {
            np.float64: '%.6f',
        }
        time = data['time']
        #data['time'] = data['time'].isoformat()
        data = dict(data)
        data['time'] = datetime_to_epoch(time)
        fn = os.path.join(self.path, time.strftime(self.pattern))
        if self.file is None or self.file.name != fn:
            if self.file is not None: self.file.close()
            if not os.path.exists(os.path.dirname(fn)):
                os.makedirs(os.path.dirname(fn))
            file_already_existed = os.path.exists(fn)
            self.file = open(fn, 'at')
            if not file_already_existed:
                self.file.write("\t".join(cols) + "\n")
            print "Opened %s file %s" % ("existing" if file_already_existed else "new", fn)
        self.file.write("\t".join(formats.get(type(data[k]), "%s") %
                                  data[k] for k in cols) + "\n")
        self.file.flush()


from influxdb import client as influxdb

class InfluxDBWriter(object):
    def __init__(self, columns):
        self.columns = columns
        self.db = influxdb.InfluxDBClient('localhost', 8086, 'clocklogger', 'pendulum', 'clock')
        print "Opened connection to InfluxDB"

    def write(self, data):
        data = dict(data)
        data['time'] = datetime_to_epoch(data['time'])
        points = [
            {
                "name":    "clock",
                "columns": self.columns,
                "points":  [[data[k] for k in self.columns]],
            }
        ]
        self.db.write_points_with_precision(points, 's')


from tempodb.client import Client
from tempodb.protocol import DataPoint
import os

class TempoDBWriter(object):
    DATABASE_ID = "clock"

    def __init__(self, columns):
        try:
            api_key = os.environ['TEMPODB_API_KEY']
            api_sec = os.environ['TEMPODB_API_SECRET']
        except KeyError:
            raise Exception("You must define environment variables "
                            "TEMPODB_API_KEY and TEMPODB_API_SECRET")

        self.columns = columns
        self.client = Client(self.DATABASE_ID, api_key, api_sec)

    def write(self, data):
        t = data['time']
        print data
        points = [DataPoint.from_data(t, float(data[k]), key='clock.%s' % k)
                  for k in self.columns if k != 'time']
        resp = self.client.write_multi(points)
        if resp.status != 200:
            raise Exception("TempoDB error [%d] %s" %
                            (resp.status, resp.error))
