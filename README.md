Extensible Data Format (XDF)
============================

XDF is a general-purpose container format for multi-channel time series data with extensive associated meta information. XDF is tailored towards biosignal data such as EEG, EMG, EOG, ECG, GSR, MEG, but it can also handle data with high sampling rate (like audio) or data with a high number of channels (like fMRI or raw video). Meta information is stored as XML.

XDF is open source and designed to be a community project; that is, everyone is invited to contribute to the format [specification](https://github.com/sccn/xdf/wiki/Specifications). The core specification of the format is kept as simple as possible, but at the same time rich enough to support features such as time stamp corrections, boundary chunks for seeking, and data streams supporting many different data types (including int, float, double, and string).

The XDF concept and beta version was developed by Christian Kothe and Clemens Brunner at the [Swartz Center for Computational Neuroscience (SCCN)](http://sccn.ucsd.edu/) at the [University of California San Diego, CA, USA](http://www.ucsd.edu/).

# Repository Structure

The XDF specification is outlined in the home repository at https://github.com/sccn/xdf. As of late April 2019, XDF readers, writers, and associated tools can be found in the https://github.com/xdf-modules organization.

The most popular XDF importers (for Python, Matlab, and EEGLAB) are linked in the home repository as submodules. For this reason, if your intention is to download XDF and its implementations then you shouldn't use the green "Download" button in GitHub (which doesn't download submodules), and when you clone the repository please be sure to use the `--recursive` flag.

If you encounter any issues with any of the specific implementations then please open an issue in the appropriate submodule repository. Opening issues in the submodule instead of the home repository will help ensure it is seen by the people who are best able to help. Issues in the home XDF repository should be limited to issues with the XDF specification itself, or when a submodule link needs to be updated.
