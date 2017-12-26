#!/usr/bin/env python3
import tkinter
import tkinter.filedialog
import tkinter.messagebox
import tkinter.scrolledtext
from tkinter import WORD


# series nubmer, and name
import tempfile
import os
import os.path
import sys
import subprocess
import datetime
import glob
import re
from distutils.dir_util import copy_tree

import nipy
import numpy
import dicom
# from rewritedcm import *

# where is this script (the slice atlas is probably also here)
origdir = os.path.dirname(os.path.realpath(__file__))

outputdirroot = os.path.expanduser('~/Desktop/slice_warps/')
if not os.path.exists(outputdirroot):
    os.mkdir(outputdirroot)

# ----- settings -----
atlas = "%s/slice_atlas.nii.gz" % origdir
templatebrain = "/opt/ni_tools/standard/mni_icbm152_nlin_asym_09c/mni_icbm152_t1_tal_nlin_asym_09c_brain.nii"
mrpath = '/Volumes/Disk_C/Temp/'  # mount point for scanner
initialdir = mrpath

filebrowser = 'open'

# things change if we are testing (local computer)
if os.uname().nodename in ["reese"]:  # , "7TMacMini.local"]:
    mrpath = "/Volumes/Phillips/Raw/MRprojects/mMRDA-dev/2015.09.18-08.35.03/B0070/Sagittal_MPRAGE_ADNI_256x240.29/"
    initialdir = mrpath


# ---- initialize gui -----
master = tkinter.Tk()
master.title('Subject Native Slice Orientation')

# ---- make sure we have the mount ----
if not os.path.exists(mrpath) and len(sys.argv) > 1 and sys.argv[1] != 'test':
    tkinter.messagebox.showerror(
        "Error", "MR is not mounted?! (%s)\nuse command+k in finder" % mrpath)
    sys.exit(1)


# ----- get dicom directory ----
# code hangs here until user makes a choice
master.update()  # close the file dialog box on OS X
master.filename = \
    tkinter.filedialog.askopenfilename(
        initialdir=initialdir,
        title="Select a representative DICOM",
    )
# filetypes = (("all files","*.*"),("Dicoms","MR*")))
master.update()  # close the file dialog box on OS X
if not master.filename:
    sys.exit(1)

dcmdir = os.path.dirname(master.filename)
# do we have a nii or a dcmdir?
nii = ""
if re.match('.*\.nii(\.gz)?$', master.filename):
    nii = master.filename

# get id from dicom
if re.match('(^MR.*)|(.*IMA)$', master.filename):
    masterdcm = master.filename
    selectedDicom = dicom.read_file(masterdcm)
    subjid = "%s_%s" % (selectedDicom.PatientID, selectedDicom.PatientName)
else:
    subjid = 'unknown'


# ----- define area's used by functions -----

# logging output of commands
logarea = tkinter.scrolledtext.ScrolledText(
    master=master, wrap=WORD)  # ,width=20,height=10)
logarea.tag_config('info', foreground='green')
logarea.tag_config('cmd', foreground='blue')
logarea.tag_config('output', foreground='grey')
logarea.tag_config('error', foreground='red')
logarea.tag_config('alert', foreground='orange')
# display
# photo=tkinter.PhotoImage(file="mprage_bet.pgm")
# photolabel=tkinter.Label(master,image=photo)
photolabel = tkinter.Label(master)

# display options
selectedImg = tkinter.StringVar()
selectedImg.set("mprage_bet.pgm")

# selectedImg.trace set below after function defined
avalImgMenu = tkinter.OptionMenu(master, selectedImg, [])


# ----- functions -----
def logtxt(txt, tag='output'):
    logarea.mark_set(tkinter.INSERT, tkinter.END)
    logarea.config(state="normal")
    logarea.insert(tkinter.INSERT, txt + "\n", tag)
    logarea.config(state="disable")
    logarea.see(tkinter.END)
    logarea.update_idletasks()


def shouldhave(thisfile):
    if not os.path.isfile(thisfile):
        logtxt("ERROR: expected file (%s/%s) does not exist!" %
               (os.getcwd(), thisfile), 'error')


def logruncmd(cmd):
    logtxt("\n[%s %s]" % (datetime.datetime.now(), os.getcwd()), 'info')
    logtxt("%s" % cmd, 'cmd')


def logcmdoutput(p, logit):
    output, error = p.communicate()
    if logit:
        logtxt(output.decode(), 'output')
    if error.decode():
        logtxt("ERROR: " + error.decode(), 'error')


