Python library for importing Extensible Data Format (XDF)
========================================================

Python importer for [xdf](https://github.com/sccn/xdf).

## For maintainers

1. For pypi
    1. `rm -Rf build dist *.egg-info` or `rmdir /S build dist pyxdf.egg-info`
    1. `python setup.py sdist bdist_wheel`
    1. `twine upload --repository-url https://test.pypi.org/legacy/ dist/*`
    
* Delete the `--repository-url` part from the above command when ready
for permanent upload. pypi is unfriendly and requires a version bump
for any new upload.
