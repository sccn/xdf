"""Defines the function load_xdf, which imports XDF files.

This function is closely following the load_xdf reference implementation.

"""

import os
import struct
import itertools
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict

import numpy as np

__all__ = ['load_xdf']
__version__ = '1.14.0'


def load_xdf(filename,
             on_chunk=None,
             verbose=True,
             synchronize_clocks=True,
             handle_clock_resets=True,
             dejitter_timestamps=True,
             jitter_break_threshold_seconds=1,
             jitter_break_threshold_samples=500,
             clock_reset_threshold_seconds=5,
             clock_reset_threshold_stds=5,
             clock_reset_threshold_offset_seconds=1,
             clock_reset_threshold_offset_stds=10,
             winsor_threshold=0.0001):
    """Import an XDF file.

    This is an importer for multi-stream XDF (Extensible Data Format)
    recordings. All information covered by the XDF 1.0 specification is
    imported, plus any additional meta-data associated with streams or with
    the container file itself.

    See http://code.google.com/p/xdf/ for more information on XDF.

    The function supports several further features, such as robust time
    synchronization, support for breaks in the data, as well as some other
    defects.

    Args:
        filename : name of the file to import (*.xdf or *.xdfz)

        verbose : Whether to print verbose diagnostics. (default: false)

        synchronize_clocks : Whether to enable clock synchronization based on
          ClockOffset chunks. (default: true)

        dejitter_timestamps : Whether to perform jitter removal for regularly
          sampled streams. (default: true)

        on_chunk : Function that is called for each chunk of data as it is
           being retrieved from the file; the function is allowed to modify
           the data (for example, sub-sample it). The four input arguments
           are 1) the matrix of [#channels x #samples] values (either numeric
           or 2d cell array of strings), 2) the vector of unprocessed local
           time stamps ( one per sample), 3) the info struct for the stream (
           same as the .info field in the final output, buth without the
           .effective_srate sub-field), and 4) the scalar stream number (
           1-based integers). The three return values are 1) the (optionally
           modified) data, 2) the (optionally modified) time stamps, and 3)
           the (optionally modified) header (default: []).

        Parameters for advanced failure recovery in clock synchronization:

        handle_clock_resets : Whether the importer should check for potential
          resets of the clock of a stream (e.g. computer restart during
          recording, or hot-swap). Only useful if the recording system
          supports recording under such circumstances. (default: true)

        clock_reset_threshold_stds : A clock reset must be accompanied by a
          ClockOffset chunk being delayed by at least this many standard
          deviations from the distribution. (default: 5)

        clock_reset_threshold_seconds : A clock reset must be accompanied by a
          ClockOffset chunk being delayed by at least this many seconds. (
          default: 5)

        clock_reset_threshold_offset_stds : A clock reset must be accompanied
          by a ClockOffset difference that lies at least this many standard
          deviations from the distribution. (default: 10)

        clock_reset_threshold_offset_seconds : A clock reset must be
          accompanied by a ClockOffset difference that is at least this many
          seconds away from the median. (default: 1)

        clock_reset_max_jitter : Maximum tolerable jitter (in seconds of error)
          for clock reset handling. (default: 5)

        Parameters for jitter removal in the presence of data breaks:

        jitter_break_threshold_seconds : An interruption in a regularly-sampled
          stream of at least this many seconds will be considered as a
          potential break (if also the jitter_break_threshold_samples is
          crossed) and multiple segments will be returned. (default: 1)

        jitter_break_threshold_samples : An interruption in a regularly-sampled
          stream of at least this many samples will be considered as a
          potential break (if also the jitter_break_threshold_samples is
          crossed) and multiple segments will be returned. (default: 500)

    Returns:
        streams : list of dicts, one for each stream; the dicts
                  have the following content:
                 ['time_series'] entry: contains the stream's time series
                   [#Channels x #Samples] this matrix is of the type declared in
                   ['info']['channel_format']
                 ['time_stamps'] entry: contains the time stamps for each sample
                   (synced across streams)

                 ['info'] field: contains the meta-data of the stream
                   (all values are strings)
                   ['name']: name of the stream
                   ['type']: content-type of the stream ('EEG','Events', ...)
                   ['channel_format']: value format ('int8', 'int16', 'int32',
                     'int64', 'float32', 'double64', 'string')
                   ['nominal_srate']: nominal sampling rate of the stream
                     (as declared by the device); zero for streams with
                     irregular sampling rate
                   ['effective_srate']: effective (measured) sampling rate of
                     the stream, if regular (otherwise omitted)
                   ['desc']: dict with any domain-specific meta-data declared
                     for the stream; see www.xdf.org for the declared
                     specifications

        fileheader : dict with file header contents in the "info" field

    Examples:
        load the streams contained in a given XDF file
        >>> streams = load_xdf('C:\Recordings\myrecording.xdf')

    License:
        This file is covered by the BSD license.

        Copyright (c) 2015-2018, Syntrogi Inc. dba Intheon

        Redistribution and use in source and binary forms, with or without
        modification, are permitted provided that the following conditions are
        met:

            * Redistributions of source code must retain the above copyright
              notice, this list of conditions and the following disclaimer.
            * Redistributions in binary form must reproduce the above copyright
              notice, this list of conditions and the following disclaimer in
              the documentation and/or other materials provided with the
              distribution

        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
        "AS IS AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
        LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
        A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
        OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
        SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
        LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
        DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
        THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (
        INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
        OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    """

    class StreamData:
        """Temporary per-stream data."""
        def __init__(self, xml):
            """Init a new StreamData object from a stream header."""
            fmt2char = {'int8': 'b', 'int16': 'h', 'int32': 'i', 'int64': 'q',
                        'float32': 'f', 'double64': 'd'}
            fmt2nbytes = {'int8': 1, 'int16': 2, 'int32': 4, 'int64': 8,
                          'float32': 4, 'double64': 8}
            # number of channels
            self.nchns = int(xml['info']['channel_count'][0])
            # nominal sampling rate in Hz
            self.srate = int(xml['info']['nominal_srate'][0])
            # format string (int8, int16, int32, float32, double64, string)
            self.fmt = xml['info']['channel_format'][0]
            # list of time-stamp chunks (each an ndarray, in seconds)
            self.time_stamps = []
            # list of time-series chunks (each an ndarray or list of lists)
            self.time_series = []
            # list of clock offset measurement times (in seconds)
            self.clock_times = []
            # list of clock offset measurement values (in seconds)
            self.clock_values = []
            # last observed time stamp, for delta decompression
            self.last_timestamp = 0.0
            # nominal sampling interval, in seconds, for delta decompression
            self.tdiff = 1.0/self.srate if self.srate > 0 else 0.0
            # pre-calc some parsing parameters for efficiency
            if self.fmt != 'string':
                # number of bytes to read from stream to handle one sample
                self.samplebytes = self.nchns * fmt2nbytes[self.fmt]
                # format string to pass to struct.unpack() to handle one sample
                self.structfmt = '<%s%s' % (self.nchns, fmt2char[self.fmt])

    if verbose:
        print('Importing XDF file %s...' % filename)
    if not os.path.exists(filename):
        raise Exception('file %s does not exist.' % filename)

    # dict of returned streams, in order of apparance, indexed by stream id
    streams = OrderedDict()
    # dict of per-stream temporary data (StreamData), indexed by stream id
    temp = {}
    # XML content of the file header chunk
    fileheader = None
    # number of bytes in the file for fault tolerance
    filesize = os.path.getsize(filename)

    # read file contents ([SomeText] below refers to items in the XDF Spec)
    with open(filename, 'rb') as f:

        # read [MagicCode]
        if f.read(4) != b'XDF:':
            raise Exception('not a valid XDF file: %s' % filename)

        # for each chunk...
        while True:

            # noinspection PyBroadException
            try:
                # read [NumLengthBytes], [Length]
                chunklen = _read_varlen_int(f)
            except:
                if f.tell() < filesize-1024:
                    print('  got zero-length chunk, scanning forward to next '
                          'boundary chunk.')
                    _scan_forward(f)
                    continue
                else:
                    if verbose:
                        print('  reached end of file.')
                    break

            # read [Tag]
            tag = struct.unpack('<H', f.read(2))[0]
            if verbose:
                print('  read tag: %i at %d bytes, length=%d'
                      % (tag, f.tell(), chunklen))

            # read the chunk's [Content]...
            if tag == 1:
                # read [FileHeader] chunk
                xml_string = f.read(chunklen-2)
                fileheader = _xml2dict(ET.fromstring(xml_string))
            elif tag == 2:
                # read [StreamHeader] chunk...
                # read [StreamId]
                s = struct.unpack('<I', f.read(4))[0]
                # read [Content]
                xml_string = f.read(chunklen-6)
                hdr = _xml2dict(ET.fromstring(xml_string))
                streams[s] = hdr
                if verbose:
                    print('  found stream ' + hdr['info']['name'][0])
                # initialize per-stream temp data
                temp[s] = StreamData(hdr)
            elif tag == 3:
                # read [Samples] chunk...
                try:
                    # read [StreamId]
                    s = struct.unpack('<I', f.read(4))[0]
                    # read [NumSampleBytes], [NumSamples]
                    nsamples = _read_varlen_int(f)
                    # allocate space
                    stamps = np.zeros((nsamples,))
                    if temp[s].fmt == 'string':
                        # read a sample comprised of strings
                        values = [[None]*temp[s].nchns for _ in range(nsamples)]
                        # for each sample...
                        for k in range(nsamples):
                            # read or deduce time stamp
                            if struct.unpack('B', f.read(1))[0]:
                                stamps[k] = struct.unpack('<d', f.read(8))[0]
                            else:
                                stamps[k] = (temp[s].last_timestamp +
                                             temp[s].tdiff)
                            temp[s].last_timestamp = stamps[k]
                            # read the values
                            for ch in range(temp[s].nchns):
                                raw = f.read(_read_varlen_int(f))
                                values[k][ch] = raw.decode(errors='replace')
                    else:
                        # read a sample comprised of numeric values
                        values = np.zeros((nsamples, temp[s].nchns))
                        # for each sample...
                        for k in range(nsamples):
                            # read or deduce time stamp
                            if struct.unpack('B', f.read(1))[0]:
                                stamps[k] = struct.unpack('<d', f.read(8))[0]
                            else:
                                stamps[k] = (temp[s].last_timestamp +
                                             temp[s].tdiff)
                            temp[s].last_timestamp = stamps[k]
                            # read the values
                            raw = f.read(temp[s].samplebytes)
                            values[k, :] = struct.unpack(temp[s].structfmt, raw)
                    if verbose:
                        print('  reading [%s,%s]' % (temp[s].nchns, nsamples))
                    # optionally send through the on_chunk function
                    if on_chunk is not None:
                        values, stamps, streams[s] = on_chunk(values, stamps,
                                                              streams[s], s)
                    # append to the time series...
                    temp[s].time_series.append(values)
                    temp[s].time_stamps.append(stamps)
                except Exception as e:
                    # an error occurred (perhaps a chopped-off file): emit a
                    # warning and scan forward to the next recognized chunk
                    print('  got error (%s), scanning forward to next '
                          'boundary chunk.', e)
                    _scan_forward(f)
            elif tag == 6:
                # read [StreamFooter] chunk
                s = struct.unpack('<I', f.read(4))[0]
                xml_string = f.read(chunklen-6)
                streams[s]['footer'] = _xml2dict(ET.fromstring(xml_string))
            elif tag == 4:
                # read [ClockOffset] chunk
                s = struct.unpack('<I', f.read(4))[0]
                temp[s].clock_times.append(struct.unpack('<d', f.read(8))[0])
                temp[s].clock_values.append(struct.unpack('<d', f.read(8))[0])
            else:
                # skip other chunk types (Boundary, ...)
                f.read(chunklen-2)

    # Concatenate the signal across chunks
    for stream in temp.values():
        if stream.time_stamps:
            # stream with non-empty list of chunks
            stream.time_stamps = np.concatenate(stream.time_stamps)
            if stream.fmt == 'string':
                stream.time_series = list(itertools.chain(*stream.time_series))
            else:
                stream.time_series = np.concatenate(stream.time_series)
        else:
            # stream without any chunks
            stream.time_stamps = np.zeros((0,))
            if stream.fmt == 'string':
                stream.time_series = []
            else:
                stream.time_series = np.zeros((stream.nchns, 0))

    # perform (fault-tolerant) clock synchronization if requested
    if synchronize_clocks:
        if verbose:
            print('  performing clock synchronization...')
        temp = _clock_sync(temp, handle_clock_resets,
                           clock_reset_threshold_stds,
                           clock_reset_threshold_seconds,
                           clock_reset_threshold_offset_stds,
                           clock_reset_threshold_offset_seconds,
                           winsor_threshold)

    # perform jitter removal if requested
    if dejitter_timestamps:
        if verbose:
            print('  performing jitter removal...')
        temp = _jitter_removal(temp, jitter_break_threshold_seconds,
                               jitter_break_threshold_samples,)
    else:
        for stream in temp.values():
            duration = stream.time_stamps[-1] - stream.time_stamps[0]
            stream.effective_srate = len(stream.time_stamps)/duration

    for k in streams.keys():
        stream = streams[k]
        tmp = temp[k]
        stream['info']['effective_srate'] = tmp.effective_srate
        stream['time_series'] = tmp.time_series
        stream['time_stamps'] = tmp.time_stamps

    streams = [s for s in streams.values()]
    return streams, fileheader


