from __future__ import division
import numpy as np
from numpy import sin, cos, pi
from datetime import timedelta

PLOT = False
try:
    import matplotlib.pyplot as plt
except ImportError:
    PLOT = False

if PLOT:
    plt.ioff()

PPS_RATE_ERROR_THRESHOLD = 50e-6

class DataError(Exception):
    pass

def round_time_to_three_seconds(t):
    return t.replace(second = (t.second//3)*3, microsecond = 0)

class ClockAnalyser(object):
    def __init__(self, source, initial_drift=0, invert=False):
        self.source = source
        self.drift_offset = initial_drift
        self.invert = invert
        self.last_drift = None
        self.cache = np.empty((0, 2))
        self.cache_start_time = None
        self.pretrigger = 0.2 # seconds
        self.edge_level = 0.2
        self.shim_width = 24.0 # millimetres ~= milliradians (at 1m from pivot)
        self.decay_fit_duration = 0.05  # duration of fit segment (s)
        self.decay_fit_delay = 0.003 # wait after crossing threshold (s)
        self.decay_fit_level = 0.5 # y-value to use as reference point

    def process(self, pps_edge='up', sampling_rate_from_pps=False, fit_decay=False):
        """Read samples from source and yield drift & amplitude values"""

        #pretrigger_samples = self.pretrigger * source.fs
        last_time = None
        for t, (i_pos_pps, i_neg_pps), (i_pos_tick, i_neg_tick) in self.generate_edge_groups(fit_decay=fit_decay):
            i_pps = i_pos_pps if pps_edge == 'up' else i_neg_pps
            self.sanity_check_pps(i_pps)

            # Find first PPS after down tick & calculate drift
            drift_delta = self.calculate_drift(i_pos_tick, i_pps, sampling_rate_from_pps)

            # Calculate amplitude
            amplitude = self.calculate_amplitude(i_pos_tick, i_neg_tick)

            print(("Found ticks: PPS  %5d up, %5d down\n" +
                   "             Tick %5d up, %5d down") \
                 % tuple([len(_) for _ in [i_pos_pps, i_neg_pps, i_pos_tick, i_neg_tick]]))

            # Unwrap phase
            if self.last_drift is None:
                # initial value stored in self.drift_offset
                self.drift_offset = np.round(self.drift_offset - drift_delta)
                self.last_drift = self.drift_offset + drift_delta
            if (self.drift_offset + drift_delta) > (self.last_drift + 0.5):
                self.drift_offset -= 1
                print "(offset -1 sec to %d)" % self.drift_offset
            elif (self.drift_offset + drift_delta) < (self.last_drift - 0.5):
                self.drift_offset += 1
                print "(offset +1 sec to %d)" % self.drift_offset
            self.last_drift = drift = self.drift_offset + drift_delta

            # Make the time be neat; multiple of 3 seconds from midnight
            # Also don't repeat timestamps; if this t is the same as the last,
            # drop this one; if it's 6 seconds in between, fill in the gap
            # This might happen because the chunks are going to beat with the exact 3 seconds
            t = round_time_to_three_seconds(t)
            if last_time is not None:
                if t == last_time:
                    print "------ skipping repeated time %s" % t
                    continue
                if t == last_time + timedelta(seconds=6):
                    print "------------- filling gap before %s" % t
                    yield {"time": t - timedelta(seconds = 3),
                           "drift": drift, "amplitude": amplitude}
            last_time = t
            yield {"time": t, "drift": drift, "amplitude": amplitude}

    def soundcheck(self):
        """Read samples from source and yield drift & amplitude values"""
        while True:
            # Read some samples
            num_samples = 6 * self.source.fs
            try:
                samples = self.source.get_samples(num_samples)
                if self.invert:
                    samples *= -1
                self.source.consume(num_samples)
            except EOFError:
                break

            # Stats
            pps = samples[:, self.source.CHANNEL_PPS]
            tick = samples[:, self.source.CHANNEL_TICK]

            # Analyse to find edges
            i_pos_pps,  i_neg_pps  = self.find_edges(pps)
            i_pos_tick, i_neg_tick = self.find_edges(tick)

            yield {
                'pps': { 'min': pps.min(), 'max': pps.max(), 'npos': len(i_pos_pps), 'nneg': len(i_neg_pps) },
                'tick': { 'min': tick.min(), 'max': tick.max(), 'npos': len(i_pos_tick), 'nneg': len(i_neg_tick) },
            }

    def generate_edge_groups(self, fit_decay=False):
        """Read samples from source, and generate indices of edge groups"""
        while True:
            # Read some samples
            num_samples = 6 * self.source.fs
            try:
                samples = self.source.get_samples(num_samples)
                if self.invert:
                    samples *= -1
            except EOFError:
                break

            # Analyse to find edges
            i_pos_pps,  i_neg_pps  = self.find_edges(samples[:,self.source.CHANNEL_PPS ])
            i_pos_tick, i_neg_tick = self.find_edges(samples[:,self.source.CHANNEL_TICK])

            # Fit decay to improve accuracy if required
            if fit_decay:
                i_pos_pps  = self.fit_decays( samples[:,self.source.CHANNEL_PPS ], i_pos_pps)
                i_neg_pps  = self.fit_decays(-samples[:,self.source.CHANNEL_PPS ], i_neg_pps)
                i_pos_tick = self.fit_decays( samples[:,self.source.CHANNEL_TICK], i_pos_tick)
                i_neg_tick = self.fit_decays(-samples[:,self.source.CHANNEL_TICK], i_neg_tick)

            # Find which is the 'down' tick: the IR signal looks like this:
            #
            # Tick:   ,u'     ,d'                    ,u'     ,d'
            #
            # (a):  | 0 1     2 3     (long gap)   |
            # (b):          | 0 1     (long gap)     2 3   |
            #
            # The 3 seconds start either before an 'up' tick (a) or a 'down' tick (b).
            # (down means pendulum is about to pass through centre, up is return swing)
            # We distinguish the two cases by comparing the inner gap ([2] - [1]) with
            # the outer gap ([0]+3secs - [3]).

            if len(i_pos_tick) < 3:
                print "Not enough ticks"
                if PLOT:
                    #plt.clf()
                    fig, ax = plt.subplots(2, sharex=True)
                    ax[0].plot(samples[:, 0]) #[:,self.source.CHANNEL_TICK])
                    ax[1].plot(samples[:, 1])
                    ax[0].set_title('tick')
                    ax[1].set_title('pps')
                    for i in i_pos_tick: ax[0].axvline(i, c='g')
                    for i in i_neg_tick: ax[0].axvline(i, c='r')
                    for i in i_pos_pps: ax[1].axvline(i, c='g')
                    for i in i_neg_pps: ax[1].axvline(i, c='r')
                    plt.show()
                    plt.draw()
                self.source.consume(len(samples))
                continue

            # Start of pulse is up
            tick_gap_1 = i_pos_tick[1] - i_pos_tick[0]
            tick_gap_2 = i_pos_tick[2] - i_pos_tick[1]
            if tick_gap_1 > tick_gap_2:
                # down tick 0 is the start of the down-swing
                iref = i_pos_tick[0]
                print "First tick is down-swing"
            else:
                # down tick 1 is the start of the down-swing
                iref = i_pos_tick[1]
                print "Second tick is down-swing"

            # Consume samples belonging to this chunk
            i_put_back = iref + (3.0 - self.pretrigger)*self.source.fs

            i_pos_tick = [i for i in i_pos_tick if i >= iref]
            i_neg_tick = [i for i in i_neg_tick if i >= iref]
            i_pos_pps  = [i for i in i_pos_pps  if i >= iref]
            i_neg_pps  = [i for i in i_neg_pps  if i >= iref]

            # XXX This is messy, checking multiple times
            if len(i_pos_tick) < 3:
                print "Not enough ticks after down-swing"
                self.source.consume(len(samples))
                continue

            if PLOT:
                #plt.clf()
                fig, ax = plt.subplots(2, sharex=True)
                ax[0].plot(samples[:, 0]) #[:,self.source.CHANNEL_TICK])
                ax[1].plot(samples[:, 1])
                ax[0].set_title('tick')
                ax[1].set_title('pps')
                for i in i_pos_tick: ax[0].axvline(i, c='g')
                for i in i_neg_tick: ax[0].axvline(i, c='r')
                for i in i_pos_pps: ax[1].axvline(i, c='g')
                for i in i_neg_pps: ax[1].axvline(i, c='r')
                ax[0].axvline(i_put_back, c='k', lw='2')
                ax[0].plot(int(iref), samples[int(iref), self.source.CHANNEL_TICK], 'o')
                ax[0].axvline(iref, ls='--', c='k')
                plt.show()
                plt.draw()

            # Time of reference tick
            t = self.source.time + timedelta(seconds = iref / self.source.fs)

            print "Consuming %d samples" % i_put_back
            #self.put_back_samples(samples[i_put_back:])
            self.source.consume(i_put_back)

            yield t, (i_pos_pps, i_neg_pps), (i_pos_tick, i_neg_tick)

    def find_edges(self, samples):
        above = (samples >  self.edge_level).astype(int)
        below = (samples < -self.edge_level).astype(int)
        i_pos = np.where(np.diff(above) > 0)[0]
        i_neg = np.where(np.diff(below) > 0)[0]
        return i_pos, i_neg

    def fit_decays(self, y, i_edges):
        """
        Fit the exponential decays found in ``y`` after each index in ``ii``
        """
        Nfit = int(self.decay_fit_duration * self.source.fs)
        Nlag = int(self.decay_fit_delay * self.source.fs)

        # Extract decay segments and fit line to log(y)
        segments = np.vstack([y[i+Nlag:i+Nlag+Nfit] for i in i_edges
                              if (i+Nlag+Nfit) < len(y)]).T
        K, A_log = np.polyfit(np.arange(Nfit), np.log(segments), 1)
        A = np.exp(A_log)

        # Time when fitted line crosses a threshold
        # when ythresh = A exp(K i) ===> log(ythresh/A)/K = i
        #i_decay = np.log(0.5 / A) / K
        i_decay = (np.log(0.5) - A_log) / K
        return i_edges[:len(i_decay)] + Nlag + i_decay

    def sanity_check_pps(self, i_edges):
        # Find mean sample rate from PPS signal
        fs_mean = np.mean(np.diff(i_edges))
        fs_var = np.std(np.diff(i_edges))
        print i_edges, fs_mean, fs_var
        if abs(fs_mean / self.source.fs - 1) > PPS_RATE_ERROR_THRESHOLD:
            raise DataError("Sample rate is off by too much: %+d ppm"
                            % (1e6*abs(fs_mean/self.source.fs-1)))

        # PPS should be +/- 1us. Warn if std.deviation * 3, say, is greater than this.
        #  i.e. 9*variance > (1e-6 * fs)^2? but this is rather less than 1 sample...
        if fs_var > 2: #  warn if sample rate seems too variable (empirical)
            print "** Warning: PPS signal interval variance is high (%d)" % fs_var

    def calculate_drift(self, ticks, pps, relative_to_pps=False):
        pps_ref = [i for i in pps if i >= ticks[0]]
        if not pps_ref:
            raise DataError("No PPS found after down tick")

        local_fs = self.source.fs
        if relative_to_pps:
            # Assume the gap between PPS edges is 1 second, rather than using
            # nominal sample rate
            i_pps_ref = [j for j in range(len(pps)) if pps[j] >= ticks[0]][0]
            if i_pps_ref > 0: # use previous gap
                local_fs = pps[i_pps_ref] - pps[i_pps_ref-1]
            elif (i_pps_ref == 0) and (i_pps_ref+1 < len(pps)): # use next gap
                local_fs = pps[i_pps_ref+1] - pps[i_pps_ref]
            # Otherwise fall back on nominal rate

        drift = (pps_ref[0] - ticks[0]) / local_fs
        if drift > 1.5:
            # must be a missing PPS, or something's gone wrong
            raise DataError("Time between down tick and next PPS too high: %.2f s" % drift)
        return drift

    def calculate_amplitude(self, pos, neg):
        period = (pos[2] - pos[0]) # in samples

        w = 2 * pi / period # pendulum frequency in rad/sample

        num = sin(w*pos[0]) - sin(w*neg[0]) + sin(w*pos[1]) - sin(w*neg[1])
        den = cos(w*pos[0]) - cos(w*neg[0]) + cos(w*pos[1]) - cos(w*neg[1])
        t0 = np.arctan2(num, den)

        return abs(self.shim_width / (sin(w*pos[0] - t0) - sin(w*neg[0] - t0)))
