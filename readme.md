# Slice Warp GUI
python GUI to guide through brain extraction (skull stripping) and linear warping an atlas to native space. We also make an attempt to put the atlas into dcms to import on the scanner.
## Files
 * `warps.bash` and the incluced nifti images (`*.nii*`) follow the FSL pipeline to accomplish this.
 * `slice_warp.py` is a guided GUI to select a dicom folder, bet, and warp.
 * `rewritedcm.m` and `rewritedcm.py` are attempts to write the output nii back to dcm. see `rewritedcm.bash` for usage. both are also called by `slice_warp.py`
 * `mkOSxApp.bash` failed attempt to create a launcher for python "app"
