from pyxdf.pyxdf import _limit_streams_to_overlap
import numpy as np
# %%
def streams():
    #generate mock-streams
    class MockStream(dict):
    
        def __init__(self, timestamps, timeseries, effective_srate, channel_format):
            self['time_series'] = timeseries
            self['time_stamps'] = timestamps
            self['info']        = {}
            self['info']['effective_srate'] = effective_srate
            self['info']['channel_format'] = channel_format
            
    streams = {}
    # fastest stream, latest timestamp
    streams[1] = MockStream(np.linspace(1,2,1001), 
                            np.linspace(1,2,1001), 
                            1000,  ['float32'])
    
    # slowest stream, earliest timestamp
    streams[2] = MockStream(np.linspace(0.4,1.4,251), 
                            np.linspace(0.4,1.4,251), 
                            250, ['float32'])
      
    # marker stream
    streams[3] = MockStream([0.2, 1.1071, 1.2, 1.9, 2.5],
                            ['mark_' + str(n) for n in range(0,5,1)], 
                            0, ['string'])
    return streams

# %% test

def test_timestamps():
    'test whether the first and last timestamps have been selected as expected'
    olap = _limit_streams_to_overlap(streams())
    for s,v in zip(olap.values(), 
                   [(1, 1.4), (1, 1.4), (1.1071, 1.2)]):
        assert np.isclose(s['time_stamps'][0], v[0])
        assert np.isclose(s['time_stamps'][-1], v[-1])
    
def test_timeseries():
    'test whether the first and last value are as expected'
    olap = _limit_streams_to_overlap(streams())
    for s,v in zip(olap.values(), 
                   [(1, 1.4), (1, 1.4), ('mark_1', 'mark_2')]):
        if s['info']['channel_format'] != ['string']:
            assert np.isclose(s['time_series'][0], v[0])
            assert np.isclose(s['time_series'][-1], v[-1])
        else:
            assert s['time_series'][0] == v[0]
            assert s['time_series'][-1] == v[-1]
    
