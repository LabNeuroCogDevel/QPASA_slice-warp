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
        self.logfile = None  # see set_logfile

    def __del__(self):
        "Deconstructor. dont leave dangling file handler."
        if self.logfile and not self.logfile.closed:
            self.logfile.close()

    def set_logfile(self, logfilepath):
        """
        Logfile not set during class init.
        Working dir is changed after gui is initialized (based on file picker)
        logtxt appends to file only when self.logfile is set (by calling this function)
        @param logfilepath path of file to append logs
        """
        print("# Writting log to %s\n" % logfilepath)
        self.logfile = open(logfilepath, 'w')

    def logtxt(self, txt, tag='output'):
        """
        message to text box area
        tags info, cmd, output, error, alert.  see logarea.tag_config lines
        """
        if not self.logarea:
            print("%s: %s" % (tag, txt))
            return

        if self.logfile:
            self.logfile.write("%s: %s\n" % (tag, txt))
            self.logfile.flush() # dont wait for program to close to write

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
            self.logtxt(output.decode('utf-8','replace'), 'output')
        if error.decode():
            self.logtxt("ERROR: " + error.decode('utf-8','replace'), 'error')


    def runcmd(self, cmd, logit=True):
        """run command and optionally log it. always log errors"""
        if logit:
            self.logruncmd(cmd)
        p = subprocess.Popen(
            cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.logcmdoutput(p, logit)
