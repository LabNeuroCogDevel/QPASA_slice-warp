#!/usr/bin/env bash
set +e
mhway() {
  # using all MH outputs -- nonlinear
  applywarp -i slice_atlas.nii.gz -r MPRAGE.nii -o slice_in_mprage.nii.gz -w  mhpp/template_to_subject_warpcoef.nii.gz 
  # inverting nonlinear locally (same thing as above)
  invwarp -r MPRAGE.nii -o invwarpcoef.nii.gz -w mhpp/product_mprage_warpcoef.nii.gz
  applywarp -i slice_atlas.nii.gz -r mhpp/product_mprage_bet.nii.gz -o slice_in_mprage_frominv.nii.gz -w  invwarpcoef.nii.gz
  
  # invert mat
  convert_xfm -omat invSTD2NTV_aff.mat -inverse mhpp/product_mprage_to_MNI_1mm_affine.mat
  applyxfm4D slice_atlas.nii.gz mhpp/product_mprage_bet.nii.gz slice_mprage_rigid.nii.gz invSTD2NTV_aff.mat -singlematrix
}

timesince() {
 tic="$1"
 toc=$(date +%s)
 diff=$(echo "$toc - $tic"|bc -l)
 case "$2" in
  "")   div=1;            suf="";;
  m*)   div=60;           suf="min";;
  h*)   div="60**2";      suf="hour" ;;
  d*)   div="(60**2)*24"; suf="day" ;;
  s*|*) div=1;            suf="sec";;
 esac
 #e.g. from min to " min(s)"
 [ -n "$suf" ] && suf=" $suf(s)" 

 echo "$(echo "$diff/$div" |bc -l)$suf"
}

## now on our own
[ -d own ] && rm -r own
mkdir own
cd own

tic=$(date +%s)
bet ../MPRAGE.nii prod_bet.nii.gz  -f .7
flirt -in ../template_brain.nii -ref prod_bet.nii.gz -omat direct_std2prod_aff.mat -out std_in_native.nii.gz -dof 12 -interp spline
applyxfm4D ../slice_atlas.nii.gz prod_bet.nii.gz slice_mprage_rigid.nii.gz direct_std2prod_aff.mat -singlematrix

timesince $tic 

# or we could go native->std and invert it
#flirt -in prod_bet.nii.gz -ref ../template_brain.nii -omat prod2std_aff.mat -out native_in_std.nii.gz -dof 12 -interp spline
#convert_xfm -omat std2prod_aff.mat  -inverse prod2std_aff.mat 
#applyxfm4D ../slice_atlas.nii.gz prod_bet.nii.gz slice_mprage_rigid.nii.gz std2prod_aff.mat -singlematrix