def _read_varlen_int(f):
    """Read a variable-length integer."""
    nbytes = struct.unpack('B', f.read(1))[0]
    if nbytes == 1:
        return struct.unpack('B', f.read(1))[0]
    elif nbytes == 4:
        return struct.unpack('<I', f.read(4))[0]
    elif nbytes == 8:
        return struct.unpack('<Q', f.read(8))[0]
    else:
        raise RuntimeError('invalid variable-length integer encountered.')


def _xml2dict(t):
    """Convert an attribute-less etree.Element into a dict."""
    dd = defaultdict(list)
    for dc in map(_xml2dict, list(t)):
        for k, v in dc.items():
            dd[k].append(v)
    return {t.tag: dd or t.text}


def _scan_forward(f):
    """Scan forward through the given file object until after the next
    boundary chunk."""
    blocklen = 2**20
    signature = bytes([0x43, 0xA5, 0x46, 0xDC, 0xCB, 0xF5, 0x41, 0x0F,
                       0xB3, 0x0E, 0xD5, 0x46, 0x73, 0x83, 0xCB, 0xE4])
    while True:
        curpos = f.tell()
        block = f.read(blocklen)
        matchpos = block.find(signature)
        if matchpos != -1:
            f.seek(curpos + matchpos + 15)
            print('  scan forward found a boundary chunk.')
            break
        if len(block) < blocklen:
            print('  scan forward reached end of file with no match.')
            break


