import pytest
import os
import os.path
from gui import SliceWarp
from logfield import LogField
from settings import ATLAS, TEMPLATEBRAIN, ORIGDIR

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

    def updateimg(self, img):
        print("would update image %s" % img)

@pytest.fixture
def gui_nii():
    os.chdir(ORIGDIR)
    return FakeSliceWarp('example/20210122_grappa.nii.gz')

@pytest.fixture
def gui_dcm():
    os.chdir(ORIGDIR)
    return FakeSliceWarp('example/20210220_143419_mlBrainStrip_MPRAGE_GRAPPA1mm/20210220LUNA1.MR.TIEJUN_JREF-LUNA.0013.0001.2021.02.20.14.34.40.312500.263962728.IMA')

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
    assert os.path.isfile(os.path.join(gui_dcm.tempdir,'mprage1.nii.gz'))
    assert os.path.isfile(os.path.join(gui_dcm.tempdir,'mprage1_res.nii.gz'))
    assert os.path.isfile(os.path.join(gui_dcm.tempdir,'mprage_bet.nii.gz'))

def test_warp(tmpdir, gui_dcm):
    gui_dcm.setup(tmpdir)
    gui_dcm.get_initial_input()
    gui_dcm.warp()
    assert os.path.isfile(os.path.join(gui_dcm.tempdir,'slice_mprage_rigid.nii.gz'))

