#!/usr/bin/env python
"""
remove large values from nifti
deal with sinus artifict
"""
# 20210126 - init
#          - can probably use afni tools for faster processing instead of nibabel
import subprocess
import re
import nibabel as nib
import numpy as np

def zero_thres(imdata, rat_thres):
    """ zero out data above max*ratio threshold
    >>> zero_thres(np.array([1,2,10]), .5)
    array([1, 2, 0])
    """
    mx = max(imdata)
    imdata[np.where(imdata > mx*rat_thres)] = 0
    return imdata

def resave_nib(infile, outfile, fn):
    "get data, run fn, save data"
    img = nib.load(infile)
    imdata = img.get_fdata()
    newdata = fn(imdata)
    nib.save(nib.Nifti1Image(newdata, img.affine), outfile)

def get_3dmax(inname):
    """use brickstat to get the max value
    strip all whitespaces
    >>> get_3dmax("MPRAGE.nii")
    '4054'
    """
    stdout = subprocess.check_output(['3dBrickStat', '-slow', '-max', inname])
    maxval=re.sub('\W', '', stdout.decode())
    return maxval