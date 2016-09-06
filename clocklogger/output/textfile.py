import os
import os.path
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)


def datetime_to_epoch(d):
    return int((d - datetime(1970, 1, 1)).total_seconds())


class TextFileWriter(object):
    def __init__(self, path, prefix, columns=None):
        self.path = path
        self.columns = columns
        self.pattern = "%Y/%m/{}%Y-%m-%d.txt".format(prefix)
        self.file = None

    def __del__(self):
        if self.file is not None:
            self.file.close()

    def write(self, data):
        cols = self.columns or sorted(data)
        formats = {
            np.float64: '%.6f',
            float: '%.6f',
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
            logger.info("Opened %s file %s",
                        "existing" if file_already_existed else "new",
                        fn)
        self.file.write(" ".join(formats.get(type(data[k]), "%s") %
                                  data[k] for k in cols) + "\n")
        self.file.flush()
