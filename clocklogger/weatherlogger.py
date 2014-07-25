import time

from source.weather import WeatherStationDataSource
from output.textfile import TextFileWriter
from output.tempodb import TempoDBWriter


def process(source, writers):
    for data in source.read():
        for writer in writers:
            try:
                writer.write(data)
            except Exception as e:
                print "Writer error [%s]: %s" % (writer.__class__, e)


def sleep_til_next_time(interval):
    now = time.time()
    time.sleep(interval - (now % interval))


def main():
    fields = ['inTemp', 'pressure', 'inHumidity']
    source = WeatherStationDataSource(fields)
    interval = 30.0  # seconds

    # Outputs
    columns = ['time'] + fields
    writers = [
        TextFileWriter('data', 'weather', columns),
        TempoDBWriter(columns)
    ]

    # Read data & output
    while True:
        process(source, writers)
        sleep_til_next_time(interval)


if __name__ == "__main__":
    main()
