#!/usr/bin/env bash

thisdir=$(cd $(dirname $0);pwd)
python3=$(which python3)

appdir=/Applications/slice_warp.app/Contents/MacOS/
# dont need to do anything if it already exists
[ -r $appdir/slice_warp ] && exit 0

[ ! -d $appdir ] && mkdir -p $appdir

echo > $appdir/slice_warp <<HEREDOC
#!/usr/bin/osascript
do shell script "export LC_ALL=en_US.UTF-8; export LANG=en_US.UTF-8; $python3 '$thisdir/slice_warp.py' &> /dev/null &"
HEREDOC

chmod +x $appdir/slice_warp 
