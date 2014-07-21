from __future__ import print_function, absolute_import

import os
import os.path
from tempodb.client import Client
from tempodb.protocol import DataPoint


class TempoDBWriter(object):
    DATABASE_ID = "clock"

    def __init__(self, columns):
        try:
            api_key = os.environ['TEMPODB_API_KEY']
            api_sec = os.environ['TEMPODB_API_SECRET']
        except KeyError:
            raise RuntimeError("You must define environment variables "
                               "TEMPODB_API_KEY and TEMPODB_API_SECRET")

        self.columns = columns
        self.client = Client(self.DATABASE_ID, api_key, api_sec)

    def write(self, data):
        t = data['time']
        print(data)
        points = [DataPoint.from_data(t, float(data[k]), key='clock.%s' % k)
                  for k in self.columns if k != 'time']
        resp = self.client.write_multi(points)
        if resp.status != 200:
            raise Exception("TempoDB error [%d] %s" %
                            (resp.status, resp.error))
