import os
import os.path
from rewritedcm import rewritedcm
from test.helper import allniiclose


def test_rewrite(tmpdir):
    expath = os.path.abspath('example/')
    exnii = expath + "/20210122_grappa.nii.gz"
    os.chdir(tmpdir)
    rewritedcm(expath + "/20210220_grappa/", exnii)
    os.system("dcm2niix -o ./ -f new pySlice_*/")
    assert allniiclose(exnii, 'new.nii.gz')

