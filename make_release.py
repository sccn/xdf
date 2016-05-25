"""Python script to create a GitHub release of this repository.

github3 Python package must be installed. Get it with `pip install github3.py`

Change the version number in Matlab/xdf/load_xdf.m before making the release.
If the version number is the same as a release already on the GitHub server
then the new release will not be made.

Be sure to commit all changes and push them to the server before
making the release.

Usage:
python make_release.py -u <ghusername> -p <ghpassword>
"""


import inspect
import os
import sys
import getopt
import re
import zipfile
from github3 import GitHub, GitHubError  # pip install github3.py

def zipdir(dir2zip, zipout, expand_dir = None):
    # zipout is zipfile handle
    for root, dirs, files in os.walk(dir2zip):
        for fname in files:
            if not fname.startswith('.'):
                if expand_dir:
                    split_path = list(os.path.split(root))
                    split_path[0] = expand_dir
                    new_root = os.path.join(*tuple(split_path))
                    zipout.write(os.path.join(root, fname), arcname=os.path.join(new_root, fname))
                else:
                    zipout.write(os.path.join(root, fname))

def main(argv):
    # Parse input arguments into username and password
    username = ''
    password = ''
    try:
        opts, args = getopt.getopt(argv,"u:p:",["username=","password="])
    except getopt.GetoptError:
        print('make_release.py -u <ghusername> -p <ghpassword>')
        sys.exit(2)
    if len(opts) < 2:
        print('make_release.py -u <ghusername> -p <ghpassword>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('make_release.py -u <ghusername> -p <ghpassword>')
            sys.exit()
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
    
    # Scan the xdf/load_xdf.m file and pull out the version
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    root_path = os.path.dirname(os.path.abspath(filename))
    mfile_path = os.path.join(root_path, 'Matlab', 'xdf', 'load_xdf.m')
    version_found = False
    with open(mfile_path) as f:
        for line in f:
            if not version_found:
                m = re.match("LIBVERSION\s=\s'(\d+\.\d+)';", line)
                if m:
                    mfile_version = m.group(1)
                    version_found = True
    
    # Create a GitHub instance and access the repository
    g = GitHub(username, password)
    repo = g.repository('sccn', 'xdf')
    
    if version_found:
        #Create the release
        #http://github3py.readthedocs.org/en/latest/repos.html#github3.repos.repo.Repository.create_release
        try:
            release = repo.create_release('v'+mfile_version, target_commitish='master')
        except GitHubError:
            print('Release for version ' + mfile_version + ' already exists or validation failed.')
            return None
        
        #zip contents of Matlab\* into xdfimport<version#>.zip
        eeglabfn = 'xdfimport' + mfile_version + '.zip'
        zf = zipfile.ZipFile(eeglabfn, mode='w', compression=zipfile.ZIP_DEFLATED)
        zipdir('Matlab/', zf, 'xdfimport' + mfile_version)
        zf.close()
        
        #zip contents of Matlab\xdf\* into xdf.zip
        zf2 = zipfile.ZipFile('xdf.zip', mode='w', compression=zipfile.ZIP_DEFLATED)
        zipdir('Matlab/xdf/', zf2, 'xdf')
        zf2.close()
        
        #http://github3py.readthedocs.org/en/latest/repos.html#github3.repos.release.Release.upload_asset
        #Upload zip files as release assets
        with open(eeglabfn, 'rb') as fd:
            content = fd.read()
            release.upload_asset('application/zip', eeglabfn, content)
        with open('xdf.zip', 'rb') as fd:
            content = fd.read()
            release.upload_asset('application/zip', 'xdf.zip', content)
        #Upload mex files as release assets
        for fn in os.listdir('Matlab/xdf/'):
            fname, fext = os.path.splitext(fn)
            if len(fext) > 3 and fext[:4] == '.mex':
                with open(os.path.join('Matlab', 'xdf', fn), 'rb') as fd:
                    content = fd.read()
                release.upload_asset('application/octet-stream', fn, content)

if __name__ == "__main__":
    main(sys.argv[1:])