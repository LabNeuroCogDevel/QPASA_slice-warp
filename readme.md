# Slice Warp GUI
python GUI to guide through brain extraction (skull stripping) and linear warping an atlas to native space. We also make an attempt to put the atlas into dcms to import on the scanner.

# Depends

* python3: nipy, pydicom, numpy
* matlab (for rewriting nifti to dicom - python implemetation not accepted by siemens scanner?)
* scanner exported samba share mounted to exchange dicom directories
* a way to launch python scripts (windows, see anaconda; osx, consider automator running homebrew python)

## Tutorial
The goal is to 
1. read in t1 dicoms
2. put a plane through the anatomical to indicate where to postion a slice
3. make new dicoms with the annotation avaiable to the scanner

We can guide the GUI to do this:
![all](img/9_all.png?raw=True)

### Open
When opening `slice_warp.py`, you are prompted for an example anatomical dicom. 
 * All dicoms in this folder will be used to reconstruct a nifti file.
 * N.B. The final step will save dicoms to a new folder as a sibling to the one you selected. The input and output directory will share the parent directory highlighted in purple here.

![open](img/0.0_open.png?raw=True)


### Skullstrip

After selecting a reprsentive dicom, 
 * an 3d image will be constructed and skull stripped with the bet default fractional intensity threshold of .5.

![init](img/0.1_init_bet.png?raw=True)

The default skull stripping can be improved by moving the slider and clicking 're-strip'. 
> smaller values give larger brain outline estimates

![strip](img/0.2_re-strip.png?raw=True)

### Warp
Once we have the brain isolated from skull, we are read to warp. Clicking this button will 
  * bring our slice mask into native space
  * change the brain image area to display the annotation plane mask in red
  * Warping takes 30 seconds.

![warp](img/1_warp.png?raw=True)

### Make
After warping, we need to make a new image that includes the slice and convert it back to dicom for the scanner. After pushing make,
 * matlab is launched to convert annotated nifti back to dicom
 * we can inspect the newly created image with AFNI. This is also useful for setting the slice position by hand if the following 'copy back' step does not work. 

![make](img/2_make.png?raw=True)

### Copy
Finally, we can copy the newly created dicoms back to the scanner, assuming the scanner can read from the parent of the directory of the initial dicoms (highlighted purple in the first image).
 * The new output folder will have `_mlBrainStrip_` in the directory name 
 * dicoms will have a sequence number `200` greater than the initial input dicoms.

![copy](img/3_copyback.png?raw=True)

## Files
 * `warps.bash` and the incluced nifti images (`*.nii*`) follow the FSL pipeline to accomplish this.
 * `slice_warp.py` is a guided GUI to select a dicom folder, bet, and warp.
 * `rewritedcm.m` and `rewritedcm.py` are attempts to write the output nii back to dcm. see `rewritedcm.bash` for usage. both are also called by `slice_warp.py`
 * `mkOSxApp.bash` failed attempt to create a launcher for python "app"
