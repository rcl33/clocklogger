import time
from datetime import datetime
from source.weather import WeatherStationDataSource
from output.textfile import TextFileWriter
from output.influxdb import InfluxDBWriter
from output.tempodb import TempoDBWriter


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
            print "Writer error [%s]: %s" % (writer.__class__, e)


def sleep_til_next_time(interval):
    now = time.time()
    time.sleep(interval - (now % interval))


def main():
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
            print "Error creating %s: %s" % (cls, err)
    add_writer(TextFileWriter, 'data', 'weather', columns)
    add_writer(InfluxDBWriter, 'weather', columns)
    add_writer(TempoDBWriter, 'weather', columns)

    # Read data & output
    while True:
        process(source, writers)
        sleep_til_next_time(interval)


if __name__ == "__main__":
    main()
