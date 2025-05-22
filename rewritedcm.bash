#!/usr/bin/env bash
set -e

# rewrite dicoms to look like a nifti

usage(){
cat <<HERE
rewritedcm.bash "path/to/dcmdir" "path/to/nii.gz" [ "python"|"octave" ]

Example:
 ./rewritedcm.bash example/20210220_grappa/ example/20210122_grappa.nii.gz python
 feh example/pySlice_MPRAGE_GRAPPA1mm/*.png

HERE
exit
}

[ $# -eq 0 ] && usage

[ -z "$1" -o ! -d "$1" ] && echo "bad dcm directory '$1'" && exit 1
[ -z "$2" -o ! -r "$2" ] && echo "bad nifti '$2'"         && exit 1

mkcannon() { echo $(cd $(dirname $1);pwd)/$(basename $1);}
mkniiandimg(){
  pwd
  dcm2niix -z y .
  slicer -a img.png $(ls -1tc $(pwd)/*nii.gz|sed 1q)
  ls $(pwd)/img.png
}

dcmdir=$(mkcannon $1)
niifile=$(mkcannon $2)

thisdir=$(cd $(dirname $0);pwd)

# reference image
# [ ! -r $dcmdir/img.png ] && (cd $dcmdir; mkniiandimg)

case "${3:-matlab}" in
   matlab)
     unset CLICOLOR
     unset LSCOLORS
     mlcmd="rewritedcm('$dcmdir','$niifile')"
     set -x
     matlab -nodisplay -r "try, addpath('$thisdir');$mlcmd;catch e, disp(e), end, quit()"
     set +x
     cd $(dirname $niifile)/*mlBrainStrip_*/
     mkniiandimg
     ;;
  python)
     cd $(dirname $niifile)

     set -x
     $thisdir/rewritedcm.py "$dcmdir" "$niifile"
     set +x
     cd pySlice*/
     mkniiandimg
     ;;
  octave)
     unset CLICOLOR
     unset LSCOLORS

     mlcmd="rewritedcm('$dcmdir','$niifile', '$(date +%F)_octave_')"
     set -x
     octave --eval "try, addpath('$thisdir');$mlcmd;catch e, disp(e), end, quit()"
     set +x
     cd $(dirname $niifile)/*_octave_*/
     mkniiandimg;;
esac

slicer -a nifti_img.png $niifile
