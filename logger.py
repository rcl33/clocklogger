from input import PrerecordedDataSource, SoundCardDataSource
from analysis import ClockAnalyser
from output import TextFileWriter

def main():
    #source = PrerecordedDataSource('../../dataq/record_20130331_0002_100s.npz')
    source = SoundCardDataSource()
    analyser = ClockAnalyser(source, initial_drift=-1)
    writer = TextFileWriter('data', columns=['time', 'drift', 'amplitude'])

    # Read samples, analyze
    for data in analyser.process(fit_decay=False, pps_edge='down'):
        writer.write(data)

if __name__ == "__main__":
    main()
