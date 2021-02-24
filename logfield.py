"""
Operate a Tk log text area
"""

import os
import tkinter
import datetime
import subprocess


class LogField:
    """
    handle displaying commands run and error/stdout
    """
    def __init__(self, logarea):
        """@param logarea  Tk textara
        add colored tags
        """
        self.logarea = logarea
        if not logarea:
            return
        logarea.tag_config('info', foreground='green')
        logarea.tag_config('cmd', foreground='blue')
        logarea.tag_config('output', foreground='grey')
        logarea.tag_config('error', foreground='red')
        logarea.tag_config('alert', foreground='orange')

    def logtxt(self, txt, tag='output'):
        """
        message to text box area
        tags info, cmd, output, error, alert.  see logarea.tag_config lines
        """
        if not self.logarea:
            print("%s: %s" % (tag, txt))
            return
        self.logarea.mark_set(tkinter.INSERT, tkinter.END)
        self.logarea.config(state="normal")
        self.logarea.insert(tkinter.INSERT, txt + "\n", tag)
        self.logarea.config(state="disable")
        self.logarea.see(tkinter.END)
        self.logarea.update_idletasks()


    def shouldhave(self, thisfile):
        """log if file does not exist"""
        if not os.path.isfile(thisfile):
            self.logtxt("ERROR: expected file (%s/%s) does not exist!" %
                   (os.getcwd(), thisfile), 'error')


    def logruncmd(self, cmd):
        """write comand we want to run to log"""
        self.logtxt("\n[%s %s]" % (datetime.datetime.now(), os.getcwd()), 'info')
        self.logtxt("%s" % cmd, 'cmd')


    def logcmdoutput(self, p, logit):
        """run pipe and display colored output"""
        output, error = p.communicate()
        if logit:
            self.logtxt(output.decode(), 'output')
        if error.decode():
            self.logtxt("ERROR: " + error.decode(), 'error')


    def runcmd(self, cmd, logit=True):
        """run command and optionally log it. always log errors"""
        if logit:
            self.logruncmd(cmd)
        p = subprocess.Popen(
            cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.logcmdoutput(p, logit)