def _clock_sync(streams,
                handle_clock_resets=True,
                reset_threshold_stds=5,
                reset_threshold_seconds=5,
                reset_threshold_offset_stds=10,
                reset_threshold_offset_seconds=1,
                winsor_threshold=0.0001):
    for stream in streams.values():
        if len(stream.time_stamps) > 0:
            clock_times = stream.clock_times
            clock_values = stream.clock_values

            # Detect clock resets (e.g., computer restarts during recording)
            # if requested, this is only for cases where "everything goes
            # wrong" during recording note that this is a fancy feature that
            # is not needed for normal XDF compliance.
            if handle_clock_resets:
                # First detect potential breaks in the synchronization data;
                # this is only necessary when the importer should be able to
                # deal with recordings where the computer that served a
                # stream was restarted or hot-swapped during an ongoing
                # recording, or the clock was reset otherwise.

                time_diff = np.diff(clock_times)
                value_diff = np.abs(np.diff(clock_values))
                median_ival = np.median(time_diff)
                median_slope = np.median(value_diff)

                # points where a glitch in the timing of successive clock
                # measurements happened
                mad = (np.median(np.abs(time_diff-median_ival)) +
                       np.finfo(float).eps)
                cond1 = time_diff < 0
                cond2 = (time_diff - median_ival) / mad > reset_threshold_stds
                cond3 = time_diff - median_ival > reset_threshold_seconds
                time_glitch = cond1 | (cond2 & cond3)

                # Points where a glitch in successive clock value estimates
                # happened
                mad = (np.median(np.abs(value_diff-median_slope)) +
                       np.finfo(float).eps)
                cond1 = value_diff < 0
                cond2 = ((value_diff - median_slope) / mad >
                         reset_threshold_offset_stds)
                cond3 = (value_diff - median_slope >
                         reset_threshold_offset_seconds)
                value_glitch = cond1 | (cond2 & cond3)
                resets_at = time_glitch & value_glitch

                # Determine the [begin,end] index ranges between resets
                if not any(resets_at):
                    ranges = [(0, len(clock_times)-1)]
                else:
                    indices = np.where(resets_at)[0]
                    indices = np.hstack((0, indices, indices+1,
                                         len(resets_at)-1))
                    ranges = np.reshape(indices, (2, -1)).T

            # Otherwise we just assume that there are no clock resets
            else:
                ranges = [(0, len(clock_times)-1)]

            # Calculate clock offset mappings for each data range
            coef = []
            for range_i in ranges:
                if range_i[0] != range_i[1]:
                    e = np.ones((range_i[1]-range_i[0]+1,))
                    X = (e, np.array(clock_times[range_i[0]:range_i[1]+1]))
                    X = np.reshape(np.hstack(X), (2, -1)).T/winsor_threshold
                    y = np.array(clock_values[range_i[0]:range_i[1]+1])
                    y /= winsor_threshold
                    # noinspection PyTypeChecker
                    coef.append(_robust_fit(X, y))
                else:
                    coef.append((clock_values[range_i[0]], 0))

            # Apply the correction to all time stamps
            if len(ranges) == 1:
                stream.time_stamps += coef[0][0] + coef[0][1]*stream.time_stamps
            else:
                for coef_i, range_i in zip(coef, ranges):
                    r = slice(range_i[0], range_i[1])
                    stream.time_stamps[r] += (coef_i[0] +
                                              coef_i[1]*stream.time_stamps[r])
    return streams


