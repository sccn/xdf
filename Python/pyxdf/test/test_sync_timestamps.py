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
    # integer datatype stream, 
    streams[4] = MockStream(np.linspace(0.1,1.1,251), 
                            np.linspace(0, 250, 251, dtype='int32'), 
                            250, ['int32'])

    return streams

@pytest.fixture(scope='session')
def synced(streams):
    synced = _sync_timestamps(deepcopy(streams))
    return synced

#%% test
def test_samplingrate(synced):
    'check that for all streams the sampling rate is identical to the fastest'
    for s in synced.values():                
        assert(s['info']['effective_srate']==1000)    

def test_timestamps(synced):
    '''test whether all timestamps are identical and as expected
    earliest timestamp is 0.1 from stream 1,4; latest is 2.5 from stream 3'''
    for s in synced.values():
        assert np.all(np.isclose(s['time_stamps'], np.linspace(.1, 2.5, 2401)))        
     
def test_identical_timestamp_steps(synced):
    'all steps between samples should be identical within float precision'
    for stream in synced.values():        
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
                           np.array([0.2 , #identical
                                     1.107, #shifted
                                     1.2  , 1.9  , 2.5  ]#shifted
                                    )))

def test_interpolation(synced):
    '''the linearly to 1000 Hz interpolated data from stream 2 should 
    be identical with a linspace with 1001 samples.'''
    idx = np.where(~np.isnan(synced[2]['time_series']))[0]
    assert np.all(np.isclose(synced[2]['time_series'][idx], 
                             np.linspace(2, 1, 1001)))
    
def test_extrapolation(synced, streams):
    '''extrapolated data should be nans or "" for markers '''
    # stream 1 is extrapolated from 0.1 up to 1 and after 2 to 2.5
    idx = np.where(np.isnan(synced[1]['time_series']))[0]
    values = synced[1]['time_stamps'][idx]    
    expectation = np.hstack((np.linspace(.1, 1, 900, endpoint=False),
                             np.linspace(2.001, 2.5, 500, endpoint=True)))
    assert np.all(np.isclose(values, expectation))
    
    # stream 2 is extrapolated from after 1.1 to 2.5
    idx = np.where(np.isnan(synced[2]['time_series']))[0]
    values = synced[2]['time_stamps'][idx]    
    expectation = np.linspace(1.101, 2.5, num=1400, endpoint=True)
    assert np.all(np.isclose(values, expectation))
    
    # stream 3 is extrapolated everywhere but at the marker stamps
    # can be tested easier by checking whether the count of [''] 
    # equals the total samples minus the original markers
    values = np.where(synced[3]['time_series']==[''])[0].shape[0]
    expectation = (synced[3]['time_series'].shape[0] - 
                   len(streams[3]['time_series']))
    assert values == expectation
    
    # stream 4 is extrapolated from after 1.1 to 2.5
    idx = np.where(np.isnan(synced[4]['time_series']))[0]
    values = synced[4]['time_stamps'][idx]    
    expectation = np.linspace(1.101, 2.5, num=1400, endpoint=True)
    assert np.all(np.isclose(values, expectation))    
                                            
def test_identity_after_interpolation(synced, streams):
    'the data for stream 1 should be identical to original'
    idx = np.where(~np.isnan(synced[1]['time_series']))[0]
    assert np.all(np.isclose(synced[1]['time_series'][idx],
                             streams[1]['time_series']))
                             
def test_integer_interpolation(synced, streams):
    '''the data of stream 4 should be all integers. 
    
    .. note::
        interpolation is tricky, as it depends on np.around and linear 
        interpolation, which can not be approximated with np.linspace
    '''
    u = np.unique(synced[4]['time_series'])
    u = np.int64(np.compress(~np.isnan(u), u))
    assert np.all(streams[4]['time_series'] == u)
    