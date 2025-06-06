# Quantitative Partial Acquisition Slice Alignment
QPASA is a graphical tool allowing near identical slice placement across individuals despite differing morphology.
The tool walks through (1) coregistation of an outlined oblique slice (in standard MNI space) to subject space in real time and (2) uploading the subject specific image to the scan computer to guide slice placement.

It is written in python/tk and guides the user through brain extraction (skull stripping) and linear warping an atlas to native space both via FSL tools. A Matlab script is used to write the generated subject atlas as dicom files that can be imported back to the scanner for guided slice placement. AFNI's gui is used for interactively exploring the slice warpped from standard to subject space.


[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8066027.svg)](https://doi.org/10.5281/zenodo.8066027)


# Install

The quickest way to get the `qpasa` command is to run
```
pip install git+https://github.com/LabNeuroCogDevel/QPASA_slice-warp.git
```

(and have e.g. `~/.local/bin` in your `$PATH`)


Alternatively, you can clone and run from the repo directory like
```
git clone https://github.com/LabNeuroCogDevel/QPASA_slice-warp.git
cd QPASA_slice-warp.git
./qpasa
```

# Depends

* python3: nipy, pydicom, numpy, nibabel
* fsl (skullstrip, flirt)
* afni (for viewing final nifti)
* matlab (for rewriting nifti to dicom - python implemetation not accepted by siemens scanner?)
* optionally [ROBEX](https://www.nitrc.org/projects/robex) (slow but accurate skull stripping)
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

# Testing

```
python3 -m doctest *.py 
python3 -m pytest test/
python3 -m pytest test/test_pipeline.py -k test_matlab --pdb
```

# Notes on Matlab code
`load_untouch` does not apply sform or qform. We're assuming this is important when putting data back into dicoms!

```bash
3dinfo -aform_real example/MPRAGE.nii
```

```
# mat44 (aform_real):
      0.010386     -0.026947     -1.949725      94.026360
      1.717818      0.055802      0.010786    -112.157684
     -0.055645      1.717633     -0.030939    -140.046310

```


```matlab
addpath('nifti_tools/')
nii = load_nii('MPRAGE.nii');
unt = load_untouch_nii('MPRAGE.nii');

[size(nii.img); size(unt.img)]
%    96   118   128
%   118   128    96


subplot(1,2,1)
imshow(imadjust(nii.img(:,:,end/2))); title('load nii');
subplot(1,2,2);
imshow(imadjust(unt.img(:,:,end/2))); title('load untouched');
```

![](./load_untouch.png)
