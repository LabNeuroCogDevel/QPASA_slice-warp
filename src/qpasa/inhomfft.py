#!/usr/bin/env python
"""
fix inhomogeneity that results in bad skull strip
fft->shift->ifft
"""
# 20200901 - port CM's ML code to python
import nibabel as nib
import numpy as np
from numpy.fft import fft, fftshift, ifft


def inhomfft(data, winsize=[10, 12, 10]):
    """fft->ifft to remove inhomogenaities
    @param data  3d matrix from nibabel
    @param winsize  window size for each dim"""

    # window must be even
    winsize = (np.array(winsize) // 2) * 2

    # replace signal drop out by 1 SD above mean
    mnval = np.mean(data)
    too_small = data <= mnval / 5
    data[too_small] = mnval + np.std(data)

    # for each dim:
    #   transform and shift
    #   build mask index location
    mski = [[]] * 3
    dsize = data.shape
    dfft = data * 1
    for i in range(3):
        # fft each dimension
        dfft = fftshift(fft(dfft, None, i), i)
        # build window indexes: center window on midpoint
        mski[i] = (dsize[i] + np.array([-1, 1]) * winsize[i]) // 2

    mask = dfft * 0
    mask[mski[0][0]:mski[0][1],
         mski[1][0]:mski[1][1],
         mski[2][0]:mski[2][1]] = 1

    # invert transform on masked spectrum
    filt = dfft * mask
    for i in range(3):
        filt = ifft(filt, None, i)

    # scale by shift. replace too small with zero
    icd = data / np.abs(filt)  # * mnval
    icd[too_small] = 0

    # dc component removed? values too low
    # rescale
    if(np.max(icd) < 10000):
        intensity_fix = 10000
    else:
        intensity_fix = 1

    return icd*intensity_fix


def rewrite(fname, outname=None):
    """apply correction and save
    @param fname input nifti
    @param outname output nifti
    @return corrected 3d matrix
    """
    img = nib.load(fname)
    imdata = img.get_fdata()
    icdata = inhomfft(imdata)
    if outname:
        nib.save(nib.Nifti1Image(icdata, img.affine), outname)
    return icdata


def main():
    """ command line interface
    take input and optionally save output if given
    if no output, plot
    """
    import sys

    fname = sys.argv[1]
    img = nib.load(fname)
    imdata = img.get_fdata()
    icdata = inhomfft(imdata)

    if len(sys.argv) >= 3:
        print(f"saving {sys.argv[2]}...")
        nib.save(nib.Nifti1Image(icdata, img.affine), sys.argv[2])
    else:
        import matplotlib.pyplot as plt

        def show_img(nii):
            """show center of 3d matrix/brain"""
            _, axs = plt.subplots(1, 3)
            slices = [
                nii[nii.shape[0] // 2, :, :],
                nii[:, nii.shape[1] // 2, :],
                nii[:, :, nii.shape[2] // 2],
            ]
            for i, slc in enumerate(slices):
                axs[i].imshow(slc.T, cmap="gray", origin="lower")

        show_img(imdata)
        show_img(icdata)
        plt.show()


if __name__ == "__main__":
    main()
