from distutils.dir_util import copy_tree
import datetime
import glob
import re
import os
import sys
import tkinter
from tkinter import WORD
import tempfile
import subprocess
import nipy
import numpy

import inhomfft
import ratthres
from logfield import LogField
from tooltip import ToolTip
from image_preview import ImagePreview

def bname(path):
    """basename that works for folders
    >>> bname('/a/b/')
    'b'
    >>> bname('/a/b')
    'b'
    """
    return [x for x in path.split(os.path.sep) if x][-1]

def get_dxyz(img):
    """dims of nifti from 3dinfo as string
    >>> get_dxyz('example/MPRAGE.nii')
    '1.718750 1.718750 1.950000'
    """
    orig = subprocess.check_output(['3dinfo', '-ad3', img])
    return orig.decode().replace('\t', ' ').replace('\n', '')
    # res=[ float(x) for x in orig.decode().split(' ')]
    # return(res)


def add_slice(mpragefile, atlas_fname='slice_mprage_rigid.nii.gz'):
    mprage = nipy.load_image(mpragefile)
    t1 = mprage.get_data()

    sliceimg = nipy.load_image(atlas_fname)
    slice_atlas = sliceimg.get_data()

    if(numpy.max(t1) < 10000):
        intensity_fix = 10000
    else:
        intensity_fix = 1

    # add slice
    intensityval = numpy.percentile(t1[t1 > 0], 90)
    t1andslc_data = (intensityval * (slice_atlas > 0)) + t1

    # fix low range so exam cart can see mprage
    t1andslc_data = t1andslc_data * intensity_fix
    t1andslc = mprage.from_image(mprage, data=t1andslc_data)
    return  t1andslc


