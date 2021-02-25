import nipy
import numpy as np


def allniiclose(a, b):
    """compare 2 nifti images. input is filenames"""
    a = nipy.load_image(a).get_data()
    b = nipy.load_image(b).get_data()
    # test is useless if all numbers are low
    assert np.max(np.abs(a)) > 1.5
    # 1.5 b/c dciom converts floats back to ints
    return np.allclose(a, b, atol=1.5)
