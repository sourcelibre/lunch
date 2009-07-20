#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Miville
# Copyright (C) 2008 Société des arts technologiques (SAT)
# http://www.sat.qc.ca
# All rights reserved.
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Miville is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Miville. If not, see <http://www.gnu.org/licenses/>.

import sys
import time
import os
import signal
import grp
import pwd

# -- module variables --
_APP_NAME = "lunch"
_DATA_DIR = os.path.expanduser("~/.%s/data" % (_APP_NAME)) # directory where we store data
_processes = {} # processes
DELAY_AFTER_START = 5.0 # time to wait after start before checking if alive.
DELAY_AFTER_KILL = 2.0 # time to wait after kill before checking if dead.
VERBOSE = True

# -- module functions --
def _is_pid_running(pid):
    return os.path.exists("/proc/%d" % (pid))

def set_data_dir(data_dir):
    """ Sets the data directory for the app.
        Where to store pid files.
    """
    global _DATA_DIR
    _DATA_DIR = data_dir

def _create_dirs(path):
    """ Creates data directory if it doesn't exist."""
    global VERBOSE
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            if VERBOSE:
                print('mkdir '+ path)
    except OSError, e:
        if VERBOSE:
            print('Error creating directories ' + path + str(e.message))


def _run_action_for_identifier(action, identifier):
    """ Start/stop/restart/status for a process by its identifier. """
    global _DATA_DIR
    global _processes
    # TODO: support the "all" identifier
    _create_dirs(_DATA_DIR)
    try:
        p = _processes[identifier]
    except KeyError, e:
        print("No such process : " + str(e.message))
    else:
        method = getattr(p, action) # get the method identified by its name
        try:
            method()
        except ProcessStartupError, e:
            # raise e
            print("Could not launch process %s: %s " % (identifier, e.message))
            sys.exit(1)

def main(action, identifier):
    """ The main function starts/stops/restart/status for a process. """
    global _processes
    global _DATA_DIR
    
    success = True
    if identifier not in _processes.keys():
        # if identifier == "all":
        #    success = _run_action_for_identifier(action, "all")
        #else:
        # TODO: support the "all" identifier
        print("Process identifier %s not found." % (identifier))
        success = False
    if action not in ["start", "stop", "restart", "status"]:
        print("Invalid command %s" % (action))
        success = False
    success = _run_action_for_identifier(action, identifier)
    if not success:
        sys.exit(1) # error

def add(process):
    """ Adds a process to manage. """
    global _processes
    if _processes.has_key(process.identifier):
        raise ProcessAlreadyManagedError("Process with same identifer is already registered.")
    _processes[process.identifier] = process

def _check_priviledges():
    """ Check if run as super user. """
    # TODO
    if os.getuid() != 0:
        print("You are not root !")
        return False
        # sys.exit(1)
    else:
        return True

# -- classes --

class ProcessStartupError(Exception):
    """ Could not start the process error. """
    pass

class ProcessAlreadyManagedError(Exception):
    """ Raised when user tries to add two processes with 
        the same identifier.
    """
    pass

class Process(object):
    """ GNU process that can be started, stopped, restarted
        or for which we can query the state.
    """
    def __init__(self, 
            identifier, 
            executable, 
            args=[], 
            uid=None, 
            gid=None,
            working_directory=None, 
            env={},
            stop_signal=None, 
            description=""):
        """ 
        Initializes the attributes for the process.
        """
        if stop_signal is None:
            stop_signal = signal.SIGKILL
        self.stop_signal = stop_signal
        self.identifier = identifier
        self.description = description
        self.args = [executable]
        self.args.extend(args)
        self.working_directory = working_directory
        self.gid = None
        self.uid = None
        self.enable_stderr = False
        self.enable_stdout = False
        # TODO : manage gid and uid
        #if gid is not None:
        #    self.gid = grp.getgrnam(gid)[2]
        #if uid is not None:
        #    self.uid = pwd.getpwnam(uid)[2]
    
    def _get_pidfile_path(self):
        """ Returns the path to the pidfile for this process. """
        global _DATA_DIR
        return os.path.join(_DATA_DIR, "%s.pid" % (self.identifier))

    def _read_pid(self):
        """ Opens pid file and read it. Returns None if there is none. """
        if not os.path.exists(self._get_pidfile_path()):
            return None
        else:
            f = open(self._get_pidfile_path(), "r")
            pid = int(f.read())
            f.close()
            return pid

    def status(self):
        """ Prints status. """
        print("%s %s" % (self.identifier, self._get_status()))

    def _get_status(self):
        """ Returns single-word status """
        pid = self._read_pid()
        if pid is None:
            return "stopped"
        elif _is_pid_running(pid):
            return "running"
        else:
            return "crashed"

    def start(self):
        """ Starts the process """
        pid = self._read_pid()
        will_start = True
        if pid is not None:
            if _is_pid_running(pid):
                print("%s is already running." % (self.identifier))
                wll_start = False
                return
            else:
                print("%s had crashed." % (self.identifier))
        if will_start:
            print("Launching %s..." % (self.identifier))
            self._do_start()

    def _do_start(self):
        """ Actually starts the process """
        global VERBOSE
        if VERBOSE:
            print("%s %s" % (self.executable, " ".join(self.args)))
        fork_result = os.fork()
        if fork_result == 0: # child process
            # TODO: manage gid and uid
            if self.working_directory is not None:
                os.chdir(self.working_directory)
            null_file = os.open("/dev/null", os.O_RDWR)
            os.dup2(null_file, 0) # replace stdin
            if not self.enable_stdout:
                os.dup2(null_file, 1) # replace stdout
            if not self.enable_stderr:
                os.dup2(null_file, 2) # replace stderr
            os.close(null_file)
            os.execv(self.executable, self.args) # launch it !
        else: # parent process
            pid = fork_result
            f = open(self._get_pidfile_path(), "w")
            f.write("%d" % (pid))
            f.close()
            time.sleep(DELAY_AFTER_START)
            ret = os.waitpid(pid, os.WNOHANG)
            if ret == (0, 0):
                print("%s is running" % (self.identifier))
            else:
                print("Failed to start %s" % (self.identifier))
                raise ProcessStartupError("Process is not running")

    def stop(self, warn_if_crashed=True):
        """ Stops the process if running. """
        pid = self._read_pid()
        if pid is not None:
            if _is_pid_running(pid):
                print("Stopping %s..." % (self.identifier))
                os.kill(pid, self.stop_signal)
                time.sleep(DELAY_AFTER_KILL)
                if not _is_pid_running(pid):
                    print("Killed %s" % (self.identifier))
                else:
                    print("Failed to kill %s" % (self.identifier))
            else:
                if warn_if_crashed:
                    print("%s seems to have crashed before we tried to kill it." % (self.identifier))
            os.remove(self._get_pidfile_path())
        else:
            print("%s is not running." % (self.identifier))

    def restart(self):
        """ Stops and start again the process. """
        self.stop(False)
        self.start()




