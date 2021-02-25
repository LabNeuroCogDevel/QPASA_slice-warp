import pytest
import os
import os.path
import glob
import shutil
import numpy as np
import nipy
from gui import SliceWarp
from logfield import LogField
from settings import ATLAS, TEMPLATEBRAIN, ORIGDIR


def allniiclose(a, b):
    """compare 2 nifti images. input is filenames"""
    a = nipy.load_image(a).get_data()
    b = nipy.load_image(b).get_data()
    # test is useless if all numbers are low
    assert np.max(np.abs(a)) > 1.5
    # 1.5 b/c dciom converts floats back to ints
    return np.allclose(a, b, atol=1.5)


class FakeSlider:
    def __init__(self, val=None):
        self.val = val

    def set(self, val):
        self.val = val
        return val

    def get(self):
        return self.val


class FakeSliceWarp(SliceWarp):
    def __init__(self, dcm):
        self.master = lambda x: x
        self.master.filename = dcm
        self.slice_mni = ATLAS
        self.template_brain = TEMPLATEBRAIN
        self.betscale = FakeSlider(.5)
        self.thres_slider = FakeSlider(.5)
        self.shouldresample = FakeSlider(1)
        self.logfield = LogField(None)

        # only for matlab
        self.logarea = lambda x: x
        self.logarea.config = lambda state: state

    def updateimg(self, img, *args):
        print("would update image %s" % img)


@pytest.fixture
def gui_nii():
    os.chdir(ORIGDIR)
    return FakeSliceWarp('example/20210122_grappa.nii.gz')


@pytest.fixture
def gui_dcm():
    os.chdir(ORIGDIR)
    return FakeSliceWarp('example/20210220_grappa/20210220LUNA1.MR.TIEJUN_JREF-LUNA.0013.0001.2021.02.20.14.34.40.312500.263962728.IMA')


def test_setupnii(gui_nii, tmpdir):
    gui_nii.setup(tmpdir)
    assert gui_nii.subjid == 'unknown'
    assert os.path.isdir(gui_nii.tempdir)


def test_setupdcm(tmpdir, gui_dcm):
    gui_dcm.setup(tmpdir)
    assert gui_dcm.subjid == '1_20210220Luna1'
    assert os.path.isdir(gui_dcm.tempdir)


def test_initial(tmpdir, gui_dcm):
    gui_dcm.setup(tmpdir)
    gui_dcm.get_initial_input()
    assert os.path.isfile(os.path.join(gui_dcm.tempdir, 'mprage1.nii.gz'))
    assert os.path.isfile(os.path.join(gui_dcm.tempdir, 'mprage1_res.nii.gz'))
    assert os.path.isfile(os.path.join(gui_dcm.tempdir, 'mprage_bet.nii.gz'))


def test_warp(tmpdir, gui_dcm):
    gui_dcm.setup(tmpdir)
    gui_dcm.get_initial_input()
    gui_dcm.warp()
    final_out = os.path.join(gui_dcm.tempdir, 'slice_mprage_rigid.nii.gz')
    assert os.path.isfile(final_out)


def test_matlab(tmpdir, gui_dcm):
    gui_dcm.setup(tmpdir)
    slice_example = os.path.join(ORIGDIR, 'example/anatAndSlice_unres.nii.gz')
    # copy b/c defaults to saving in same directory as nifti
    shutil.copy(slice_example, gui_dcm.tempdir)
    gui_dcm.write_back_to_dicom()

    dcmout = glob.glob(gui_dcm.tempdir + "/*mlBrainStrip*")[0]
    assert os.path.isdir(dcmout)

    final_outs = glob.glob(dcmout + "/*")
    assert len(final_outs) == 192

    dcm2nii = "dcm2niix -o %s -f testme %s" % (gui_dcm.tempdir, dcmout)
    gui_dcm.logfield.runcmd(dcm2nii)
    assert os.path.isfile('testme.nii.gz')
    assert allniiclose('testme.nii.gz', 'anatAndSlice_unres.nii.gz')