def _jitter_removal(streams,
                    break_threshold_seconds=1,
                    break_threshold_samples=500):
    for stream in streams.values():
        nsamples = len(stream.time_stamps)
        if nsamples > 0 and stream.srate > 0:
            # Identify breaks in the data
            diffs = np.diff(stream.time_stamps)
            breaks_at = diffs > np.max((break_threshold_seconds,
                                        break_threshold_samples*stream.tdiff))
            if np.any(breaks_at):
                indices = np.where(breaks_at)[0]
                indices = np.hstack((0, indices, indices+1, nsamples-1))
                ranges = np.reshape(indices, (2, -1)).T
            else:
                ranges = [(0, nsamples-1)]

            # Process each segment separately
            num_samples = []
            effective_srate = []
            for range_i in ranges:
                if range_i[1] > range_i[0]:
                    indices = np.arange(range_i[0], range_i[1]+1, 1)
                    tmp_duration = len(indices)
                    num_samples.append(tmp_duration)
                    duration = (stream.time_stamps[range_i[1]] -
                                stream.time_stamps[range_i[0]])
                    effective_srate.append(tmp_duration/duration)
                    e = np.ones((len(indices),))
                    X = np.reshape(np.hstack((e, indices)), (2, -1)).T
                    y = stream.time_stamps[indices]
                    mapping = np.linalg.lstsq(X, y, rcond=None)[0]
                    stream.time_stamps = mapping[0] + mapping[1]*indices
                    effective_srate = np.array(effective_srate)
                    num_samples = np.array(num_samples)
                    x = np.sum(effective_srate/num_samples/np.sum(num_samples))
                    stream.effective_srate = x
        else:
            stream.effective_srate = 0
    return streams


# noinspection PyTypeChecker
def _robust_fit(A, y, rho=1, iters=1000):
    """Perform a robust linear regression using the Huber loss function.

    solves the following problem via ADMM for x:
        minimize 1/2*sum(huber(A*x - y))

    Args:
        A : design matrix
        y : target variable
        rho : augmented Lagrangian variable (default: 1)
        iters : number of iterations to perform (default: 1000)

    Returns:
        x : solution for x

    Based on the ADMM Matlab codes also found at:
    http://www.stanford.edu/~boyd/papers/distr_opt_stat_learning_admm.html

    """
    Aty = np.dot(A.T, y)
    L = np.linalg.cholesky(np.dot(A.T, A))
    U = L.T
    z = np.zeros_like(y)
    u = z
    x = z
    for k in range(iters):
        x = np.linalg.solve(U, (np.linalg.solve(L, Aty + np.dot(A.T, z - u))))
        d = np.dot(A, x) - y + u
        tmp = np.maximum(0, (1 - (1+1/rho)/np.abs(d)))
        z = rho/(1 + rho)*d + 1/(1 + rho)*tmp*d
        u = d - z
    return x
