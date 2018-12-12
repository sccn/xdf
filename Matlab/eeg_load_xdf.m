function raw = eeg_load_xdf(filename, varargin)
% Import an XDF file from disk
% EEG = eeg_load_xdf(Filename, Options...)
%
% In:
%   Filename : name of the xdf file
%
%   Options... : list of name-value pairs for further options; the allowed names are as follows:
%                'streamname' : import only the first stream with the given name
%                               if specified, takes precedence over the streamtype argument
%
%                'streamtype' : import only the first stream with the given content type
%                                (default: 'EEG')
%
%                'effective_rate' : if true, use the effective sampling rate instead of the nominal
%                                   sampling rate (as declared by the device). Note that using
%                                   effective_rate can lead to incorrect results if the nominal
%                                   sampling rate is 0 (i.e. non constant sample interval)
%                                   (default: false)
%
%                'exclude_markerstreams' : can be a cell array of stream names to exclude from
%                                          use as marker streams (default: {})
%
% Out:
%   EEG : imported EEGLAB data set
%
%                           Christian Kothe, Swartz Center for Computational Neuroscience, UCSD
%                           2012-05-07

% parse arguments
args = hlp_varargin2struct(varargin,'streamname','','streamtype','EEG','effective_rate',false, ...
    'exclude_markerstreams',{});

% Add the folder containing load_xdf to the path.
addpath(fullfile(fileparts(mfilename('fullpath')), 'xdf'));

% first load the .xdf file
streams = load_xdf(filename);

% then pick the first stream that matches the criteria
if ~isempty(args.streamname)
    % select by name
    for s=1:length(streams)
        if isfield(streams{s}.info,'name') && strcmp(streams{s}.info.name,args.streamname)
            % found it
            stream = streams{s};
            break;
        end
    end    
    if ~exist('stream','var')
        error(['The data contains no stream with the name "'  args.streamname '".']); end
elseif ~isempty(args.streamtype)
    % select by type
    for s=1:length(streams)
        if isfield(streams{s}.info,'type') && strcmp(streams{s}.info.type,args.streamtype)
            % found it
            stream = streams{s};
            break;
        end
    end
    if ~exist('stream','var')
        error(['The data contains no stream with the type "'  args.streamtype '".']); end
else
    error('You need to pass either the streamname or the streamtype argument.');
end

raw = eeg_emptyset;

raw.data = stream.time_series;
[raw.nbchan,raw.pnts,raw.trials] = size(raw.data);
[raw.filepath,fname,fext] = fileparts(filename); raw.filename = [fname fext];
if args.effective_rate && isfinite(stream.info.effective_srate) && stream.info.effective_srate>0
    raw.srate = stream.info.effective_srate;
else
    raw.srate = str2num(stream.info.nominal_srate); %#ok<ST2NM>
end    
raw.xmin = 0;
raw.xmax = (raw.pnts-1)/raw.srate;

% chanlocs...
chanlocs = struct();
try
    for c=1:length(stream.info.desc.channels.channel)
        chn = stream.info.desc.channels.channel{c};
        if isfield(chn,'label')
            chanlocs(c).labels = chn.label; end            
        if isfield(chn,'type')
            chanlocs(c).type = chn.type; end
        try
            chanlocs(c).X = str2double(chn.location.X)/1000;
            chanlocs(c).Y = str2double(chn.location.Y)/1000;
            chanlocs(c).Z = str2double(chn.location.Z)/1000;
            [chanlocs(c).sph_theta,chanlocs(c).sph_phi,chanlocs(c).sph_radius] = cart2sph(chanlocs(c).X,chanlocs(c).Y,chanlocs(c).Z);
            [chanlocs(c).theta,chanlocs(c).radius] = cart2pol(chanlocs(c).X,chanlocs(c).Y);
        catch
            [chanlocs(c).X,chanlocs(c).Y,chanlocs(c).Z,chanlocs(c).sph_theta,chanlocs(c).sph_phi,chanlocs(c).sph_radius,chanlocs(c).theta,chanlocs(c).radius] = deal([]);
        end
        chanlocs(c).urchan = c;
        chanlocs(c).ref = '';
    end
    raw.chaninfo.nosedir = '+Y';    
