from pyxdf.pyxdf import _sync_timestamps
import numpy as np
from copy import deepcopy
import pytest
# %%
@pytest.fixture(scope='session')
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
    streams[2] = MockStream(np.linspace(0.1,1.1,251), 
                            np.linspace(2,1,251), 
                            250, ['float32'])
      
    # marker stream
    streams[3] = MockStream([0.2, 1.1071, 1.2, 1.9, 2.5],
                            ['mark_' + str(n) for n in range(0,5,1)], 
                            0, ['string'])
    return streams

@pytest.fixture(scope='session')
def synced(streams):
    synced = _sync_timestamps(deepcopy(streams))
    return synced

#%% test
def test_earliest(synced):
    'should expand to the earliest timestamp, which is 0.1 from stream 2'
    for stream in synced.values():
        assert np.isclose(stream['time_stamps'][0], 0.1)

def test_lastest(synced):
    'should expand to the latest timestamp, which is 2.5 from stream 3'
    for stream in synced.values():
        assert np.isclose(stream['time_stamps'][-1], 2.5)
     
def test_identical_steps(synced):
    for stream in synced.values():
        'all steos between samples should be identical within float precision'
        uq = np.diff(stream['time_stamps'])
        assert np.all([np.isclose(u, uq) for u in uq])

def test_markerstream(synced, streams):
    '''check markers, they should be identical to the original but the second,
       which should be shifted towards the next valid sample of the fastest 
       stream'''
    idx = []
    for marker in streams[3]['time_series']:
        idx.append(synced[3]['time_series'].tolist().index([marker]))
    assert np.all(np.equal(synced[3]['time_stamps'][idx],
                           np.array([0.2 , 1.107, 1.2  , 1.9  , 2.5  ])))

def test_interpolation(synced):
    '''the linearly to 1000 Hz interpolated data from stream 2 should 
    be identical with a linspace with 1001 samples'''
    idx = np.where(~np.isnan(synced[2]['time_series']))[0]
    assert np.all(np.isclose(synced[2]['time_series'][idx], 
                             np.linspace(2, 1, 1001)))

def test_identity_after_interpolation(synced, streams):
    'the data for stream 1 should be identical to original'
    idx = np.where(~np.isnan(synced[1]['time_series']))[0]
    assert np.all(np.isclose(synced[1]['time_series'][idx],
                             streams[1]['time_series']))
