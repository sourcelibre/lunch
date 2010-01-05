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
Usage 
-----

Can be run as a server controlling remote computers with ssh security:: 
 lunch

Can also be run as a single process launcher in a xterm terminal.
 lunch -c glxgears -e DISPLAY :0.0
 
 ssh -X brrr xterm -e "lunch -c \"glxgears\" -e DISPLAY :0.0"

Notes 
-----
We use lunch slave in order to add environment variables to the remote process.

Lunch needs xterm, ssh and /bin/sh.
"""
from optparse import OptionParser
import sys

from lunch import master
from lunch import slave
from lunch import common

__version__ = "0.1.3"
EPILOG = """Released under the terms of the GNU General Public License 2.
Copyright 2009 Society for Arts and Technology."""
DESCRIPTION = """Lunch is a distributed process launcher for GNU/Linux. 
It uses the following software packages : xterm, ssh (configured using ssh-keygen, ssh-agent and ssh-copy-id). 
Lunch itself must be installed on every host. """

def run():
    """
    Runs the application.
    """
    parser = OptionParser(usage="%prog [options]", version="%prog " + __version__, epilog=EPILOG, description=DESCRIPTION)
    parser.add_option("-s", "--slave", action="store_true", help="Run in slave mode to launch a single process. The --command option is mandatory when in slave mode.")
    parser.add_option("-d", "--disable-minimum-process-time", action="store_true", help="Restart process even if it did not long last.")
    parser.add_option("-H", "--hold", action="store_true", help="Hold the xterm terminal window once it quit.")
    parser.add_option("-t", "--minimum-time", type="float", help="Sets the minimum time that a process must last to be considered crashed. Only in slave mode for now. Default is %f seconds." % (master.MINIMUM_PROCESS_TIME))
    parser.add_option("-R", "--no-respawn", action="store_true", help="Do not respawn processes when they die.")
    parser.add_option("-v", "--verbose", action="store_true", help="Run in the verbose mode.")
    parser.add_option("-c", "--command", type="string", help="Command to execute. This options is mandatory when in slave mode.")
    parser.add_option("-e", "--environment", action="append", nargs=2, help="Sets an environment variable with key/value pair.")
    parser.add_option("-f", "--config-file", type="string", help="If run as master, specifies the python config file.")
    parser.add_option("-l", "--log-file", type="string", help="If run as slave, specifies the log file to write to. WARNING : That file will be removed and written to it with the children standard output. You can read this file with the command 'tail -F %s'" % (master.DEFAULT_LOG_FILE), default=master.DEFAULT_LOG_FILE)
    (options, args) = parser.parse_args()
    if options.minimum_time:
        master.MINIMUM_PROCESS_TIME = options.minimum_time
    if options.hold:
        master.HOLD_TERMINAL = True
    if options.disable_minimum_process_time:
        master.MINIMUM_PROCESS_TIME = False
    if options.verbose:
        common.VERBOSE = True
    if options.no_respawn:
        master.RESPAWN = False
    #if not options.master or 
    if options.slave: # run as SLAVE
        #if len(args) == 0:
        if not options.command:
            print("lunch --slave: You must provide a command to execute. Try -h to get help.")
            parser.print_usage()
            sys.exit(1)
        else:
            print("Running Lunch as a slave to launch a single process.")
            # command = " ".join(args)
            log_file_name = options.log_file
            command = options.command
            variables_dict = {} # dict of environment variables
            if options.environment:
                variables_dict = options.environment
            print("Additional environment variables: %s" % (str(variables_dict)))
            ret = slave.run_slave(command, variables_dict, log_file_name)
    else: # run as MASTER
        #if options.command or 
        if options.environment:
            print("Environment variables can only be set when run in slave mode.")
            parser.print_usage()
            sys.exit(1)
        else:
            config_file = options.config_file
            if len(args) == 1 and not options.config_file: 
                print("DEBUG: overriding config_file with %s" % (args[0])) 
                config_file = args[0] 
            else:
                config_file = master.DEFAULT_CONFIG_FILE # default value
            try:
                print("DEBUG: using config_file %s" % (config_file))
                master.run_master(config_file)
            except master.FileNotFoundError, e:
                print("Error starting lunch as master.")
                print(e.message)
                print("A configuration file is missing. Try the --help flag.")
                sys.exit(1)
