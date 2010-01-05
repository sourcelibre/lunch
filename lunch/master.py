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

"""
Runs the slave commands on remote and local machines. 

"""
# TODO: use log instead of print
# TODO: create config dir/file if not found
import os
import sys
import random
import subprocess
import multiprocessing
import logging
import time

from lunch import common

__version__ = "0.1.2"
EPILOG = """Released under the terms of the GNU General Public License 2.
Copyright 2009 Society for Arts and Technology."""
DESCRIPTION = """Lunch is a distributed process launcher for GNU/Linux. 
It uses the following software packages : xterm, ssh (configured using ssh-keygen, ssh-agent and ssh-keyinstall). 
Lunch itself must be installed on every host. """
DEFAULT_CONFIG_FILE = os.path.expanduser("~/.lunchrc")
HOLD_TERMINAL = False
RESPAWN = True # Respawn all KILL/INT/TERM'ed process
ENABLE_MINIMUM_PROCESS_TIME = True
DELAY_BEFORE_LAUNCHING_AGAIN = 0.1
MINIMUM_PROCESS_TIME = 1.0 # minimum time a process must last to be considered successful
LOGGING_ENABLED = False
DEFAULT_LOG_FILE = "/var/tmp/lunch.log" # For slaves. In append mode, so that many slaves can write to it.
_commands = []

#class ParentKilledError(Exception):
#    """Raised when parent is killed by ctrl-c"""
#    pass


class ExecutionFailedError(Exception):
    """Raised when a command quickly returns an error, or when shell raises an OSError"""
    pass

class Command(object):
    """
    One command to run on a remote or local host.

    Class with no method.
    Default priority is 100
    """
    def __init__(self, command="", env={}, host=None, user=None, priority=100, title="xterm_slave", sleep=0.1, respawn=True, log_file=DEFAULT_LOG_FILE):
        self.command = command
        self.env = env
        self.host = host
        self.user = user
        self.title = title
        self.priority = priority
        self.sleep = sleep
        self.respawn = respawn
        self.log_file = log_file

def add_command(command="", env={}, host=None, user=None, priority=100, title="xterm_slave", sleep=0.25, respawn=True, log_file=DEFAULT_LOG_FILE):
    """
    This is the only function that users use from within the configuration file.
    It adds a Command instance to the list of commands to run. 
    
    Default priority is 100. The lowest the earliest.
    """
    global _commands
    if common.VERBOSE:
        print("DEBUG: adding %s %s %s %s %s %s %s" % (command, env, host, user, priority, title, sleep, respawn)) # EDIT ME
    _commands.append(Command(command=command, env=env, host=host, user=user, priority=priority, title=title, sleep=sleep, respawn=respawn, log_file=log_file)) # EDIT ME

def sorting_callback(x, y):
    """
    Sorts Command objects using their priority attribute.
    
    To define a compare function for sort(), you must follow certain pattern.
    1. Compare function must take TWO param: x and y,
    2. It should return positive number if x > y, return negative number if x< y and return 0 if they are equal for Ascending sort.
    """
    if x.priority > y.priority:
        return 1
    elif x.priority < y.priority:
        return -1
    else:
        return 0

class FileNotFoundError(Exception):
    """
    Thrown when a file could not be found.
    """
    pass

def run_master(config_file):
    """
    Runs the master that calls commands using ssh or so.

    This happens only on the master computer.
     * reads config file
     * uses multiprocessing to create many workers. (calling start_worker)
       Those worker launch the "lunch" program in a xterm terminal.
       (maybe through ssh, if on a remote host)
     * If ctrl-C is pressed from any worker, dies.
    """
    global _commands
    if os.path.exists(config_file):
        try:
            execfile(config_file) # config is plain python using the globals defined here. (the add_process function)
        except Exception, e:
            print("ERROR: Error in user configuration file.")
            raise
    else:
        # create the directory ?
        raise FileNotFoundError("ERROR: Could not find the %s file." % (config_file))
    # init multiprocessing
    if LOGGING_ENABLED:
        multiprocessing.log_to_stderr(level=logging.INFO)
        log = multiprocessing.get_logger()
        # log.warning("test debug")
    workers = []
    queue = multiprocessing.Queue()
    _commands.sort(sorting_callback)
    try:
        for command in _commands:
            user = command.user
            host = command.host
            title = command.title
            log_file = command.log_file
            cmd = command.command
            env = "" # make str from dict
            hold = ""
            if HOLD_TERMINAL:
                hold = "-hold"
            if len(command.env) > 0:
                for k, v in command.env.items():
                    env += " -e %s %s " % (k, v)
            # we use lunch slave in order to add environment variables to the remote process.
            command_str = 'xterm -T "%s" %s -e lunch %s -s --log-file %s -c "%s"' % (title, hold, env, log_file, cmd) 
            if command.host is not None:
                user_args = ""
                if command.user is not None:
                    user_args = "-l %s " % (command.user)
                command_str = 'ssh -X %s %s xterm -T "%s" %s -e lunch %s -s --log-file %s -c \\"%s\\"' % (user_args, host, title, hold, env, log_file, cmd) # prepend ssh command
                # TODO: how to escape commands properly ? 
                # TODO: Maybe better to use sys.argv for every args after --command
            # create server
            process = multiprocessing.Process(group=None, target=start_worker, name=command_str, args=(command_str, os.environ, queue, command.respawn))
            workers.append(process)
            process.start()
            time.sleep(command.sleep + random.random() * 0.05)
        # waiting for a message from any child.
        message = queue.get() # excepts the message "CTRL-C !", see below
        raise common.ChildKilledError("INTERRUPTED: A worker received ctrl-C.")
    except common.ChildKilledError:
        print("INTERRUPTED: !!! Ctrl-C was pressed in master. !!!")
        for worker in workers:
            print("EXITING: Terminating worker. Its command was: %s" % (worker.name))
            worker.terminate()
            #os.kill(worker.pid(), signal.SIGINT)
    except KeyboardInterrupt:
        print("INTERRUPTED: !!! Ctrl-C was pressed in master. !!!")
        for worker in workers:
            print("EXITING: Terminating worker. Its command was: %s" % (worker.name))
            worker.terminate()
            #os.kill(worker.pid(), signal.SIGINT)

def start_worker(command, vars={}, queue=None, respawn=True):
    """ 
    A multiprocessing worker will run as its own process 
    """
    # print("Starting command: " + str(command))
    while True: # runs forever.
        try:
            started = time.time()
            ret = common.run_command(command, vars, False) # throw an error on ctrl-C (this should be blocking)
            if ret == 1:
                print("Child process returned an error. Will not try to run it again. Its command was %s" % (command))
                break
            if ENABLE_MINIMUM_PROCESS_TIME:
                if time.time() < (started + MINIMUM_PROCESS_TIME):
                    print("ERROR: Process did not last long enough. Will not be run again. Its command was %s" % (command))
                    break
        except common.ChildKilledError:
            # break
            if queue is not None:
                queue.put(["Ctrl-C !"]) # communicates with the master
            # raise
        else:
            print("EXITED: Return value is %s" % (ret))
            if not RESPAWN or not respawn:
                print("DEBUG: Will not restart it.")
                break
            else:
                print("DEBUG: Running it again in %f seconds." % (DELAY_BEFORE_LAUNCHING_AGAIN ))
                time.sleep(DELAY_BEFORE_LAUNCHING_AGAIN )

