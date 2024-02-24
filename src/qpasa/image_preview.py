"""
manage option menu and image display
"""
import tkinter
import glob
import re

class ImagePreview:
    """
    create Tk image label and dropdown to select image
    """
    def __init__(self, master, cmd_runner, default_img="mprage_bet.pgm"):
        self.cmd_runner = cmd_runner  # likely logfield.runcmd
        self.selectedImg = tkinter.StringVar()
        self.selectedImg.set(default_img)
        self.selectedImg.trace("w", self.change_img_from_menu)

        self.photolabel = tkinter.Label(master)
        # selectedImg.trace set below after function defined
        self.avalImgMenu = tkinter.OptionMenu(master, self.selectedImg, [])


    def change_img(self, pgmimg):
        newimg = tkinter.PhotoImage(file=pgmimg)
        self.photolabel.image = newimg
        self.photolabel.configure(image=newimg)
        self.photolabel.update_idletasks()


    # search for new images to update the menu
    def update_menu_list(self, menu, newlist):
        """update Tk select dropdown"""
        menu['menu'].delete(0, "end")
        for choice in newlist:
            menu['menu'].add_command(
                label=choice, command=tkinter._setit(self.selectedImg, choice))

    def update_img_menu(self):
        allimages = glob.glob('*.pgm')
        self.update_menu_list(self.avalImgMenu, allimages)

    # take a nii, and show the slicer version of it
    def updateimg(self, niiimg, overlay="", pgmimg=""):
        if pgmimg == "":
            # pgmimg=niiimg.replace(".nii.gz",".pgm")
            pgmimg = re.sub('.nii(.gz)?$', '.pgm', niiimg)
        self.cmd_runner("slicer %s %s -a %s " % (overlay, niiimg, pgmimg), logit=False)
        self.update_img_menu()
        self.selectedImg.set(pgmimg)
        # change_img(pgmimg)

    # change from menu
    def change_img_from_menu(self, *args):
        pgmimg = self.selectedImg.get()
        self.change_img(pgmimg)
