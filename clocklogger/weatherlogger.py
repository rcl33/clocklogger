import time
import argparse
import logging
from datetime import datetime
from .source.weather import WeatherStationDataSource
from .output.textfile import TextFileWriter
from .output.influxdb import InfluxDBWriter
from .output.tempodb import TempoDBWriter

logger = logging.getLogger(__name__)


def round_time_to_interval(t, interval):
    return t.replace(second=int(t.second//interval)*interval,
                     microsecond=0)


def process(source, writers):
    data = source.get_measurements()
    data['time'] = round_time_to_interval(datetime.utcnow(), 30)  # TODO: interval
    for writer in writers:
        try:
            writer.write(data)
        except Exception as e:
            logger.error("Writer error [%s]: %s", writer.__class__, e)


def sleep_til_next_time(interval):
    now = time.time()
    time.sleep(interval - (now % interval))


def main():
    # Set up logging
    parser = argparse.ArgumentParser(description='weatherlogger')
    parser.add_argument('-L', '--log-level', default='warning')
    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log_level)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s")

    fields = ['inTemp', 'inHumidity', 'pressure']
    source = WeatherStationDataSource(fields)
    interval = 30.0  # seconds

    # Outputs
    columns = ['time'] + fields

    # TODO: should do this in a more flexible way
    writers = []
    def add_writer(cls, *args):
        try:
            writers.append(cls(*args))
        except Exception as err:
            logger.error("Error creating %s: %s", cls, err)
    add_writer(TextFileWriter, 'data', 'weather', columns)
    #add_writer(InfluxDBWriter, 'weather', columns)
    #add_writer(TempoDBWriter, 'weather', columns)

    # Read data & output
    while True:
        process(source, writers)
        sleep_til_next_time(interval)


if __name__ == "__main__":
    main()
