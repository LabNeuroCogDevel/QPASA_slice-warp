#!/usr/bin/env bash
#
# osascript saved as app, put in dock:
#  tell application "Terminal" to do script "/opt/ni_tools/slice_warp_gui/slice_warp.bash; exit"
#

# use brew python and other tools
PATH="/usr/local/bin:$PATH"
# add slice gui to path
PATH="$PATH:/opt/ni_tools/slice_warp_gui"

# add dcm2niix to the path
PATH="$PATH:/opt/ni_tools/dcm2niix"
# ROBEX
PATH="$PATH:/opt/ni_tools/robex_1.12"
# MATLAB
PATH="$PATH:/Applications/MATLAB_R2017a.app/bin"

AFNIDIR="/opt/ni_tools/afni"
PATH="$PATH:$AFNIDIR"
# mount data  if we dont have it
#[ ! -d /Volumes/Disk_C/Temp/ ] && echo "mounting temp!" && osascript -e "try" -e "mount volume \"smb://meduser@192.168.2.1/Disk_C\"" -e "end try" 
vialinux=""
viascanner=""
[ -d /Volumes/HostDicom/ ] && mount | grep HostDicom -q  && vialinux=yes
[ -d /Volumes/Disk_C/ ] && mount | grep Disk_C -q  && viascanner=yes
if [ -z "$viascanner$vialinux" ]; then
   ret=$(osascript -e 'tell application (path to frontmost application as text) to display dialog "MR computer is not accessible! meduser@10.48.88.119/HostDicom or .../Disck_C with finder (go->connect to server)" buttons {"Continue","Quit"} with icon caution')

   [[ $ret =~ Quit ]] && exit 1
fi
# Launch our program if we dont have it open
slice_warp.py
