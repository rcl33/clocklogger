import time
from input import PrerecordedDataSource, SoundCardDataSource
from analysis import ClockAnalyser, DataError
from output.textfile import TextFileWriter
from output.influxdb import InfluxDBWriter
from output.tempodb import TempoDBWriter


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
                print "Writer error [%s]: %s" % (writer.__class__, e)
        save_last_drift(data['drift'])


def main():
    #source = PrerecordedDataSource('../../dataq/record_20130331_0002_100s.npz')
    source = SoundCardDataSource()
    analyser = ClockAnalyser(source, initial_drift=get_last_drift())

    # Outputs
    columns = ['time', 'drift', 'amplitude']
    writers = [
        TextFileWriter('data', columns),
        InfluxDBWriter(columns),
        TempoDBWriter(columns)
    ]

    # Read samples, analyze
    while True:
        try:
            process(analyser, writers)
        except DataError as err:
            print "Error: %s" % err
            print "Trying to start again in 3 seconds..."
            time.sleep(3)

if __name__ == "__main__":
    main()
