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
DELAY_AFTER_START = 2.0 # time to wait after start before checking if alive.
DELAY_AFTER_KILL = 2.0 # time to wait after kill before checking if dead.
VERBOSE = True

# -- classes --
class ProcessStartupError(Exception):
    """ Could not start the process error. """
    pass

class Process(object):
    """ GNU process that can be started, stopped, restarted
        or for which we can query the state.
    """
    def __init__(self, 
            executable, 
            args=[], 
            env={},
            working_directory=None
            ):
        """ 
        Initializes the attributes for the process.
        """
        #if stop_signal is None:
        #    stop_signal = signal.SIGKILL
        #self.stop_signal = stop_signal
        # self.description = description
        self.executable = executable
        self.args = [] # [executable]
        self.args.extend(args)
        self.working_directory = working_directory
        self.enable_stderr = False
        self.enable_stdout = False
    
    def start(self):
        """
        Starts the process 
        """
        global VERBOSE
        if VERBOSE:
            print("$ %s %s" % (self.executable, " ".join(self.args)))
        fork_result = os.fork()
        if fork_result == 0: # child process
            # change directory
            if self.working_directory is not None:
                os.chdir(self.working_directory)
            # redirect stdout and stderr
            null_file = os.open("/dev/null", os.O_RDWR)
            os.dup2(null_file, 0) # replace stdin
            if not self.enable_stdout:
                os.dup2(null_file, 1) # replace stdout
            if not self.enable_stderr:
                os.dup2(null_file, 2) # replace stderr
            os.close(null_file)
            # manage environment variables
            for key, val in self.env.items():
                os.environ[key] = val
            # launch it !
            print("os.execv(%s, %s)..." % (self.executable, str(self.args)))
            args = [self.executable]
            args.expand(self.args)
            os.execv(self.executable, args)
        else: # parent process
            pid = fork_result
            print("STARTED AS %s\n" % (pid))
            time.sleep(DELAY_AFTER_START)
            ret = os.waitpid(pid, os.WNOHANG)
            if ret == (0, 0):
                print("%s is still running after %2.2f seconds." % (self.executable, DELAY_AFTER_START))
            else:
                print("Process %s has crashed after %2.2f seconds." % (self.executable, DELAY_AFTER_START))
                # raise ProcessStartupError("Process is not running")

def execute(command_str, variables_dict={}):
    """ Creates and launches a process. """
    command = command_str.split(' ')
    p = Process(
        command[0], 
        args=command[1:], 
        env=variables_dict)
    p.start()

