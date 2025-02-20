#!/usr/bin/env python3
import pydicom
import glob
import numpy
import nipy
import sys
import os
# see pydicom
# https://pydicom.github.io/pydicom/stable/auto_examples/input_output/plot_write_dicom.html


"""
read in dicoms from a given directory
rewrite over data with that from given nifti
save new dicoms out in protoprefix+SeriesDescription directory

20210419 -- imports but cannot be found!
"""


def rewritedcm(dcmdir, niifile,
               protonumadd=210,
               protoprefix='pySlice_',
               maxintensity=1000):
    """
    create new dicoms using old ones
    intened to update data to include slice overlay
    """
    newdata = nipy.load_image(niifile)
    # newer nibabel uses get_fdata
    try:
        niidata = newdata.get_data()
    except AttributeError as e:
        niidata = newdata.get_fdata()


    alldcms = glob.glob(dcmdir + '/*IMA')
    alldcms = unique_uids(alldcms, niidata.shape[2])
    # niiimg = nipy.load_image(nii)
    # niidata = niiimg.get_data()

    # d.pixel_array.shape # niidata.shape
    # (128, 118)          # (96, 118, 128)

    # acquisition direction matters for repacking
    # 'Tra' (mprage) vs 'Axl' (mp2rage)
    first = pydicom.read_file(alldcms[0], stop_before_pixels=True)
    acqdir = first.get_item((0x51, 0x100e)).value.decode('utf-8').strip()

    ndcm = len(alldcms)
    newuid = pydicom.uid.generate_uid()
    for i in range(ndcm):
        dcm = alldcms[i]

        # transpose directions, flip horz and flip vert
        ndataford = dcm_rearrange(niidata, i, ndcm, acqdir)

        d = pydicom.read_file(dcm)
        d.pixel_array.flat = ndataford.astype(numpy.int16).flatten()
        d.PixelData = d.pixel_array.tobytes()

        # change settings so we can reimport
        # --- CM's code:
        #       SeriesDescription_ = ['BrainStrip_' info.SeriesDescription];
        #       info.SeriesNumber       = info.SeriesNumber + 200;
        #       info.SeriesDescription  = SeriesDescription_;
        #       info.SeriesInstanceUID  =  uid;
        # ---
        d.SeriesInstanceUID = newuid
        d.SeriesNumber = d.SeriesNumber + protonumadd

        d.SeriesDescription = protoprefix + d.SeriesDescription
        d.SequenceName = protoprefix + d.SequenceName
        d.ProtocolName = protoprefix + d.ProtocolName

        d.SmallestImagePixelValue = 0
        d.LargestImagePixelValue = maxintensity

        # save directroy sould include seriesdescription
        # savedir = 'slice_warp_dcm'
        savedir = d.SeriesDescription
        if not os.path.exists(savedir):
            os.mkdir(savedir)
        outname = savedir + '/' + os.path.basename(dcm)
        d.save_as(outname)


def dcm_rearrange(Y, i, ndcm, acqdir='Tra'):
    """
    GRAPPA MPRAGE is Tra (newer acq)
    MP2RAGE is Axl       (old sometimes crashes scanner)
    >>> egdcm='example/20210220_grappa/20210220LUNA1.MR.TIEJUN_JREF-LUNA.0013.0001.2021.02.20.14.34.40.312500.263962728.IMA'
    >>> egnii='example/20210122_grappa.nii.gz'
    >>>  pydicom.read_file(egdcm).pixel_array.shape
    (256, 184)
    >>> dcm_rearrange(nipy.load_image(egnii).get_data(), 0, 192).shape
    (256, 184)
    """
    if acqdir == 'Tra':
        myslice = Y[:, :, i].transpose()
        data = numpy.rot90(myslice, k=2)
    else:  # Ax1
        myslice = Y[(ndcm - 1 - i), :, :].transpose()
        data = numpy.fliplr(numpy.flipud(myslice))
    return data


def get_sop_uid(dcm):
    """return unique id of acquisition slice
    will want to discard dcm if redundant
    """
    return pydicom.read_file(dcm, stop_before_pixels=True).SOPInstanceUID


def unique_uids(alldcms, nslice=0):
    """only take unique uid
    >>> dcms=glob.glob('example/20210220_grappa/*IMA')
    >>> len(dcms)
    384
    >>> len(unique_uids(dcms))
    192
    """
    if len(alldcms) == nslice:
        return alldcms

    sopdict = {get_sop_uid(dcm): dcm for dcm in alldcms}
    dcms = sorted(list(sopdict.values()))

    # sanity check
    if nslice > 0 and len(dcms) != nslice:
        raise Exception("unique dicoms != number of slices (%d != %d)" %
                        (len(dcms), nslice))
    return dcms


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ValueError('need 2 arguements to %s' % sys.argv[0])
    rewritedcm(sys.argv[1], sys.argv[2])
