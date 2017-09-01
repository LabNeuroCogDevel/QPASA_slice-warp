#!/usr/bin/env python3
import tkinter 
from tkinter import filedialog, scrolledtext, WORD, messagebox

import tempfile, os, os.path
import sys
import subprocess
import datetime
import shutil
import glob
import re

import nipy, numpy, dicom


## settings
mrpath='/Volumes/Disk_C/Temp/'

#origdir=os.getcwd()
origdir=os.path.dirname(os.path.realpath(__file__))

#initialdir = "/Volumes/Phillips/Raw/MRprojects/mMRDA-dev/2015.09.18-08.35.03/B0070/Sagittal_MPRAGE_ADNI_256x240.29/"
initialdir = mrpath

templatebrain="/opt/ni_tools/standard/mni_icbm152_nlin_asym_09c/mni_icbm152_t1_tal_nlin_asym_09c_brain.nii"
atlas="%s/slice_atlas.nii.gz"%origdir



## initialize gui
master = tkinter.Tk()
master.title('Subject Native Slice Orientation')

## make sure we have the mount
if not os.path.exists(mrpath): 
 tkinter.messagebox.showerror("Error","MR is not mounted?! (%s)"%mrpath)
 sys.exit(1)


## get dicom directory
# code hangs here until user makes a choice
master.filename = \
        tkinter.filedialog.askopenfilename(\
                      initialdir = initialdir,\
                      title = "Select a representative DICOM",\
		      )
                      #filetypes = (("all files","*.*"),("Dicoms","MR*")))
if not master.filename: sys.exit(1)

# do we havea nii or a dcmdir?
nii    = "";
if re.match('.*\.nii(\.gz)?$',master.filename ) : nii = master.filename

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

# copy nii or make form dicom (mprage1.nii.gz)
def getInitialInput():
    # dcm2niix will put the echo number if we ask for it or not
    if(nii==""):
        runcmd("dcm2niix -o ./ -f mprage%%e %s"%dcmdir)
    else:
        runcmd("3dcopy %s mprage1.nii"%nii)

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
def updateimg(niiimg,overlay="", pgmimg=""):
    if pgmimg=="": pgmimg = re.sub('.nii(.gz)?$','.pgm',niiimg) #pgmimg=niiimg.replace(".nii.gz",".pgm")
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
    updateimg('slice_mprage_rigid.nii.gz','','slice_only.pgm')
    updateimg('mprage_bet.nii.gz','slice_mprage_rigid.nii.gz','betRed.pgm')
    updateimg('slice_mprage_rigid.nii.gz','mprage_bet.nii.gz','sliceRed.pgm')

def saveandafni():
    mpragefile = 'mprage1.nii'
    if not os.path.isfile(mpragefile): mpragefile='mprage1.nii.gz'
    mprage   = nipy.load_image(mpragefile)
    sliceimg = nipy.load_image('slice_mprage_rigid.nii.gz')

    t1andslc = mprage.get_data()
    intensityval = numpy.percentile( t1andslc[t1andslc>0], 90)
    t1andslc_data = (intensityval * (sliceimg.get_data()>0) ) + t1andslc 
    t1andslc      = mprage.from_image(mprage,data=t1andslc_data)
    nipy.save_image(t1andslc,'anatAndSlice.nii.gz')
    updateimg('anatAndSlice.nii.gz','','anatAndSlice.pgm')

    make_dicom(t1andslc_data)

    subprocess.Popen('afni')
    subprocess.Popen(['open', tempdir])

    
    

def make_dicom(niidata):
   savedir = 'slice_warp_dcm'
   if not os.path.exists(savedir): os.mkdir(savedir)

   alldcms=glob.glob(dcmdir + '/*IMA' )
   # niiimg = nipy.load_image(nii)
   # niidata = niiimg.get_data()
   
   # d.pixel_array.shape # niidata.shape
   # (128, 118)          # (96, 118, 128)
   
   ndcm=len(alldcms)
   for i in range(ndcm):
     dcm = alldcms[i]
   
     # transpose directions, flip horz and flip vert
     ndataford = numpy.fliplr( numpy.flipud( niidata[(ndcm-1-i),:,:].transpose() ) )
     outname   = savedir + '/' + os.path.basename(dcm) 
   
     d = dicom.read_file(dcm)
     d.pixel_array.flat = ndataford.flatten()
     d.PixelData = d.pixel_array.tostring()
     d.save_as(outname)


###################

## go to new directory
tempdir=tempfile.mkdtemp()
os.chdir(tempdir)
#os.symlink(atlas, './')

## startup
logtxt("reading from "    + dcmdir )
logtxt("saving files to " + tempdir )

## buttons 

selectedImg.trace("w", change_img_from_menu)
betgo  = tkinter.Button(master,text='1. strip',command=skullstrip)
warpgo = tkinter.Button(master,text='2. warp',command=warp)
savego = tkinter.Button(master,text='3. save',command=saveandafni)


## display
betscale.pack(side="left")
betgo.pack(side="left")
warpgo.pack(side="left")
savego.pack(side="left")
avalImgMenu.pack()
logarea.pack(side="bottom")
photolabel.pack(side="bottom")
#redogo.pack()

## start
# run dicom2nii (and skull strip) or 3dcopy as soon as we launch
master.after(0,getInitialInput) 
# show the gui
tkinter.mainloop()

## remove tempdir
#TODO: maybe keep? as subject name? want coeffs
os.chdir(origdir)
shutil.rmtree(tempdir)
