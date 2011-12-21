#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Lunch
# Copyright (C) 2009 Société des arts technologiques (SAT)
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
# along with Lunch.  If not, see <http://www.gnu.org/licenses/>.
"""
Main entry point of the lunch master application.
"""
import os
import sys
import traceback
from optparse import OptionParser
import lunch

DESCRIPTION = "Lunch is a distributed process launcher for GNU/Linux. The Lunch master launches lunch-slave processes through an encrypted SSH session if on a remote host. Those slave processes can in turn launch the desired commands on-demand."

def run():
    """
    Runs the application.
    """
    # this will set logging and PID directories to $USER
    parser = OptionParser(usage="%prog [config file] [options]", version="%prog " + lunch.__version__, description=DESCRIPTION)
    parser.add_option("-f", "--config-file", type="string",
                        help="Specifies the python config file. You can also simply specify the config file as the first argument.")
    parser.add_option("-l", "--logging-directory", type="string",
                        help="Specifies the logging directory for the master. Default is %s/$USER/" % (lunch.DEFAULT_LOG_DIR)) # change error message in master.run_master() if you change this
    parser.add_option("-p", "--pid-directory", type="string",
                        help="Specifies the pidfile directory for the master. Default is %s/$USER/" % (lunch.DEFAULT_PID_DIR)) # change error message in master.run_master() if you change this
    parser.add_option("-q", "--log-to-file", action="store_true", help="Enables logging master infos to file and disables logging to standard output.")
    parser.add_option("-g", "--graphical", action="store_true", help="Enables the graphical user interface.")
    parser.add_option("-v", "--verbose", action="store_true", help="Makes the logging output verbose.")
    parser.add_option("-d", "--debug", action="store_true", help="Makes the logging output very verbose.")
    parser.add_option("-k", "--kill", action="store_true",
                        help="Kills another lunch master that uses the same config file and logging directory. Exits once it's done.")
    (options, args) = parser.parse_args()
    # --------- set configuration file
    if options.config_file:
        config_file = options.config_file
    DEFAULT_CONFIG_FILE = os.path.expanduser("~/.lunchrc")
    if len(args) == 1 and not options.config_file: 
        #log.msg("DEBUG: overriding config_file with %s" % (args[0])) 
        config_file = args[0] 
    else:
        config_file = DEFAULT_CONFIG_FILE
    # --------- set if logging 
    if options.log_to_file:
        file_logging_enabled = True
    else:
        file_logging_enabled = False
    # ---------- load the right reactor
    if options.graphical:
        try:
            from twisted.internet import gtk2reactor
            gtk2reactor.install() # has to be done before importing reactor
            import gtk # just for a test
            GUI_ENABLED = True
            #print("Successfully loaded the GTK+ graphical user interface.")
        except ImportError, e:
            print("Could not load the GTK+ graphical user interface. " + str(e))
            GUI_ENABLED = False
    else:
        # print("Using lunch master without the GUI.")
        GUI_ENABLED = False
    from twisted.internet import reactor
    from twisted.internet import defer
    # --------- load the module and run
    from lunch import master
    if options.logging_directory:
        logging_dir = options.logging_directory
    else:
        logging_dir = master.get_default_log_dir_full_path()
    if options.pid_directory:
        pid_dir = options.pid_directory
    else:
        pid_dir = master.get_default_pid_dir_full_path()
    if pid_dir is None:
        pid_dir = master.get_default_pid_dir_full_path() # FIXME:code duplication
    if not master.create_dir_and_make_writable(pid_dir):
        print("PID directory is not writable: %s. Use the --pid-directory option" % (pid_dir))
        sys.exit(1)
    error_message = None
    if not os.path.exists(config_file):
        error_message = "No such file: %s" % (config_file)
    else:
        log_level = 'warning'
        if options.verbose:
            log_level = 'info'
        if options.debug:
            log_level = 'debug'
        if options.kill:
            def _killed_cb(result):
                #TODO: show a dialog to the user if --graphical is given.
                if reactor.running:
                    reactor.stop()
            master.start_stdout_logging(log_level=log_level) #FIXME: should be able to log to file too
            identifier = master.gen_id_from_config_file_name(config_file)
            master.log.info("Will check if lunch master %s is running and kill it if so." % (identifier))
            deferred = master.kill_master_if_running(identifier=identifier, directory=pid_dir)
            deferred.addCallback(_killed_cb)
            reactor.run()
            sys.exit(0)
        try:
            #print("DEBUG: using config_file %s" % (config_file))
            lunch_master = master.run_master(config_file, log_to_file=file_logging_enabled, pid_dir=pid_dir, log_dir=logging_dir, log_level=log_level)
        except master.FileNotFoundError, e:
            #print("Error starting lunch as master.")
            msg = "A configuration file is missing. Try the --help flag. "
            msg += str(e)
            error_message = msg
            # will exit with error. see below.
        except RuntimeError, e:
            error_message = str(e)
            # will exit with error. see below.
        except Exception, e:
            error_message = "There is an error in your lunch file !\n"
            error_message += traceback.format_exc()
            # will exit with error. see below.
    if error_message is not None:
        print(error_message)
        if GUI_ENABLED:
            from lunch import dialogs
            def _cb(result):
                # stops reactor when the error dialog is closed
                reactor.stop()
            d = defer.Deferred()
            d.addCallback(_cb)
            error_dialog = dialogs.ErrorDialog(d, error_message)
            print("Running reactor to show error dialog.")
            reactor.run() # need it for the GTK error dialog
            print("Reactor stopped. Exiting.")
        sys.exit(1) # exits with error
    if GUI_ENABLED:
        from lunch import gui
        app = gui.start_gui(lunch_master)
        #print("Done starting the app.")
    try:
        reactor.run()
    except KeyboardInterrupt:
        #log.msg("Ctrl-C in Master.", logging.INFO)
        #lunch_master.quit_master()
        reactor.stop()

