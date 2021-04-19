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
import pydicom

import inhomfft
import ratthres
from logfield import LogField
from tooltip import ToolTip
from image_preview import ImagePreview
from settings import FILEBROWSER, ORIGDIR
from rewritedcm import rewritedcm


def bname(path):
    """basename that works for folders
    >>> bname('/a/b/')
    'b'
    >>> bname('/a/b')
    'b'
    """
    return [x for x in path.split(os.path.sep) if x][-1]


def maybe_add_gz(fname):
    "add gz to make .nii.gz if .nii doesn't exist"
    if not os.path.isfile(fname):
        fname = fname + '.gz'
    return fname


def get_dxyz(img):
    """dims of nifti from 3dinfo as string
    >>> get_dxyz('example/MPRAGE.nii')
    '1.718750 1.718750 1.950000'
    """
    orig = subprocess.check_output(['3dinfo', '-ad3', img])
    return orig.decode().replace('\t', ' ').replace('\n', '')
    # res=[ float(x) for x in orig.decode().split(' ')]
    # return(res)


def show_mni_slice(win, show_file=None):
    """setup example slice image. implemented but unused 20210415"""
    if show_file is None:
        show_file = os.path.dirname(os.path.abspath(__file__)) + '/slice_atlas.png'
    exslice_img = tkinter.PhotoImage(file=show_file)
    mni_img = tkinter.Label(win)
    mni_img.image = exslice_img
    mni_img.configure(image=exslice_img)
    mni_img.update_idletasks()
    return mni_img


def subjid_from_dcm(filename):
    """extract PAT ID from dicom so temp folder can have recognizable name
    >>> subjid_from_dcm('example/20210220_grappa/20210220LUNA1.MR.TIEJUN_JREF-LUNA.0013.0001.2021.02.20.14.34.40.312500.263962728.IMA')
    '1_20210220Luna1'
    """
    # get id from dicom
    if re.match('(^MR.*)|(.*IMA)$', filename):
        selectedDicom = pydicom.read_file(filename)
        subjid = "%s_%s" % (selectedDicom.PatientID, selectedDicom.PatientName)
    else:
        subjid = 'unknown'
    return subjid


def add_slice(mpragefile, atlas_fname='slice_mprage_rigid.nii.gz', adjust_intensity=True):
    """add slice warped into native space to mprage"""
    mprage = nipy.load_image(mpragefile)
    t1 = mprage.get_data()

    sliceimg = nipy.load_image(atlas_fname)
    slice_atlas = sliceimg.get_data()

    # if bias correction removed DC component. add intensity back
    # should also be corrected in inhomofft
    # ..and we should be using original
    # ..and dcm maxintensity=1000 in rewritedcm.m
    if numpy.max(t1) < 10000 and adjust_intensity:
        intensity_fix = 10000
    else:
        intensity_fix = 1

    # add slice
    intensityval = numpy.percentile(t1[t1 > 0], 90)
    t1andslc_data = (intensityval * (slice_atlas > 0)) + t1

    # fix low range so exam cart can see mprage
    t1andslc_data = t1andslc_data * intensity_fix
    t1andslc = mprage.from_image(mprage, data=t1andslc_data)
    return t1andslc


