#!/usr/bin/env python3
"""
slice_warp.py              # run file selector. check for mount location.
slice_warp.py test         # run even if mount isn't available
slice_warp.py /path/to/nii # use /path/to/nii instead of file selector
slice_warp.py /path/to/nii test # use nifti and don't run through default steps
"""

import tkinter
import tkinter.filedialog
import tkinter.messagebox
import tkinter.scrolledtext

import os
import os.path
import sys
import re
import pydicom

from gui import SliceWarp

## GLOBAL SETTINGS
# where is the scanner mounted
MRPATH='/Volumes/HostDicom/'
# what program to use to open files. "open" on osx. maybe "xdg-open" on linux?
FILEBROWSER = 'open'  # command to open browser
# where is this script (the slice atlas is probably also here)
ORIGDIR = os.path.dirname(os.path.realpath(__file__))
ATLAS = "%s/slice_atlas.nii.gz" % ORIGDIR
EXAMPLEPATH = os.path.join(ORIGDIR, "example/")
OUTPUTDIRROOT = os.path.expanduser('~/Desktop/slice_warps/')
CARE_ABOUT_MOUNT = False   # die if True and mount doesn't exist
TEMPLATEBRAIN = "/opt/ni_tools/standard/mni_icbm152_nlin_asym_09c/mni_icbm152_t1_tal_nlin_asym_09c_brain.nii"
# FLOAT32 vs FLOAT64? dont care
os.environ['AFNI_NIFTI_TYPE_WARN'] = 'NO'


def find_init(master, initialdir, filename=None):
    """ get dicom directory from file prompt
    can also choose a nifti file
    if nothing given on command line
     code hangs here until user makes a choice
    """
    master.update()  # TODO: is this update needed.
    if filename and os.path.exists(filename):
        filename = os.path.abspath(filename)
        print("set filename via command line: %s" % master.filename)
    else:
        filename = \
            tkinter.filedialog.askopenfilename(
                initialdir=initialdir,
                title="Select a representative DICOM",
            )
    master.update()  # close the file dialog box on OS X

    return filename

def subid_from_dcm(filename):
    # get id from dicom
    if re.match('(^MR.*)|(.*IMA)$', filename):
        selectedDicom = pydicom.read_file(filename)
        subjid = "%s_%s" % (selectedDicom.PatientID, selectedDicom.PatientName)
    else:
        subjid = 'unknown'
    return subjid

def check_mount(mrpath, care_about_mount):
    """make sure we have the mount ----
     not needed if we specified a file on the command line
      though we will try if first argument is test (why? -- is this used by osx shortcut?)"""
    if care_about_mount and not os.path.exists(mrpath):
        tkinter.messagebox.showerror(
            "Error", "MR is not mounted?! (%s)\nuse command+k in finder" % mrpath)
        sys.exit(1)


###################
def main():
    if not os.path.exists(OUTPUTDIRROOT):
        os.mkdir(OUTPUTDIRROOT)

    check_mount(MRPATH, CARE_ABOUT_MOUNT and len(sys.argv) <= 1)
    # ---- initialize gui -----
    master = tkinter.Tk()
    master.title('Subject Native Slice Orientation')

    # make testing easier: set default path to local examples
    initialdir = MRPATH
    in_filename = None
    if os.uname().nodename in ["reese", "kt"]:  # , "7TMacMini.local"]:
        initialdir = EXAMPLEPATH
    if len(sys.argv) > 1:
        in_filename = sys.argv[1]


    master.filename = find_init(master, initialdir, in_filename)
    # do we need another master.update() here?

    if not master.filename:
        sys.exit(1)

    gui = SliceWarp(master, TEMPLATEBRAIN, ATLAS)
    dcmdir = os.path.dirname(master.filename)
    subjid = subid_from_dcm(master.filename)
    gui.start(dcmdir, OUTPUTDIRROOT, subjid)

    os.chdir(ORIGDIR)
    # currently keeping all files used to generate slice
    # might be useful to have linear warp parameters later
    # shutil.rmtree(tempdir)

if __name__ == "__main__":
    main()
