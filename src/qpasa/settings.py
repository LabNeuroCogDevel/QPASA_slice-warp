"""
global settings
"""
import os
import errno
import os.path
# where is the scanner mounted
MRPATH = '/Volumes/G/'
# what program to use to open files. "open" on osx. maybe "xdg-open" on linux?
FILEBROWSER = 'open'  # command to open browser
if 'Linux' in os.uname().sysname:
    FILEBROWSER = 'xdg-open'
# where is this script (the slice atlas is probably also here)
ORIGDIR = os.path.dirname(os.path.realpath(__file__))
ATLAS = os.path.join(ORIGDIR, "data","slice_atlas.nii.gz")
OUTPUTDIRROOT = os.path.expanduser('~/Desktop/slice_warps/')
CARE_ABOUT_MOUNT = False   # die if True and mount doesn't exist
TEMPLATEBRAIN = os.path.join(ORIGDIR, "data","mni_icbm152_t1_tal_nlin_asym_09c_brain.nii.gz")

# no point if we are missing ATLAS or TEMPLATEBRAIN
for fname in ATLAS, TEMPLATEBRAIN:
    if not os.path.isfile(ATLAS):
        raise FileNotFoundError(errno.ENOENT,
                                os.strerror(errno.ENOENT),
                                fname)