def runcmd(cmd, logit=True):
    if logit:
        logruncmd(cmd)
    p = subprocess.Popen(
        cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logcmdoutput(p, logit)

# copy nii or make form dicom (mprage1.nii.gz)


def getInitialInput():
    # dcm2niix will put the echo number if we ask for it or not
    if(nii == ""):
        runcmd("dcm2niix -o ./ -f mprage%%e %s" % dcmdir)
    else:
        runcmd("3dcopy %s mprage1.nii" % nii)

    resample()
    updateimg('mprage1_res.nii')
    skullstrip()


def change_img(pgmimg):
    newimg = tkinter.PhotoImage(file=pgmimg)
    photolabel.image = newimg
    photolabel.configure(image=newimg)
    photolabel.update_idletasks()


def update_menu_list(menu, newlist):
    menu['menu'].delete(0, "end")
    for choice in newlist:
        menu['menu'].add_command(
            label=choice, command=tkinter._setit(selectedImg, choice))

# search for new images to update the menu


def update_img_menu():
    allimages = glob.glob('*.pgm')
    update_menu_list(avalImgMenu, allimages)

# take a nii, and show the slicer version of it


def updateimg(niiimg, overlay="", pgmimg=""):
    if pgmimg == "":
        # pgmimg=niiimg.replace(".nii.gz",".pgm")
        pgmimg = re.sub('.nii(.gz)?$', '.pgm', niiimg)
    runcmd("slicer %s %s -a %s " % (overlay, niiimg, pgmimg), logit=False)
    update_img_menu()
    selectedImg.set(pgmimg)
    # change_img(pgmimg)

# change from menu


def change_img_from_menu(*args):
    pgmimg = selectedImg.get()
    change_img(pgmimg)

# get original resolution
# keep as string for passing back into resample


def get_dxyz(img):
    orig = subprocess.check_output(['3dinfo', '-ad3', img])
    return(orig.decode().replace('\t', ' ').replace('\n', ''))
    # res=[ float(x) for x in orig.decode().split(' ')]
    # return(res)


def resample(*args):
    # what are our resample dimenstions?
    # orig = get_dxyz('mprage1.nii')
    # min_d=min([ float(x) for x in orig.split(' ')])
    # -- instead always use 2mm
    if shouldresample.get():  # and min_d < 1:
        runcmd(
            "3dresample -overwrite -inset mprage1.nii -dxyz 2 2 2 -prefix mprage1_res.nii.gz")
    else:
        shouldresample.set(0)
        runcmd("3dcopy -overwrite mprage1.nii mprage1_res.nii.gz")
    shouldhave('mprage1_res.nii.gz')


def skullstrip():
    runcmd(
        "bet mprage1_res.nii.gz mprage_bet.nii.gz -f %.02f" %
        betscale.get())
    shouldhave('mprage_bet.nii.gz')
    updateimg('mprage_bet.nii.gz')


def run_robex():
    # this takes a while, so make sure we want to do it
    prompt = tkinter.messagebox.askokcancel(
               "runROBEX",
               "This will take a while, are you sure?")
    # return to gui if we dont didn't confirm
    if not prompt:
        return()
    # otherwise, proceed
    runcmd("runROBEX.sh mprage1_res.nii.gz mprage_bet.nii.gz")
    shouldhave('mprage_bet.nii.gz')
    updateimg('mprage_bet.nii.gz')


def warp():
    runcmd(
        "flirt -in %s -ref mprage_bet.nii.gz -omat direct_std2native_aff.mat -out std_in_native.nii.gz -dof 12 -interp spline" %
        templatebrain)
    runcmd(
        "applyxfm4D %s mprage_bet.nii.gz slice_mprage_rigid.nii.gz direct_std2native_aff.mat -singlematrix" %
        atlas)
    runcmd("slicer slice_mprage_rigid.nii.gz -a slice_only.pgm", logit=False)
    updateimg('slice_mprage_rigid.nii.gz', '', 'slice_only.pgm')
    updateimg('mprage_bet.nii.gz', 'slice_mprage_rigid.nii.gz', 'betRed.pgm')
    updateimg('slice_mprage_rigid.nii.gz', 'mprage_bet.nii.gz', 'sliceRed.pgm')
    logtxt("[%s] warp finished!" % datetime.datetime.now(), tag='alert')


def saveandafni():
    mpragefile = 'mprage1_res.nii'
    # maybe we are using compression:
    if not os.path.isfile(mpragefile):
        mpragefile = mpragefile + '.gz'

    mprage = nipy.load_image(mpragefile)
    sliceimg = nipy.load_image('slice_mprage_rigid.nii.gz')

    # add slice line to mprage usign nipy
    t1andslc = mprage.get_data()
    intensityval = numpy.percentile(t1andslc[t1andslc > 0], 90)
    t1andslc_data = (intensityval * (sliceimg.get_data() > 0)) + t1andslc

    # save new image out
    t1andslc = mprage.from_image(mprage, data=t1andslc_data)
    nipy.save_image(t1andslc, 'anatAndSlice_res.nii.gz')
    # update window
    updateimg('anatAndSlice_res.nii.gz', '', 'anatAndSlice.pgm')

    # resample back
    origdxyz = get_dxyz('mprage1.nii')
    if(origdxyz != get_dxyz('anatAndSlice_res.nii.gz')):
        runcmd(
            '3dresample -overwrite -inset anatAndSlice_res.nii.gz -dxyz %s -prefix anatAndSlice_unres.nii.gz' %
            origdxyz)
    # start afni
    subprocess.Popen(
        ['afni', '-com', 'SET_UNDERLAY anatAndSlice_unres.nii.gz'])
    subprocess.Popen([filebrowser, tempdir])

    # ----- finally write out dicoms -----
    # write it out as a dicom, using matlab
    mlcmd = "rewritedcm('%s','%s')" % (
        dcmdir, os.path.join(tempdir, 'anatAndSlice_unres.nii.gz'))
    mlfull = [
        'matlab',
        '-nodisplay',
        '-r',
        "try, addpath('%s');%s;catch e, disp(e), end, quit()" %
        (origdir,
         mlcmd)]
    cmdstr = ' '.join(mlfull)
    logruncmd(cmdstr)
    logarea.config(state="normal")

    print(cmdstr)
    # run matlab in an empty enviornment so we dont get ls colors
    mlp = subprocess.Popen(
        mlfull,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            'PATH': os.environ['PATH'],
            'TERM': ""})
    logcmdoutput(mlp, True)

    # # using python
    # print('rewritedcm("%s","anatAndSlice_unres.nii.gz")'%dcmdir)
    # rewritedcm(dcmdir, 'anatAndSlice_unres.nii.gz')
    # # so we can copy from it?