catch e
    disp(['Could not import chanlocs: ' e.message]);
end
raw.chanlocs = chanlocs;

try
    raw.chaninfo.labelscheme = stream.info.desc.cap.labelscheme;
catch
end

% events...
event = [];
for s=1:length(streams)
    if (strcmp(streams{s}.info.type,'Markers') || strcmp(streams{s}.info.type,'Events')) && ~ismember(streams{s}.info.name,args.exclude_markerstreams)
        try
            s_events = struct('type', '', 'latency', [], 'duration', num2cell(ones(1, length(streams{s}.time_stamps))));
            for e=1:length(streams{s}.time_stamps)
                if iscell(streams{s}.time_series)
                    s_events(e).type = streams{s}.time_series{e};
                else
                    s_events(e).type = num2str(streams{s}.time_series(e));
                end
                [~, s_events(e).latency] = min(abs(stream.time_stamps - streams{s}.time_stamps(e)));
            end
            event = [event, s_events]; %#ok<AGROW>
        catch err
            disp(['Could not interpret event stream named "' streams{s}.info.name '": ' err.message]);
        end
    end
end
raw.event = event;


% etc...
raw.etc.desc = stream.info.desc;
raw.etc.info = rmfield(stream.info,'desc');


function res = hlp_varargin2struct(args, varargin)
% Convert a list of name-value pairs into a struct with values assigned to names.
% struct = hlp_varargin2struct(Varargin, Defaults)
%
% In:
%   Varargin : cell array of name-value pairs and/or structs (with values assigned to names)
%
%   Defaults : optional list of name-value pairs, encoding defaults; multiple alternative names may 
%              be specified in a cell array
%
% Example:
%   function myfunc(x,y,z,varargin)
%   % parse options, and give defaults for some of them: 
%   options = hlp_varargin2struct(varargin, 'somearg',10, 'anotherarg',{1 2 3}); 
%
% Notes:
%   * mandatory args can be expressed by specifying them as ..., 'myparam',mandatory, ... in the defaults
%     an error is raised when any of those is left unspecified
%
%   * the following two parameter lists are equivalent (note that the struct is specified where a name would be expected, 
%     and that it replaces the entire name-value pair):
%     ..., 'xyz',5, 'a',[], 'test','toast', 'xxx',{1}. ...
%     ..., 'xyz',5, struct( 'a',{[]},'test',{'toast'} ), 'xxx',{1}, ...     
%
%   * names with dots are allowed, i.e.: ..., 'abc',5, 'xxx.a',10, 'xxx.yyy',20, ...
%
%   * some parameters may have multiple alternative names, which shall be remapped to the 
%     standard name within opts; alternative names are given together with the defaults,
%     by specifying a cell array of names instead of the name in the defaults, as in the following example:
%     ... ,{'standard_name','alt_name_x','alt_name_y'}, 20, ...
%
% Out: 
%   Result : a struct with fields corresponding to the passed arguments (plus the defaults that were
%            not overridden); if the caller function does not retrieve the struct, the variables are
%            instead copied into the caller's workspace.
%
% Examples:
%   % define a function which takes some of its arguments as name-value pairs
%   function myfunction(myarg1,myarg2,varargin)
%   opts = hlp_varargin2struct(varargin, 'myarg3',10, 'myarg4',1001, 'myarg5','test');
%
%   % as before, but this time allow an alternative name for myarg3
%   function myfunction(myarg1,myarg2,varargin)
%   opts = hlp_varargin2struct(varargin, {'myarg3','legacyargXY'},10, 'myarg4',1001, 'myarg5','test');
%
%   % as before, but this time do not return arguments in a struct, but assign them directly to the
%   % function's workspace
%   function myfunction(myarg1,myarg2,varargin)
%   hlp_varargin2struct(varargin, {'myarg3','legacyargXY'},10, 'myarg4',1001, 'myarg5','test');
%
% See also:
%   hlp_struct2varargin, arg_define
%
%                               Christian Kothe, Swartz Center for Computational Neuroscience, UCSD
%                               2010-04-05

