#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Lunch
# Copyright (C) 2008 Société des arts technologiques (SAT)
# http://www.sat.qc.ca
# All rights reserved.
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Lunch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lunch. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import random
import subprocess

VERBOSE = False

class ChildKilledError(Exception):
    """Raised when child is killed"""
    pass

class ExecutionFailedError(Exception):
    """Raised when a command quickly returns an error, or when shell raises an OSError"""
    pass

def run_command(command_str, variables_dict={}, die_on_ctrl_c=True, log_file_name=None):
    """
    Creates and launches a process. 

    Uses subprocess to launch a process. Blocking.
    When called, might throw a OSError or ValueError.
    Throws a ChildKilledError if ctrl-C is pressed.
    """
    global VERBOSE
    retcode = None
    environment = {}
    environment.update(os.environ)
    environment.update(variables_dict)
    log_file = None
    if log_file_name is not None:
        try:
            os.remove(log_file_name) # cleans it up from last time we ran it. TAKE CARE !
        except OSError, e:
            pass
        try:
            log_file = open(log_file_name, 'a') # append mode
        except IOError, e:
            log_file = None
            raise # !!!
    try:
        def verb(txt, log_file=None):
            """
            Local function
            Writes to a log file debug messages and prints it too.
            """
            if log_file is not None:
                log_file.write("%s\n" % (txt))
                log_file.flush()
            print(txt)
        if VERBOSE:
            verb("--------", log_file)
        verb("RUNNING: %s" % (command_str), log_file)
        p = subprocess.Popen(command_str, shell=True, env=environment, stderr=subprocess.STDOUT, stdout=log_file)
        verb("PID: %s" % (p.pid), log_file)
        if VERBOSE:
            verb("ENV: %s" % (str(variables_dict)), log_file)
            verb("--------", log_file)
        retcode = p.wait() # blocking
        if retcode < 0:
            err = "EXITED: Child was terminated by signal %d. Its command was \"%s\".\n" % (retcode, command_str)
            sys.stderr.write(err)
        else:
            err = "EXITED: Child returned %s Its command was \"%s\"." % (retcode, command_str)
            verb(err, log_file)
            sys.stderr.write(err)
    except OSError, e:
        err = "EXITED: Execution of child failed: %s. Its command was \"%s\"\n" % (e.message, command_str)
        sys.stderr.write(err)
        verb(err, log_file)
        retcode = 1
    except KeyboardInterrupt, e:
        if die_on_ctrl_c:
            msg = "INTERRUPTED: Ctrl-C has been pressed in a slave terminal. Dying. Its command was \"%s\"" % (command_str, log_file)
            verb(msg, log_file)
            sys.exit(1)
        else:
            raise ChildKilledError("INTERRUPTED: Ctrl-C has been pressed in the master's terminal and caught by a worker. Its command was \"%s\"" % (command_str))
    except ValueError, e:
        err = "ERROR: Wrong arguments to subprocess.Popen: %s Its command was \"%s\"" % (e.message, command_str)
        sys.stderr.write(err)
        raise
    #else:
        #print("Success\n") # retrcode is p.wait() return val
    if log_file is not None:
        log_file.close()
    return retcode
