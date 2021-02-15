"""
tooltip from @squareRoot17
https://stackoverflow.com/questions/20399243/display-message-when-hovering-over-something-with-mouse-cursor-in-python
"""
from tkinter import Toplevel, Label, LEFT, SOLID

XOFFSET = 70
YOFFSET = 57


class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.bind_widget(self.widget)

    def bind_widget(self, widget):
        # TODO: also need to create method to unbind?
        widget.bind('<Enter>', lambda e: self.showtip())
        widget.bind('<Leave>', lambda e: self.hidetip())

    def showtip(self):
        "Display text in tooltip window"
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + XOFFSET
        y = y + cy + self.widget.winfo_rooty() + YOFFSET
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
