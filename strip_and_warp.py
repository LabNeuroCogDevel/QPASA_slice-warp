#!/usr/bin/env python3
import tkinter 
from tkinter import filedialog, scrolledtext, WORD

import tempfile, os, os.path
import sys
import subprocess
import datetime
import shutil
import glob
import re


## settings
origdir=os.getcwd()
initialdir = "/Volumes/Phillips/Raw/MRprojects/mMRDA-dev/2015.09.18-08.35.03/B0070/Sagittal_MPRAGE_ADNI_256x240.29/"
templatebrain="/opt/ni_tools/standard/mni_icbm152_nlin_asym_09c/mni_icbm152_t1_tal_nlin_asym_09c_brain.nii"
atlas="%s/slice_atlas.nii.gz"%origdir



## initialize gui
master = tkinter.Tk()
master.title('Subject Native Slice Orientation')


## get dicom directory
# code hangs here until user makes a choice
master.filename = \
        tkinter.filedialog.askopenfilename(\
                      initialdir = initialdir,\
                      title = "Select a representative DICOM",\
                      filetypes = (("Dicoms","MR*"),("all files","*.*")))
if not master.filename: sys.exit(1)
dcmdir = os.path.dirname(master.filename)


## define area's used by functions

# skull strip (brain extract - bet)  setting
betscale = tkinter.Scale(master, from_=1, to=0, resolution=.05)
betscale.set(.5)

# logging output of commands
logarea = tkinter.scrolledtext.ScrolledText(master=master,wrap=WORD) #,width=20,height=10)
logarea.tag_config('info',foreground='blue')
logarea.tag_config('cmd',foreground='green')
logarea.tag_config('output',foreground='black')
logarea.tag_config('error',foreground='red')
# display
#photo=tkinter.PhotoImage(file="mprage_bet.pgm")
#photolabel=tkinter.Label(master,image=photo)
photolabel=tkinter.Label(master)

# display options
selectedImg = tkinter.StringVar()
selectedImg.set("mprage_bet.pgm")

# selectedImg.trace set below after function defined
avalImgMenu = tkinter.OptionMenu(master, selectedImg, [])



## functions
def logtxt(txt,tag='output'):
   logarea.mark_set(tkinter.INSERT, tkinter.END) 
   logarea.config(state="normal")
   logarea.insert(tkinter.INSERT,txt+"\n",tag)
   logarea.config(state="disable")
   logarea.see(tkinter.END)
   logarea.update_idletasks()

def shouldhave(thisfile):
    if not os.path.isfile(thisfile):
       logtxt("ERROR: expected file (%s/%s) does not exist!"%(os.getcwd(),thisfile),'error')

def runcmd(cmd):
   logtxt("\n[%s %s]"%(datetime.datetime.now(),os.getcwd()),'info')
   logtxt("%s"%cmd,'cmd')
   p = subprocess.Popen(cmd.split(' '),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   output,error = p.communicate()
   logtxt(output.decode(),'output')
   if error.decode():
       logtxt("ERROR: "+error.decode(),'error')

def dicom2nii():
    # dcm2niix will put the echo number if we ask for it or not
    runcmd("dcm2niix -o ./ -f mprage%%e %s"%dcmdir)
    updateimg('mprage1.nii')
    skullstrip()

def change_img(pgmimg):
    newimg=tkinter.PhotoImage(file=pgmimg)
    photolabel.image=newimg
    photolabel.configure(image=newimg)
    photolabel.update_idletasks()

def update_menu_list(menu,newlist):
  menu['menu'].delete(0,"end")
  for choice in newlist:
        menu['menu'].add_command(label=choice, command=tkinter._setit(selectedImg, choice))

# search for new images to update the menu
def update_img_menu():
    allimages=glob.glob('*.pgm')
    update_menu_list(avalImgMenu,allimages)

# take a nii, and show the slicer version of it
def updateimg(niiimg,overlay=""):
    #pgmimg=niiimg.replace(".nii.gz",".pgm")
    pgmimg=re.sub('.nii(.gz)?$','.pgm',niiimg)
    runcmd("slicer %s %s -a %s "%(overlay,niiimg,pgmimg))
    update_img_menu()
    selectedImg.set(pgmimg)
    #change_img(pgmimg)

# change from menu
def change_img_from_menu(*args):
    pgmimg=selectedImg.get()
    change_img(pgmimg)


def skullstrip():
    runcmd("bet mprage1.nii mprage_bet.nii.gz -f %.02f"%betscale.get())
    shouldhave('mprage_bet.nii.gz')
    updateimg('mprage_bet.nii.gz')

def warp():
    runcmd("flirt -in %s -ref mprage_bet.nii.gz -omat direct_std2native_aff.mat -out std_in_native.nii.gz -dof 12 -interp spline"%templatebrain)
    runcmd("applyxfm4D %s mprage_bet.nii.gz slice_mprage_rigid.nii.gz direct_std2native_aff.mat -singlematrix"%atlas)
    runcmd("slicer slice_mprage_rigid.nii.gz -a slice_only.pgm")
    updateimg('mprage_bet.nii.gz','slice_mprage_rigid.nii.gz')

###################

## go to new directory
tempdir=tempfile.mkdtemp()
os.chdir(tempdir)

## startup
logtxt("reading from "    + dcmdir )
logtxt("saving files to " + tempdir )

## buttons 

selectedImg.trace("w", change_img_from_menu)
betgo  = tkinter.Button(master,text='1. strip',command=skullstrip)
warpgo = tkinter.Button(master,text='2. warp',command=warp)


## display
betscale.pack(side="left")
betgo.pack(side="left")
warpgo.pack(side="left")
avalImgMenu.pack()
photolabel.pack(side="bottom")
logarea.pack(side="bottom")
#redogo.pack()

## start
# run dicom2nii (and skull strip) as soon as we launch
master.after(0,dicom2nii) 
# show the gui
tkinter.mainloop()

## remove tempdir
#TODO: maybe keep? as subject name? want coeffs
os.chdir(origdir)
shutil.rmtree(tempdir)
