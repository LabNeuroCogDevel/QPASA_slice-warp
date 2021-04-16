"""
global settings
"""
import os
import os.path
# where is the scanner mounted
MRPATH = '/Volumes/HostDicom/'
# what program to use to open files. "open" on osx. maybe "xdg-open" on linux?
FILEBROWSER = 'open'  # command to open browser
if 'Linux' in os.uname().sysname:
    FILEBROWSER = 'xdg-open'
# where is this script (the slice atlas is probably also here)
ORIGDIR = os.path.dirname(os.path.realpath(__file__))
ATLAS = "%s/slice_atlas.nii.gz" % ORIGDIR
EXAMPLEPATH = os.path.join(ORIGDIR, "example/")
OUTPUTDIRROOT = os.path.expanduser('~/Desktop/slice_warps/')
CARE_ABOUT_MOUNT = False   # die if True and mount doesn't exist
TEMPLATEBRAIN = "/opt/ni_tools/standard/mni_icbm152_nlin_asym_09c/mni_icbm152_t1_tal_nlin_asym_09c_brain.nii"
