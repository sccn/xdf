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
    
def test_earliest_marker_stamp():
    'check validity of first element in marker stream'
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[3]['time_stamps'][0], 1.1071)
    
def test_latest_marker_stamp():
    'check validity of first element in marker stream'
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[3]['time_stamps'][-1], 1.2)

def test_earliest_marker_series():
    olap = _limit_streams_to_overlap(streams())
    assert olap[3]['time_series'][0] == 'mark_1'
    
def test_latest_marker_series():
    olap = _limit_streams_to_overlap(streams())
    assert olap[3]['time_series'][-1] == 'mark_2' 
    
def test_earliest_fast_stamp():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][0], 1.) 
    
def test_earliest_fast_series():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][0], 1.) 
    
def test_latest_fast_stamp():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][-1], 1.4) 
    
def test_latest_fast_series():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][-1], 1.4) 
    
def test_earliest_slow_stamp():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][0], 1.) 
    
def test_earliest_slow_series():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][0], 1.) 
    
def test_latest_slow_stamp():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][-1], 1.4) 
    
def test_latest_slow_series():
    olap = _limit_streams_to_overlap(streams())
    assert np.isclose(olap[1]['time_stamps'][-1], 1.4) 
    
