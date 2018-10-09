#!/usr/bin/env python3
import dicom
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
"""


def rewritedcm(dcmdir, niifile, protonumadd=210, protoprefix='pySlice_'):
    newdata = nipy.load_image(niifile)
    niidata = newdata.get_data()

    alldcms = glob.glob(dcmdir + '/*IMA')
    # niiimg = nipy.load_image(nii)
    # niidata = niiimg.get_data()

    # d.pixel_array.shape # niidata.shape
    # (128, 118)          # (96, 118, 128)

    ndcm = len(alldcms)
    newuid = dicom.UID.generate_uid()
    for i in range(ndcm):
        dcm = alldcms[i]

        # transpose directions, flip horz and flip vert
        ndataford = numpy.fliplr(numpy.flipud(
            niidata[(ndcm - 1 - i), :, :].transpose()))

        d = dicom.read_file(dcm)
        d.pixel_array.flat = ndataford.astype(int).flatten()
        d.PixelData = d.pixel_array.tostring()

        # change settings so we can reimport
        # --- chen's code:
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

        # save directroy sould include seriesdescription
        # savedir = 'slice_warp_dcm'
        savedir = d.SeriesDescription
        if not os.path.exists(savedir):
            os.mkdir(savedir)
        outname = savedir + '/' + os.path.basename(dcm)
        d.save_as(outname)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ValueError('need 2 arguements to %s' % sys.argv[0])
    rewritedcm(sys.argv[1], sys.argv[2])
