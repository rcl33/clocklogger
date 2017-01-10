import argparse
import time
import logging
from .input import PrerecordedDataSource, SoundCardDataSource
from .analysis import ClockAnalyser, DataError
from .output.textfile import TextFileWriter
# from .output.influxdb import InfluxDBWriter
# from .output.tempodb import TempoDBWriter

logger = logging.getLogger(__name__)


def get_last_drift():
    try:
        with open('data/last_drift', 'rt') as f:
            last_drift = float(f.read())
    except:
        last_drift = 0.0
    return last_drift


def save_last_drift(drift):
    with open('data/last_drift', 'wt') as f:
        f.write(str(drift))


def process(analyser, writers):
    for data in analyser.process(pps_edge='down'):
        for writer in writers:
            try:
                writer.write(data)
            except Exception as e:
                logger.error("Writer error [%s]: %s", writer.__class__, e)
        save_last_drift(data['drift'])


def main():
    # Set up logging
    parser = argparse.ArgumentParser(description='clocklogger')
    parser.add_argument('-L', '--log-level', default='warning')
    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log_level)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s")

    #source = PrerecordedDataSource('../../dataq/record_20130331_0002_100s.npz')
    source = SoundCardDataSource()
    analyser = ClockAnalyser(source, initial_drift=get_last_drift())

    # Outputs
    columns = ['time', 'drift', 'amplitude']

    # TODO: should do this in a more flexible way
    writers = []
    def add_writer(cls, *args):
        try:
            writers.append(cls(*args))
        except Exception as err:
            logger.error("Error creating %s: %s", cls, err)
    add_writer(TextFileWriter, 'data', 'clock', columns)
    #add_writer(InfluxDBWriter, 'clock', columns)
    #add_writer(TempoDBWriter, 'clock', columns)

    # Read samples, analyze
    while True:
        try:
            process(analyser, writers)
        except DataError as err:
            logger.error("Error: %s. Trying to start again in 3 seconds...",
                         err)
            time.sleep(3)

if __name__ == "__main__":
    main()
