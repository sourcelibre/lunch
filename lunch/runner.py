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

__version__ = "0.2.15"

import os
import sys
import traceback
from optparse import OptionParser

DESCRIPTION = "Lunch is a distributed process launcher for GNU/Linux. The Lunch master launches lunch-slave processes through an encrypted SSH session if on a remote host. Those slave processes can in turn launch the desired commands on-demand."

def run():
    """
    Runs the application.
    """
    parser = OptionParser(usage="%prog [config file] [options]", version="%prog " + __version__, description=DESCRIPTION)
    parser.add_option("-f", "--config-file", type="string", help="Specifies the python config file. You can also simply specify the config file as the first argument.")
    parser.add_option("-l", "--logging-directory", type="string", default="/var/tmp/lunch", help="Specifies the logging and pidfile directory for the master. Default is /var/tmp/lunch")
    parser.add_option("-q", "--log-to-file", action="store_true", help="Enables logging master infos to file and disables logging to standard output.")
    parser.add_option("-g", "--graphical", action="store_true", help="Enables the graphical user interface.")
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
    logging_dir = options.logging_directory
    # ---------- load the right reactor
    if options.graphical:
        try:
            from twisted.internet import gtk2reactor
            gtk2reactor.install() # has to be done before importing reactor
            from lunch import gui
            GUI_ENABLED = True
            print("Successfully loaded the GTK+ graphical user interface.")
        except ImportError, e:
            print("Could not load the GTK+ graphical user interface. " + str(e))
            GUI_ENABLED = False
    else:
        print("Using lunch master without the GUI.")
        GUI_ENABLED = False
    from twisted.internet import reactor
    from twisted.internet import defer
    # --------- load the module and run
    from lunch.master import run_master
    from lunch.master import FileNotFoundError
    from lunch.master import MasterError
    error_message = None
    if not os.path.exists(config_file):
        error_message = "No such file: %s." % (config_file)
    else:
        try:
            #print("DEBUG: using config_file %s" % (config_file))
            master = run_master(config_file, log_to_file=file_logging_enabled, log_dir=logging_dir)
        except FileNotFoundError, e:
            #print("Error starting lunch as master.")
            msg = "A configuration file is missing. Try the --help flag. "
            msg += str(e)
            error_message = msg
            #sys.exit(1)
        except MasterError, e:
            #print(str(e))
            error_message = str(e)
            #sys.exit(1)
        except Exception, e:
            error_message = "There is an error in your lunch file !\n"
            error_message += traceback.format_exc()
    if error_message is not None:
        print(error_message)
        if GUI_ENABLED:
            def _cb(result):
                reactor.stop()
            d = defer.Deferred()
            d.addCallback(_cb)
            error_dialog = gui.ErrorDialog(d, error_message)
            print("Running reactor to show error dialog.")
            reactor.run() # need it for the GTK error dialog
            print("Reactor stopped. Exiting.")
        sys.exit(1)
    if GUI_ENABLED:
        app = gui.start_gui(master)
        print("Done starting the app.")
    try:
        reactor.run()
    except KeyboardInterrupt:
        #log.msg("Ctrl-C in Master.", logging.INFO)
        #master.quit_master()
        reactor.stop()

