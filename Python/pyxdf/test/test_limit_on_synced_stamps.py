from pyxdf.pyxdf import _sync_timestamps, _limit_streams_to_overlap
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
    streams[2] = MockStream(np.linspace(0.5,1.5,251), 
                            np.linspace(.5, 1.5, 251), 
                            250, ['float32'])
      
    # marker stream
    streams[3] = MockStream([0.2, 1.1071, 1.2, 1.9, 2.5],
                            ['mark_' + str(n) for n in range(0,5,1)], 
                            0, ['string'])
    # integer datatype stream, 
    streams[4] = MockStream(np.linspace(0.4,1.4,251), 
                            np.linspace(4, 140, 251, dtype='int32'), 
                            250, ['int32'])

    return streams
    
def mock():
    synced = _sync_timestamps(streams())
    return _limit_streams_to_overlap(synced)
    
#%% test
# earliest overlapping timestamp is 1.0 from stream 1
# latest overlapping timestamp is 1.4 from stream 4
# fastest strteam is stream 1 with fs 1000
def test_timestamps():
    'check timestamps streams'
    for s in mock().values():        
        assert np.all(np.isclose(s['time_stamps'], np.linspace(1, 1.4, 401)))

def test_first_timeseries():
    assert np.all(np.isclose(mock()[1]['time_series'], 
                             np.linspace(1, 1.4, 401)))
    
def test_second_timeseries():
    assert np.all(np.isclose(mock()[2]['time_series'], 
                             np.linspace(1, 1.4, 401)))
    
def test_third_timeseries():
    s = mock()[3]['time_series']
    idx = np.where(s!='')[0]
    assert np.all(idx == [107, 200])    
    assert mock()[3]['time_stamps'][idx[0]] == 1.107 # shifted to closest fit 
    assert mock()[3]['time_stamps'][idx[1]] == 1.2 # fits with fs 1000
    
def test_fourth_timeseries():
    # interpolation is tricky, as it depends on np.around and linear 
    # interpolation, which can not be approximated with np.linspace
    # we therefore only test first and last value of the series
    s = mock()[4]['time_series']    
    assert np.isclose(s[0], 85)
    assert np.isclose(s[-1], 140)