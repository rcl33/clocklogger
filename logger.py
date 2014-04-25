import time
from input import PrerecordedDataSource, SoundCardDataSource
from analysis import ClockAnalyser, DataError
from output import TextFileWriter

def main():
    #source = PrerecordedDataSource('../../dataq/record_20130331_0002_100s.npz')
    source = SoundCardDataSource()
    analyser = ClockAnalyser(source, initial_drift=-1)
    writer = TextFileWriter('data', columns=['time', 'drift', 'amplitude'])

    # Read samples, analyze
    while True:
        try:
            for data in analyser.process(pps_edge='down'):
                writer.write(data)
        except DataError as err:
            print "Error: %s" % err
            print "Trying to start again in 3 seconds..."
            time.sleep(3)

if __name__ == "__main__":
    main()