def copyback():
    """copy newly created dicom folder back to original dicom folder location
    """
    # we'll create a new directory at the same level
    # as the one we got dicoms from
    # this is probably mrpath: '/Volumes/Disk_C/Temp/'
    copytodir = os.path.dirname(dcmdir)
    # YYYYMMDD_mlBrainStrip_SeriesDescrp is the default name from rewritedcm.m
    # we may want to change this to the python output at some time
    # (like when ML lisc expires)
    mldirpatt = datetime.datetime.now().strftime('%Y%m%d_mlBrainStrip_*/')
    mldir = glob.glob(mldirpatt)
    if len(mldir) < 1:
        print("NO matlab dir %s" % mldirpatt)
        return()
    mldir = mldir[0]
    copyname = os.path.join(copytodir, os.path.basename(mldir))
    if os.path.isdir(copyname):
        print("ALREADY HAVE %s" % copyname)
    else:
        copy_tree(mldir, copyname)


###################
# ----- go to new directory -----
tempdir = tempfile.mkdtemp(dir=outputdirroot, prefix=subjid)
print(tempdir)
os.chdir(tempdir)
# os.symlink(atlas, './')

# ----- startup -----
logtxt("reading from " + dcmdir)
logtxt("saving files to " + tempdir)

selectedImg.trace("w", change_img_from_menu)

# ----- frames -----
bframe = tkinter.Frame(master)
bframe.pack(side="left")

# skull strip (brain extract - bet)  setting
betscale = tkinter.Scale(bframe, from_=1, to=0, resolution=.05)
betscale.set(.5)

# ----- buttons -----
betgo = tkinter.Button(bframe, text='0. re-strip', command=skullstrip)
robexgo = tkinter.Button(bframe, text='0. alt-robex', command=run_robex)
warpgo = tkinter.Button(bframe, text='1. warp', command=warp)
makego = tkinter.Button(bframe, text='2. make', command=saveandafni)
copygo = tkinter.Button(bframe, text='3. copy back', command=copyback)

# checkbox
shouldresample = tkinter.IntVar()
shouldresample.set(1)
resampleCheck = tkinter.Checkbutton(
    master, text="2mm?", variable=shouldresample)
resampleCheck.var = shouldresample
shouldresample.trace("w", resample)

betscale.pack(side="left")
betgo.pack(side="top")
robexgo.pack(side="top")
warpgo.pack(side="top")
makego.pack(side="top")
copygo.pack(side="top")
resampleCheck.pack(side="bottom")

# ----- image menu and log -----
avalImgMenu.pack()
photolabel.pack()
logarea.pack()
#
# #redogo.pack()


# ----- start -----
# run dicom2nii (and skull strip) or 3dcopy as soon as we launch
master.after(0, getInitialInput)
# show the gui
tkinter.mainloop()

# ----- remove tempdir ------
# TODO: maybe keep? as subject name? want coeffs
os.chdir(origdir)
# shutil.rmtree(tempdir)
