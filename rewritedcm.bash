#!/usr/bin/env bash

# rewrite dicoms to look like a nifti
# usage: rewritedcm.bash "path/to/dcmdir" "path/to/nii.gz" [ "python" ]

[ -z "$1" -o ! -d "$1" ] && echo "bad dcm directory '$1'" && exit 1
[ -z "$2" -o ! -r "$2" ] && echo "bad nifti '$2'"         && exit 1

thisdir=$(cd $(dirname $0);pwd)
mlcmd="rewritedcm('$1','$2')"

if [ -z "$3" ]; then
  matlab -nodisplay -r "try, addpath('$thisdir');$mlcmd;catch e, disp(e), end, quit()"
else
  cd $(dirname $2)
  $thisdir/make_dicom.py "$1" "$2"
fi
