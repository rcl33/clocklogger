from __future__ import absolute_import

import os
import os.path
from tempodb.client import Client
from tempodb.protocol import DataPoint
import logging

logger = logging.getLogger(__name__)


class TempoDBWriter(object):
    DATABASE_ID = "clock"

    def __init__(self, base_key, columns):
        try:
            api_key = os.environ['TEMPODB_API_KEY']
            api_sec = os.environ['TEMPODB_API_SECRET']
        except KeyError:
            raise RuntimeError("You must define environment variables "
                               "TEMPODB_API_KEY and TEMPODB_API_SECRET")

        self.base_key = base_key
        self.columns = columns
        self.client = Client(self.DATABASE_ID, api_key, api_sec)

    def write(self, data):
        t = data['time']
        logger.debug("Data: %s", data)
        points = [DataPoint.from_data(t, float(data[k]),
                                      key='%s.%s' % (self.base_key, k))
                  for k in self.columns if k != 'time']
        resp = self.client.write_multi(points)
        if resp.status != 200:
            raise Exception("TempoDB error [%d] %s" %
                            (resp.status, resp.error))