class SliceWarp:
    """main gui"""

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
        self.subjid = None

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
        ToolTip(redogo, 'reset mprage1_res.nii.gz to initial state.\n' +
                "NEEDED before reapplying step 1: bias correction")

        biasgo = tkinter.Button(stripframe, text='1. brighten',
                                command=self.bias_correct)
        ToolTip(biasgo, 'inhom bias corrction. GRAPPA T1 need FFT shift.\n' +
                'NOT NEEDED for  MP2RAGE')

        afni_biasgo = tkinter.Button(stripframe, text='brighten (Alt)',
                                     command=self.bias_correct)
        ToolTip(afni_biasgo, 'Alternative to brighten.\n' +
                             'Bias corrction with AFNIs Unifize.')

        thresgo = tkinter.Button(stripframe, text='2. remove artifact',
                                 command=self.apply_threshold)
        ToolTip(thresgo, 'apply thresh to remove bright spot in nasal cavity inhabiting skullstrip.' +
                '\nartifact introduced by GRAPPA bias correction')

        betgo = tkinter.Button(stripframe, text='(re)strip',
                               command=self.skullstrip)
        ToolTip(betgo, "skull strip with FSL's BET program." +
                " use 'skull' slider to adjust how much is removed\n" +
                "high value removes more")

        robexgo = tkinter.Button(stripframe, text='robex (slow)',
                                 command=self.run_robex)
        ToolTip(robexgo, "slower 'robust brain extraction' might do better")

        warpgo = tkinter.Button(bframe, text='4. warp', command=self.warp)
        ToolTip(warpgo, "use FSL flirt. *linear* warp T1<->MNI.\n" +
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
        resample_check = tkinter.Checkbutton(
            master, text="2mm?", variable=self.shouldresample)
        resample_check.var = self.shouldresample
        self.shouldresample.trace("w", self.resample)

        # normalize to backup/original mprage
        should_norm = tkinter.IntVar()
        should_norm.set(1)
        norm_check = tkinter.Checkbutton(master, text="norm?",
                                         variable=should_norm)
        norm_check.var = should_norm

        tkinter.Label(scaleframe, text="skull  thres").pack(side="top")
        self.betscale.pack(side="left")
        self.thres_slider.pack(side="right")

        stripframe.pack(side="top")
        redogo.pack(side="top", expand="yes", fill="both")
        # bias correction
        #tkinter.Label(stripframe, text="1.").pack(side="top",fill="y")
        biasgo.pack(side="top", fill="both")
        afni_biasgo.pack(side="top", fill="both")
        # thre
        thresgo.pack(side="top", fill="both")
        # skull striping options
        tkinter.Label(stripframe, text="3.").pack(side="left")
        betgo.pack(side="left")
        robexgo.pack(side="left")

        warpgo.pack(side="top", fill="both")
        makego.pack(side="top", fill="both")
        copygo.pack(side="top", fill="both")
        sharego.pack(side="top", fill="both")


        resample_check.pack(side="bottom")
        # norm_check.pack(side="bottom")

        # ----- image menu and log -----
        self.imgview.avalImgMenu.pack()
        self.imgview.photolabel.pack()

        self.logarea.pack()


        # --- menu
        menu = tkinter.Menu(master)
        menu.add_command(label="MNI ideal", command=self.show_ideal)
        menu.add_command(label="finder", command=self.launch_browser)
        menu.add_command(label="another", command=self.open_new)
        menu.add_command(label="prev_folder", command=self.open_prev)
        menu.add_command(label="afni", command=self.launch_afni)
        menu.add_command(label="alt dcm", command=self.alternate_dcms)
        master.config(menu=menu)

        # macOS/OSX (20210419-Sierra 10.12.6) only shows "python" on menubar
        # add a menubutton we can click to get all
        mb=tkinter.Menubutton(master,text="menus")
        mb.menu = tkinter.Menu(mb)
        mb['menu'] = mb.menu
        mb.menu.add_cascade(label="All",menu=menu)
        mb.menu.add_command(label="quit", command=master.quit())
        mb.pack(side="right")


    def updateimg(self, *args):
        "lazy wrapper for imgview so we dont have to change code everywhere"
        self.imgview.updateimg(*args)

    def setup(self, outputdirroot, filename=None):
        """setup based on representative dicom file"""
        if not filename:
            filename = self.master.filename
        self.dcmdir = os.path.abspath(os.path.dirname(filename))
        self.subjid = subjid_from_dcm(filename)
        # ----- go to new directory -----
        self.tempdir = tempfile.mkdtemp(
                dir=outputdirroot,
                prefix=self.subjid + "_")
        print(self.tempdir)
        os.chdir(self.tempdir)
        # os.symlink(atlas, './')

        # ----- startup -----
        self.logfield.logtxt("reading from " + self.dcmdir)
        self.logfield.logtxt("saving files to " + self.tempdir)

    def start(self):
        "run dicom2nii (and skull strip) or 3dcopy as soon as we launch"
        self.master.after(0, self.get_initial_input)
        # show the gui
        tkinter.mainloop()

    def backup(self):
        """
        create a copy of initial so we can return to if bias or thres is wonky
        """
        cmd = '3dcopy mprage1_res.nii.gz mprage1_res_backup.nii.gz'
        self.logfield.runcmd(cmd)

    def make_input(self):
        """initial input to mprage1.nii.gz to start the pipeline
        TODO: master is holding filename. this is a hold over"""
        # dcm2niix will put the echo number if we ask for it or not
        # do we have a nii or a dcmdir?
        if re.match(r'.*\.nii(\.gz)?$', self.master.filename):
            self.logfield.runcmd("3dcopy %s mprage1.nii" % self.master.filename)
        else:
            self.logfield.runcmd("dcm2niix -o ./ -f mprage%%e %s" % self.dcmdir)

    def get_initial_input(self):
        """setup input file and run quick (inhomo+bet)
           steps with the default parameters"""
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

    def resample(self, *args):
        """ slice is in 2mm MNI. use 2mm for native space too
        will need to resample back before putting into dicoms
        """
        if self.shouldresample.get():  # and min_d < 1:
            cmd = "3dresample -overwrite -inset mprage1.nii -dxyz 2 2 2 -prefix mprage1_res.nii.gz"
        else:
            self.shouldresample.set(0)
            cmd = "3dcopy -overwrite mprage1.nii mprage1_res.nii.gz"

        self.logfield.runcmd(cmd)
        self.logfield.shouldhave('mprage1_res.nii.gz')

    def apply_threshold(self,
                        inname="mprage1_res.nii.gz",
                        outname="mprage1_res.nii.gz",
                        backup=True):
        """ get ratio of max slider value and remove from image"""
        if inname == outname:
            # prethres = "mprage1_res_prethres.nii.gz"
            prethres = re.sub('.nii.gz$', '_prethres.nii.gz', inname)
            if not os.path.exists(prethres) or not backup:
                self.logfield.runcmd("3dcopy -overwrite %s %s" % (
                    inname, prethres))
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

    def bias_correct(self,
                     inname="mprage1_res.nii.gz",
                     outname="mprage1_res.nii.gz"):
        """run fft/fftshift/ifft to correct bias in 7T grappa
        N.B. defaults to rewritting input (mprage1_res.nii.gz)"""
        self.logfield.logtxt("inhomfft %s %s" % (inname, outname), tag='cmd')
        inhomfft.rewrite(inname, outname)
        self.logfield.runcmd('3dcopy -overwrite %s biascor.nii.gz' % outname)
        self.updateimg(outname)

    def afni_bias_correct(self,
                          inname="mprage1_res.nii.gz",
                          outname="mprage1_res.nii.gz"):
        """
        remove "shading" artifiact bias field/RF inhomogeneities
        much faster than FSL's FAST. a bit slower than local inhomofft
        """
        cmd = "3dUnifize -overwrite -prefix %s %s" % (inname, outname)
        self.logfield.runcmd(cmd)
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
        "run bet"
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
            return
        # otherwise, proceed
        self.logfield.runcmd("runROBEX.sh mprage1_res.nii.gz mprage_bet.nii.gz")
        self.logfield.shouldhave('mprage_bet.nii.gz')
        self.updateimg('mprage_bet.nii.gz')

    def warp(self):
        """flirt and applyxf4D
        TODO: add option for ANTs?"""
        self.logfield.runcmd(
            "flirt -in %s -ref mprage_bet.nii.gz -omat direct_std2native_aff.mat -out std_in_native.nii.gz -dof 12 -interp spline" %
            self.template_brain)
        self.logfield.runcmd(
            "applyxfm4D %s mprage_bet.nii.gz slice_mprage_rigid.nii.gz direct_std2native_aff.mat -singlematrix" %
            self.slice_mni)
        self.updateimg('std_in_native.nii.gz', 'mprage_bet.nii.gz', 'MNIredBet.pgm')        # mni with bet in red. confirm warp
        self.updateimg('slice_mprage_rigid.nii.gz', '', 'slice_only.pgm')                   # just the slice
        self.updateimg('mprage_bet.nii.gz', 'slice_mprage_rigid.nii.gz', 'betRed.pgm')      # slice with bet edges in red
        self.updateimg('slice_mprage_rigid.nii.gz', 'mprage_bet.nii.gz', 'sliceRed.pgm')    # bet with slice edge in red
        self.logfield.logtxt("[%s] warp finished!" % datetime.datetime.now(), tag='alert')

    def launch_afni(self, underlay='mprage1_res.nii.gz', mont_str=""):
        """launch afni
        """
        # pre 20210415
        # underlay = 'anatAndSlice_unres.nii.gz'
        # mont_str = 'mont=3x3:5'
        overlay = "slice_mprage_rigid.nii.gz"

        # make sure underlay and overlay match space
        self.match_space_tlrc(underlay, overlay)
        subprocess.Popen(
            ['afni', '-com', 'SET_UNDERLAY %s' % underlay,
                '-com', 'OPEN_WINDOW axialimage %s' % mont_str,
                '-com', 'OPEN_WINDOW sagittalimage %s' % mont_str,
                '-com', 'SET_OVERLAY %s' % overlay,
                '-com', 'SET_XHAIRS SINGLE',
                '-com', 'SET_PBAR_SIGN +'])

    def launch_browser(self):
        """show current directory in a file browser
        don't die if this doesn't work"""
        try:
            subprocess.Popen([FILEBROWSER, self.tempdir])
        except Exception:
            pass

    def saveandafni(self):
        "add slice. save. open folder and afni. copy back to dicom"
        self.make_with_slice()
        # set mprage1_res.nii.gz  to TLRC. probably done in launch_afni,
        # but want to make sure even if mprage1_res is not the underlay
        self.match_space_tlrc()

        # also want the high res original aviable view with slice in afni
        # but is prob ORIG and slice is TLRC.
        # ...another case where putting the slice in ORIG would simplify things
        #
        # created here, but resampled elsewhere
        # launch_afni -> match_space_tlrc : will be refit to match slice
        afni_underlay = "mprage_forafni.nii.gz"
        if not os.path.isfile(afni_underlay):
            self.logfield.runcmd(f"3dcopy mprage1_res_backup.nii.gz {afni_underlay}")
        self.launch_afni(afni_underlay)

        # we might need to drag files back and forth.
        # it'll be useful to be in this weirdly named temp dir
        self.launch_browser()

        # dcm rewrite done last so we can see errors in log window
        self.write_back_to_dicom_ml()


    def alternate_dcms(self, niifile='anatAndSlice_unres_slicefirst.nii.gz'):
        "dcm dirs for higher res slice. and using python"
        if not os.path.isfile(niifile):
            self.logfield.logtxt("Ut Oh!? DNE: " + niifile, 'error')
            return

        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.write_back_to_dicom_ml(niifile, now + '_mlSliceFirst_')
        self.write_back_to_dicom_py(niifile, now + '_pySliceFirst_')


    def match_space_tlrc(self, mpragefile="mprage1_res.nii", atlas_fname='slice_mprage_rigid.nii.gz'):
        """
        for visualizing, we want mprage1_res to match slice_mprage_rigid.nii.gz
        to match slice in orig space
        if atlas_fname doesn't exist, assume TLRC
        """

        # only care if the file we are refiting exists
        if not os.path.exists(mpragefile):
            self.logfield.logtxt("missing %s, not refiting to tlrc" % mpragefile)
            return

        # default to TLRC, but maybe we should put everything in ORIG
        # ...that would be more accurate
        if not atlas_fname or not os.path.exists(atlas_fname):
            space = "TLRC"
        else:
            space = ratthres.cmd_single_out(["3dinfo", "-space", atlas_fname])

        # no need to run if they already match
        cur_space = ratthres.cmd_single_out(["3dinfo", "-space", mpragefile])
        if cur_space == space:
            return

        cmd = '3drefit -space %s %s' % (space, mpragefile)
        self.logfield.runcmd(cmd)

    def make_with_slice(self, mpragefile='mprage1_res.nii', origfile='mprage1.nii'):
        """add slice to initial image (with skull)"""
        # maybe we are using compression:
        mpragefile = maybe_add_gz(mpragefile)
        origfile = maybe_add_gz(origfile)

        if not os.path.isfile(mpragefile):
            self.logfield.logtxt("Ut Oh!? DNE: %s" % mpragefile, 'error')
            return
        # why do we care if the slice is put on top of the bias corrected image?
        #intensity_corrected = "mprage1_res_inhomcor.nii.gz"
        #if os.path.isfile(intensity_corrected):
        #    mpragefile = intensity_corrected

        t1andslc = add_slice(mpragefile)
        nipy.save_image(t1andslc, 'anatAndSlice_res.nii.gz')
        # update window
        self.updateimg('anatAndSlice_res.nii.gz', '', 'anatAndSlice.pgm')

        # resample back
        origdxyz = get_dxyz(origfile)
        self.logfield.runcmd('3dresample -overwrite -inset anatAndSlice_res.nii.gz -dxyz %s -prefix anatAndSlice_unres.nii.gz' %
               origdxyz)

        # try going the other direction
        self.logfield.runcmd('3dresample -overwrite -inset slice_mprage_rigid.nii.gz -master %s -prefix slice_mprage_unres.nii.gz -rmode NN' %
                origfile)
        t1slc_unres = add_slice(origfile, 'slice_mprage_unres.nii.gz', adjust_intensity=False)
        nipy.save_image(t1slc_unres, 'anatAndSlice_unres_slicefirst.nii.gz')


    def write_back_to_dicom_py(self, niifile='anatAndSlice_unres.nii.gz', prefix=None):
        """using python instead of matlab to create new dicoms with slice
        TODO: something off with dicom ids? scan computer wont read
        """
        self.logfield.logtxt('rewritedcm("%s","%s")' % (self.dcmdir, niifile),
                             'info')
        rewritedcm(self.dcmdir, niifile, protoprefix=prefix)
        # prefix None, then 'pySlice_.....'


    def write_back_to_dicom_ml(self, niifile='anatAndSlice_unres.nii.gz', saveprefix=None):
        """put slice+anat into dicom ready to send back to scanner"""

        # write it out as a dicom, using matlab
        if saveprefix:
            mlcmd = "rewritedcm('%s','%s', '%s')" % (
                self.dcmdir,
                os.path.join(self.tempdir, niifile),
                saveprefix)
        else:
            # savedirprefix matlab default looks like
            # [datestr(now(),'yyyymmdd_HHMMSS') '_mlBrainStrip_' ];
            mlcmd = "rewritedcm('%s','%s')" % (
                self.dcmdir,
                os.path.join(self.tempdir, niifile))
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

    def brainimgageshare(self):
        """launch prog to create brain image to show participant"""
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
            return
        if len(mldir) > 1:
            self.logfield.logtxt("have more than 1 %s!" % mldirpattfull, 'alert')
            return
        # we only want the last (and hopefuly only match)
        mldir = mldir[-1]

        # we'll copy it to the DICOM dir
        copyname = os.path.join(copytodir, bname(mldir))
        if os.path.isdir(copyname):
            self.logfield.logtxt("already have copied directory %s" % copyname, 'alert')
        else:
            copy_tree(mldir, copyname)
            self.logfield.logtxt("copied warped slice to %s" % copyname, 'info')

    def open_prev(self):
        """go to a previous directory"""
        initialdir = os.path.dirname(self.tempdir)
        filename = \
            tkinter.filedialog.askopenfilename(
                initialdir=initialdir,
                title="Select a representative file",
            )
        if not filename:
            self.logfield.logtxt("not loading previous run", tag='error')
            return
        self.master.update()  # close the file dialog box on OS X
        os.chdir(os.path.dirname(filename))
        self.logfield.logtxt("open new folder: %s" % os.getcwd(), tag='info')
        self.imgview.update_img_menu()

        # menu many have changed, but old image is probably still showing
        # try to update that
        self.imgview.change_img_from_menu()

    def show_ideal(self):
        "popup window with ideal slice image"
        win = tkinter.Toplevel(self.master)
        win.title("ideal slice location (MNI)")
        img = show_mni_slice(win)
        img.pack()


    def open_new(self, initialdir=None):
        """start again - open another dicom directory"""
        if not initialdir:
            initialdir = os.path.dirname(self.dcmdir)
        filename = \
            tkinter.filedialog.askopenfilename(
                initialdir=initialdir,
                title="Select a representative DICOM",
            )
        if not filename:
            self.logfield.logtxt("not loading new dcm dir", tag='error')
            return
        self.master.filename = filename
        self.master.update()  # close the file dialog box on OS X
        self.setup(os.path.dirname(self.tempdir), filename)
        self.get_initial_input()