class SliceWarp:
    def __init__(self, master, template, atlas):

        self.slice_mni = atlas
        self.template_brain = template
        self.master = master
        # logging output of commands
        self.logarea = tkinter.scrolledtext.ScrolledText(
            master=master, wrap=WORD)  # ,width=20,height=10)
        self.logfield = LogField(self.logarea)

        # will need to pack
        # imgview.photolabel and avalImgMenu
        self.imgview = ImagePreview(master, self.logfield.runcmd)

        # will store later
        self.tempdir = None
        self.dcmdir = None


        # ----- frames -----
        bframe = tkinter.Frame(master)
        stripframe = tkinter.Frame(bframe)
        scaleframe = tkinter.Frame(bframe)
        scaleframe.pack(side="left")
        bframe.pack(side="left")

        # --- sliders ---
        # skull strip (brain extract - bet)  setting
        self.betscale = tkinter.Scale(scaleframe, from_=1, to=0, resolution=.05)
        self.betscale.set(.5)

        # upper value threshold percent
        self.thres_slider = tkinter.Scale(scaleframe, from_=.1, to=2, resolution=.05)
        self.thres_slider.set(.5)

        # ----- buttons -----
        redogo = tkinter.Button(stripframe, text='0. start over',
                                command=self.reset_initial)
        ToolTip(redogo, 'reset mprage1_res.nii.gz to initial state.\n'+
                "NEEDED before reapplying step 1: bias correction")

        biasgo = tkinter.Button(stripframe, text='1. brighten',
                                command=self.bias_correct)
        ToolTip(biasgo, 'inhom bias corrction. GRAPPA T1 need FFT shift.\nNOT NEEDED for  MP2RAGE')

        thresgo = tkinter.Button(stripframe, text='2. remove artifact',
                                 command=self.apply_threshold)
        ToolTip(thresgo, 'apply thresh to remove bright spot in nasal cavity inhabiting skullstrip.' +
                '\nartifact introduced by GRAPPA bias correction')

        betgo = tkinter.Button(stripframe, text='(re)strip', command=self.skullstrip)
        ToolTip(betgo, "skull strip with FSL's BET program." +
                " use 'skull' slider to adjust how much is removed")

        robexgo = tkinter.Button(stripframe, text='robex (slow)', command=self.run_robex)
        ToolTip(robexgo, "slower 'robust brain extraction' might do better")

        warpgo = tkinter.Button(bframe, text='4. warp', command=self.warp)
        ToolTip(warpgo, "use FSL flirt. *linear* warp T1<->MNI.\n"+
                "START HERE if everything looks good at launch")

        makego = tkinter.Button(bframe, text='5. make', command=self.saveandafni)
        ToolTip(makego, "Reverse warp atlas to subject. launch AFNI to inspect")

        copygo = tkinter.Button(bframe, text='6. copy back', command=self.copyback)
        ToolTip(copygo, "copy dicom with altas imposed back to scanner")

        sharego = tkinter.Button(bframe, text='7. watermark', command=self.brainimgageshare)
        ToolTip(sharego, "launch watermarking program: brain image share")

        #  --- checkbox
        # resample to 2mm
        self.shouldresample = tkinter.IntVar()
        self.shouldresample.set(1)
        resampleCheck = tkinter.Checkbutton(
            master, text="2mm?", variable=self.shouldresample)
        resampleCheck.var = self.shouldresample
        self.shouldresample.trace("w", self.resample)

        # normalize to backup/original mprage
        should_norm = tkinter.IntVar()
        should_norm.set(1)
        norm_check = tkinter.Checkbutton(master, text="norm?", variable=should_norm)
        norm_check.var = should_norm

        tkinter.Label(scaleframe, text="skull  thres").pack(side="top")
        self.betscale.pack(side="left")
        self.thres_slider.pack(side="right")

        stripframe.pack(side="top")
        redogo.pack(side="top")
        biasgo.pack(side="top")
        thresgo.pack(side="top")
        tkinter.Label(stripframe, text="3.").pack(side="left")
        betgo.pack(side="left")
        robexgo.pack(side="left")

        warpgo.pack(side="top")
        makego.pack(side="top")
        copygo.pack(side="top")
        sharego.pack(side="top")
        resampleCheck.pack(side="bottom")
        # norm_check.pack(side="bottom")

        # ----- image menu and log -----
        self.imgview.avalImgMenu.pack()
        self.imgview.photolabel.pack()
        self.logarea.pack()

    def updateimg(self, *args):
        "lazy wrapper for imgview so we dont have to change code everywhere"
        self.imgview.updateimg(*args)

    def start(self, dcmdir, outputdirroot, subjid):
        self.dcmdir = dcmdir
        # ----- go to new directory -----
        self.tempdir = tempfile.mkdtemp(dir=outputdirroot, prefix=subjid)
        print(self.tempdir)
        os.chdir(self.tempdir)
        # os.symlink(atlas, './')

        # ----- startup -----
        self.logfield.logtxt("reading from " + dcmdir)
        self.logfield.logtxt("saving files to " + self.tempdir)

        # ----- start -----
        # run dicom2nii (and skull strip) or 3dcopy as soon as we launch
        self.master.after(0, self.getInitialInput)
        # show the gui
        tkinter.mainloop()



    # ## -- copy nii or make form dicom (mprage1.nii.gz)
    def backup(self):
        """
        create a copy of initial that we can return to if bias or thres is wonky
        """
        cmd = '3dcopy mprage1_res.nii.gz mprage1_res_backup.nii.gz'
        self.logfield.runcmd(cmd)

    def make_input(self):
        # dcm2niix will put the echo number if we ask for it or not
        # do we have a nii or a dcmdir?
        if re.match('.*\.nii(\.gz)?$', self.master.filename):
            self.logfield.runcmd("3dcopy %s mprage1.nii" % self.master.filename)
        else:
            self.logfield.runcmd("dcm2niix -o ./ -f mprage%%e %s" % self.dcmdir)


    def getInitialInput(self):
        """setup input file and run quick (inhomo+bet) steps with the default parameters"""
        self.make_input()
        self.resample()
        self.updateimg('mprage1_res.nii.gz')
        self.backup()

        # dont do anything when test
        if len(sys.argv) > 1 and "test" in sys.argv:
            return

        # bias and threshold added after transition to grappa
        # TODO: check if dicom and protocol is grapa?
        self.bias_correct()
        self.apply_threshold()
        self.skullstrip()



    # get original resolution
    # keep as string for passing back into resample


    def resample(self, *args):
        # what are our resample dimenstions?
        # orig = get_dxyz('mprage1.nii')
        # min_d=min([ float(x) for x in orig.split(' ')])
        # -- instead always use 2mm
        if self.shouldresample.get():  # and min_d < 1:
            cmd = "3dresample -overwrite -inset mprage1.nii -dxyz 2 2 2 -prefix mprage1_res.nii.gz"
        else:
            self.shouldresample.set(0)
            cmd = "3dcopy -overwrite mprage1.nii mprage1_res.nii.gz"

        self.logfield.runcmd(cmd)
        self.logfield.shouldhave('mprage1_res.nii.gz')


    def apply_threshold(self,
            inname="mprage1_res.nii.gz",
            outname="mprage1_res.nii.gz", backup=True):
        """ get ratio of max slider value and remove from image"""
        if inname == outname:
            # prethres = "mprage1_res_prethres.nii.gz"
            prethres = re.sub('.nii.gz$', '_prethres.nii.gz', inname)
            if not os.path.exists(prethres) or not backup:
                self.logfield.runcmd("3dcopy -overwrite %s %s" % (inname, prethres))
            inname = prethres

        sliderval = self.thres_slider.get()
        # maxval = ratthres.get_3dmax(inname)
        p80 = ratthres.get_3d80p(inname)
        cmd = '3dcalc -overwrite -a %s -expr a*step(%s/%.02f-a) -prefix %s' %\
              (inname, p80, sliderval, outname)
        self.logfield.runcmd(cmd)
        # logtxt("threshold %s %s @ %.2f*max" % (inname, outname, rat), tag='cmd')
        # resave_nib(inname, outname, lambda d: zero_thres(d, rat))
        self.updateimg(outname)


    def reset_initial(self,
            inname="mprage1_res_backup.nii.gz",
            outname="mprage1_res.nii.gz"):
        """copy old backup to starting"""
        self.logfield.runcmd('3dcopy -overwrite %s %s' % (inname, outname))

        prethres = "mprage1_res_prethres.nii.gz"
        if os.path.exists(prethres):
            self.logfield.runcmd('rm %s' % prethres)

        self.updateimg(outname)


    def bias_correct(self, inname="mprage1_res.nii.gz", outname="mprage1_res.nii.gz"):
        """run fft/fftshift/ifft to correct bias in 7T grappa
        N.B. defaults to rewritting input (mprage1_res.nii.gz)"""
        self.logfield.logtxt("inhomfft %s %s" % (inname, outname), tag='cmd')
        inhomfft.rewrite(inname, outname)
        self.logfield.runcmd('3dcopy -overwrite %s biascor.nii.gz' % outname)
        self.updateimg(outname)


    def skullstrip_bias(self,
                        inname="mprage1_res.nii.gz",
                        outname="mprage1_res_inhomcor.nii.gz"):
        """ skullstrip with inhomo fft fixed input"""
        if not os.path.exists(outname):
            self.logfield.logtxt("inhomfft %s %s" % (inname, outname), tag='cmd')
            inhomfft.rewrite(inname, outname)
        self.skullstrip(outname)


    def skullstrip(self, fname="mprage1_res.nii.gz"):
        self.logfield.runcmd(
            "bet %s mprage_bet.nii.gz -f %.02f" %
            (fname, self.betscale.get()))
        self.logfield.shouldhave('mprage_bet.nii.gz')
        self.updateimg('mprage_bet.nii.gz')


    def run_robex(self):
        """run robex after slow prompt/warning"""
        # this takes a while, so make sure we want to do it
        prompt = tkinter.messagebox.askokcancel(
                   "runROBEX",
                   "This will take a while, are you sure?")
        # return to gui if we dont didn't confirm
        if not prompt:
            return()
        # otherwise, proceed
        self.logfield.runcmd("runROBEX.sh mprage1_res.nii.gz mprage_bet.nii.gz")
        self.logfield.shouldhave('mprage_bet.nii.gz')
        self.updateimg('mprage_bet.nii.gz')


    def warp(self):
        self.logfield.runcmd(
            "flirt -in %s -ref mprage_bet.nii.gz -omat direct_std2native_aff.mat -out std_in_native.nii.gz -dof 12 -interp spline" %
            self.template_brain)
        self.logfield.runcmd(
            "applyxfm4D %s mprage_bet.nii.gz slice_mprage_rigid.nii.gz direct_std2native_aff.mat -singlematrix" %
            self.slice_mni)
        self.logfield.runcmd("slicer slice_mprage_rigid.nii.gz -a slice_only.pgm", logit=False)
        self.updateimg('slice_mprage_rigid.nii.gz', '', 'slice_only.pgm')
        self.updateimg('mprage_bet.nii.gz', 'slice_mprage_rigid.nii.gz', 'betRed.pgm')
        self.updateimg('slice_mprage_rigid.nii.gz', 'mprage_bet.nii.gz', 'sliceRed.pgm')
        self.logfield.logtxt("[%s] warp finished!" % datetime.datetime.now(), tag='alert')


    def saveandafni(self):
        mpragefile = 'mprage1_res.nii'
        # maybe we are using compression:
        if not os.path.isfile(mpragefile):
            mpragefile = mpragefile + '.gz'

        intensity_corrected = "mprage1_res_inhomcor.nii.gz"
        if os.path.isfile(intensity_corrected):
            mpragefile = intensity_corrected

        t1andslc = add_slice(mpragefile)
        nipy.save_image(t1andslc, 'anatAndSlice_res.nii.gz')
        # update window
        self.updateimg('anatAndSlice_res.nii.gz', '', 'anatAndSlice.pgm')

        # resample back
        origdxyz = get_dxyz('mprage1.nii')
        self.logfield.runcmd('3dresample -overwrite -inset anatAndSlice_res.nii.gz -dxyz %s -prefix anatAndSlice_unres.nii.gz' %
               origdxyz)

        # start afni
        subprocess.Popen(
            ['afni', '-com', 'SET_UNDERLAY anatAndSlice_unres.nii.gz',
                '-com', 'OPEN_WINDOW axialimage mont=3x3:5',
                '-com', 'OPEN_WINDOW sagittalimage mont=3x3:5',
                '-com', 'SET_OVERLAY slice_mprage_rigid.nii.gz',
                '-com', 'SET_XHAIRS SINGLE',
                '-com', 'SET_PBAR_SIGN +'])
        subprocess.Popen([FILEBROWSER, self.tempdir])

        # ----- finally write out dicoms -----
        # write it out as a dicom, using matlab
        mlcmd = "rewritedcm('%s','%s')" % (
            dcmdir, os.path.join(self.tempdir, 'anatAndSlice_unres.nii.gz'))
        mlfull = [
            'matlab',
            '-nodisplay',
            '-r',
            "try, addpath('%s');%s;catch e, disp(e), end, quit()" %
            (ORIGDIR,
             mlcmd)]
        cmdstr = ' '.join(mlfull)
        self.logfield.logruncmd(cmdstr)
        self.logarea.config(state="normal")

        print(cmdstr)

        # run matlab in an empty enviornment so we dont get ls colors
        mlp = subprocess.Popen(
            mlfull,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                'PATH': os.environ['PATH'],
                'TERM': ""})
        self.logfield.logcmdoutput(mlp, True)

        # # using python
        # print('rewritedcm("%s","anatAndSlice_unres.nii.gz")'%dcmdir)
        # rewritedcm(dcmdir, 'anatAndSlice_unres.nii.gz')
        # # so we can copy from it?


    def brainimgageshare(self):
        # nii or nii.gz
        orig_mprage = os.path.join(self.tempdir, "mprage1.nii.gz")
        if not os.path.isfile(orig_mprage):
            orig_mprage = os.path.join(self.tempdir, "mprage1.nii")

        cmd = ["python3", "-m", "brainimageshare", orig_mprage]
        self.logfield.logruncmd(" ".join(cmd))
        # os.spawnl(os.P_NOWAIT, *cmd)
        subprocess.Popen(cmd)


    def copyback(self):
        """copy newly created dicom folder back to original dicom folder location
        """
        # we'll create a new directory at the same level
        # as the one we got dicoms from
        # this is probably mrpath: '/Volumes/Disk_C/Temp/'
        copytodir = os.path.dirname(self.dcmdir)
        # YYYYMMDD_mlBrainStrip_SeriesDescrp is the default name from rewritedcm.m
        # we may want to change this to the python output at some time
        # (like when ML lisc expires)
        mldirpatt = datetime.datetime.now().\
            strftime('%Y%m%d_*_mlBrainStrip_*/')
        # actual name is with hhmmss -- but that was some time ago
        # strftime('%Y%m%d_%H%M%S_mlBrainStrip_*/')

        mldirpattfull = os.path.join(self.tempdir, mldirpatt)
        mldir = glob.glob(mldirpattfull)
        if len(mldir) < 1:
            self.logfield.logtxt("did you make? new dicom dir DNE: %s" % mldirpattfull, 'error')
            return()
        if len(mldir) > 1:
            self.logfield.logtxt("have more than 1 %s!" % mldirpattfull, 'alert')
            return()
        # we only want the last (and hopefuly only match)
        mldir = mldir[-1]

        # we'll copy it to the DICOM dir
        copyname = os.path.join(copytodir, bname(mldir))
        if os.path.isdir(copyname):
            self.logfield.logtxt("already have copied directory %s" % copyname, 'alert')
        else:
            copy_tree(mldir, copyname)
            self.logfield.logtxt("copied warped slice to %s" % copyname, 'info')
