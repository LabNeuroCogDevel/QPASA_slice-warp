#!/usr/bin/env python3
import sys
import os
pkg_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "src")
sys.path.append(pkg_path)
from qpasa import slice_warp
slice_warp.main()