% a struct was specified as first argument
if isstruct(args)
    args = {args}; end

% --- handle defaults ---
if ~isempty(varargin)
    % splice substructs into the name-value list
    if any(cellfun('isclass',varargin(1:2:end),'struct'))
        varargin = flatten_structs(varargin); end    
    
    defnames = varargin(1:2:end);
    defvalues = varargin(2:2:end);
    
    % make a remapping table for alternative default names...
    for k=find(cellfun('isclass',defnames,'cell'))
        for l=2:length(defnames{k})
                name_for_alternative.(defnames{k}{l}) = defnames{k}{1}; end
        defnames{k} = defnames{k}{1};
    end
    
    % create default struct
    if [defnames{:}]~='.'
        % use only the last assignment for each name
        [s,indices] = sort(defnames(:)); 
        indices( strcmp(s((1:end-1)'),s((2:end)'))) = [];
        % and make the struct
        res = cell2struct(defvalues(indices),defnames(indices),2);
    else
        % some dot-assignments are contained in the defaults
        try
            res = struct();
            for k=1:length(defnames)
                if any(defnames{k}=='.')
                    eval(['res.' defnames{k} ' = defvalues{k};']);
                else
                    res.(defnames{k}) = defvalues{k};
                end
            end
        catch
            error(['invalid field name specified in defaults: ' defnames{k}]);
        end
    end
else
    res = struct();
end

% --- handle overrides ---
if ~isempty(args)
    % splice substructs into the name-value list
    if any(cellfun('isclass',args(1:2:end),'struct'))
        args = flatten_structs(args); end
    
    % rewrite alternative names into their standard form...
    if exist('name_for_alternative','var')
        for k=1:2:length(args)
            if isfield(name_for_alternative,args{k})
                args{k} = name_for_alternative.(args{k}); end
        end
    end
    
    % override defaults with arguments...
    try
        if [args{1:2:end}]~='.'
            for k=1:2:length(args)
                res.(args{k}) = args{k+1}; end
        else
            % some dot-assignments are contained in the overrides
            for k=1:2:length(args)
                if any(args{k}=='.')
                    eval(['res.' args{k} ' = args{k+1};']);
                else
                    res.(args{k}) = args{k+1};
                end
            end
        end
    catch
        if ischar(args{k})
            error(['invalid field name specified in arguments: ' args{k}]);
        else
            error(['invalid field name specified for the argument at position ' num2str(k)]);
        end
    end
end

% check for missing but mandatory args
% note: the used string needs to match mandatory.m
missing_entries = strcmp('__arg_mandatory__',struct2cell(res)); 
if any(missing_entries)
    fn = fieldnames(res)';
    fn = fn(missing_entries);
    error(['The parameters {' sprintf('%s, ',fn{1:end-1}) fn{end} '} were unspecified but are mandatory.']);
end

% copy to the caller's workspace if no output requested
if nargout == 0
    for fn=fieldnames(res)'
        assignin('caller',fn{1},res.(fn{1})); end
end


% substitute any structs in place of a name-value pair into the name-value list
function args = flatten_structs(args)
k = 1;
while k <= length(args)
    if isstruct(args{k})
        tmp = [fieldnames(args{k}) struct2cell(args{k})]';
        args = [args(1:k-1) tmp(:)' args(k+1:end)];
        k = k+numel(tmp);
    else
        k = k+2;
    end
end
