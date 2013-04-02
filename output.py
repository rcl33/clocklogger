import os, os.path
import numpy as np

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
        fn = os.path.join(self.path, time.strftime(self.pattern))
        if self.file is None or self.file.name != fn:
            if self.file is not None: self.file.close()
            if not os.path.exists(os.path.dirname(fn)):
                os.makedirs(os.path.dirname(fn))
            file_already_existed = os.path.exists(fn)
            self.file = open(fn, 'wt')
            if not file_already_existed:
                self.file.write("\t".join(cols) + "\n")
        print repr(type(data[cols[1]]))
        self.file.write("\t".join(formats.get(type(data[k]), "%s") %
                                  data[k] for k in cols) + "\n")
        self.file.flush()
