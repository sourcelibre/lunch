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
The Lunch master manages lunch slaves.
Author: Alexandre Quessy <alexandre@quessy.net>
"""
import os
import stat
import time
import sys
import logging
import warnings
import subprocess # TODO: get rid of blocking IO

from twisted.internet import defer
from twisted.internet import error
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import task
from twisted.internet import utils
from twisted.python import failure
from twisted.python import log
from twisted.python import logfile
from twisted.python import procutils

from lunch import sig
from lunch import graph
from lunch import commands
from lunch.states import *

DEFAULT_LOG_DIR = "/var/tmp/lunch"

def start_stdout_logging():
    log.startLogging(sys.stdout)

class FileNotFoundError(Exception):
    """
    Thrown when the given config file could not be found.
    """
    pass

def add_command(command=None, title=None, env=None, user=None, host=None, group=None, order=None, sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None, sleep=None, priority=None, depends=None):
    """
    This is the only function that users use from within the configuration file.
    It adds a Command instance to the list of commands to run. 

    This function is actually an alias of the Master.add_command static method, plus a few variables changes.
    """
    # TODO: remove priority and sleep kwargs in a future version
    log.msg("Adding %s (%s) %s@%s" % (title, command, user, host), logging.INFO)
    # ------------- warnings ------------------
    if group is not None:
        warnings.warn("Groups are deprecated. Use dependencies instead.")
    if sleep is not None:
        warnings.warn("The sleep keyword argument has been renamed to sleep_after.", DeprecationWarning)
        sleep_after = sleep
    if priority is not None:
        warnings.warn("The priority keyword argument does not exist anymore. Only the order in which add_command calls are done is considered.", DeprecationWarning)
    c = commands.Command(command=command, env=env, host=host, user=user, order=order, sleep_after=sleep_after, respawn=respawn, minimum_lifetime_to_respawn=minimum_lifetime_to_respawn, log_dir=log_dir, identifier=title, depends=depends)
    Master.add_command(c)    

def add_local_address(address):
    """
    Adds an IP to which not use SSH with.
    :param address: str of list of str. IP address or host name
    """
    if type(address) is not list:
        addresses = [address]
    else:
        addresses = address
    for address in addresses:
        if address not in Master.local_addresses:
            log.msg("Adding %s in list of local addresses." % (address))
            Master.local_addresses.append(address)

def clear_local_addresses():
    """
    Deletes all local addresses.
    """
    Master.local_addresses = []

class Master(object):
    """
    The Lunch Master launches slaves, which in turn launch childs.
    There should be only one instance of this class in the application. (singleton)
    """
    # static class variables :
    commands = {}
    tree = graph.DirectedGraph()
    # For counting default names if they are none :
    i = 0
    # IP to which not use SSH with :
    local_addresses = [
        "localhost",
        "127.0.0.1"
        ] # TODO: check IP of each network interface.
    
    @staticmethod
    def add_command(command):
        """
        This static method is wrapped (called) by the add_command function.
        @param command: L{lunch.commands.Command} object.
        """    
        # check if addr is local, set it to none if so.
        if command.host in Master.local_addresses:
            log.msg("Filtering out host %s since it is in list of local addresses." % (command.host))
            command.host = None    
        # set default names if they are none:
        if command.identifier is None:
            command.identifier = "default_%d" % (Master.i)
            Master.i += 1
        while command.identifier in Master.commands: # making sure it is unique
            command.identifier += "X"
        Master.tree.add_node(command.identifier, command.depends) # Adding it the the dependencies tree.
        Master.commands[command.identifier] = command
    
    def __init__(self, log_dir=DEFAULT_LOG_DIR, pid_file=None, log_file=None, config_file=None, verbose=False):
        """
        @param log_dir: str Path.
        @param pid_file: str Path.
        @param log_file: str Path.
        @param config_file: str Path.
        """
        # These are all useless within this class, but might be useful to be read from the GUI:
        self.log_dir = log_dir
        self.pid_file = pid_file
        self.log_file = log_file
        self.config_file = config_file
        self.verbose = verbose
        self.main_loop_every = 0.05 # checks process to start/stop 20 times a second.

        self._time_now = time.time()
        self.launch_next_time = time.time() # time in future
        self._looping_call = task.LoopingCall(self.main_loop)
        self._looping_call.start(self.main_loop_every, False) 
        self.wants_to_live = False # The master is either trying to make every child live or die. 
        self.prepare_all_commands()
        self.start_all()

    def start_all(self):
        """
        Sets the master so that it starts all the slaves.
        """
        self.wants_to_live = True
    
    def prepare_all_commands(self):
        """
        Called to change some attribute of all the commands before to start them for the first time. The config file is already loaded at this time.
        """
        for c in self._get_all():
            c.verbose = self.verbose

    def main_loop(self):
        """
        Called in a looping call.
        This is actually the main loop of the application.
        
        Starting by the process with no dependency, starts them, in the order they were given, sleeping some time before each, as configured using their sleep_after attribute. 
        
        The master is set up to either keep every child alive, or keep them dead. Stopping them is done as soon as possible. Starting them is done using the sequence described above. 

        
        # get children of the root
        # get time now
        # if not started give them a time to be started, if it doesn't have one
        # if started, check if it has children
        # if so, give it a time to be started.

        """
        # Trying to make all child live. (False if in the process of quitting)
        #orphans = Master.tree.get_supported_by(Master.tree.ROOT)
        #self._manage_siblings(orphans, should_run=self.wants_to_live)
        #log.msg("----- Managing slaves LOOP ----")

        self._time_now = time.time()
        iterator = graph.iter_from_root_to_leaves(Master.tree)
        for current in iterator:
            if current != Master.tree.ROOT:
                self._treat_node(current)

    def _treat_node(self, node):
        """
        Called once for each command on each main loop iteration.
        """
        command = Master.commands[node]
        all_dependencies = Master.tree.get_all_dependencies(node)
        all_dependees = Master.tree.get_all_dependees(node)
        # If RUNNING, check if we should stop it:
        if command.child_state == STATE_RUNNING:
            if self.wants_to_live is False:
                command.stop()
            else:
                kill_it = False
                for dependency in all_dependencies:
                    dep_command = Master.commands[dependency]
                    if dep_command.child_state != STATE_RUNNING and dep_command.respawn is False and dep_command.how_many_times_run != 0:
                        kill_it = True
                if kill_it:
                    log.msg("Will kill %s" % (command.identifier))
                    command.stop()
        # If STOPPED, check if we should start it:
        elif command.child_state == STATE_STOPPED:
            if self.wants_to_live and self.launch_next_time <= self._time_now:
                #
                # Check if there are dependees missing so that we start this one
                dependees_to_wait_for = False # to wait so that they quit
                for dependee_name in all_dependees:
                    dependee = Master.commands[dependee_name]
                    if dependee.child_state != STATE_STOPPED:
                        dependees_to_wait_for = True
                    if dependee.child_state == STATE_RUNNING:
                        dependee.stop()
                if not dependees_to_wait_for:
                    start_it = True
                    if not command.respawn and command.how_many_times_run >= 1:
                        start_it = False
                    #
                    # Do not start it if not enabled !
                    # (maybe lived for not long enough)
                    if not command.enabled:
                        start_it = False
                    for dependency in all_dependencies:
                        dep_command = Master.commands[dependency]
                        if dep_command.child_state != STATE_RUNNING and dep_command.respawn is True: 
                            start_it = False
                        elif dep_command.respawn is False and dep_command.how_many_times_run == 0:
                            start_it = False
                    # Finally, start it if we are ready to.
                    if start_it:
                        self.launch_next_time = self._time_now + command.sleep_after
                        log.msg("Will start %s." % (command.identifier))
                        command.start()

    def _get_all(self):
        """
        Returns all commands.
        """
        return self.commands.values()

    def get_all_commands(self):
        """
        Returns all commands, not grouped in any way.
        Used by the GUI.
        @rettype list
        """
        return self._get_all()
    
    def stop_all(self):
        """
        Stops all commands
        """
        # TODO: use callLaters to check if stopped.
        #TODO: stop the looping call.
        commands = self._get_all()
        self.wants_to_live = False
        for c in commands:
            c.enabled = False
            c.stop()
        log.msg("Done stopping all commands.")

    def restart_all(self):
        """
        Stops all commands, then wait until they are all done. Starts them all when ready.
        """
        # TODO: use the looping call to do stuff in the future.
        self.stop_all()
        reactor.callLater(0.1, self._start_if_all_stopped)

    def _start_if_all_stopped(self):
        """
        Checks in loop if all got stopped, if so, start them over.
        """
        commands = self._get_all()
        ready_to_restart = True
        for c in commands:
            if c.child_state != STATE_STOPPED:
                ready_to_restart = False
        if ready_to_restart:
            self.start_all()
        else:
            reactor.callLater(0.1, self._start_if_all_stopped)

    def quit_master(self):
        """
        Stops all slaves and quits the application.
        """
        if reactor.running:
            reactor.stop()

    def before_shutdown(self):
        """
        Called before Twisted's shutdown. (end of master process)
        """
        now = time.time()
        _shutdown_data = {
                "shutdown_started" : now,
                "shutdown_time": now + 1.0
            }
        deferred = defer.Deferred()
        def _later(self, data):
            again = False
            for c in self._get_all():
                if c.child_state == STATE_RUNNING:
                    log.msg("Slave %s is still running. Stopping it." % (c.identifier))
                    again = True
                    c.enabled = False
                    c.quit_slave()
            if time.time() >= (data["shutdown_time"]):
                log.msg("Max shutdown time expired.", logging.ERROR)
                again = False
            if again:
                reactor.callLater(0.1, _later, self, data)
            else:
                log.msg("Stopping the Lunch Master.")
                deferred.callback(True) # stops reactor
        
        _later(self, _shutdown_data)
        return deferred

def gen_id_from_config_file_name(config_file_name="lunchrc"):
    """
    Returns an identifier for the master using the config file name.
    Useful so that there is not two masters running with the same config file.
    @rettype str
    """
    file_name = os.path.split(config_file_name)[1] # remove dir name
    identifier = file_name.replace(".", "") # getting rid of the dot in file name
    return identifier

def write_master_pid_file(identifier="lunchrc", directory="/var/tmp/lunch"):
    """
    Writes master's PID in a file.
    @return: pid file name.
    """
    file_name = "master-%s.pid" % (identifier)
    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.isdir(directory):
        raise RuntimeError("The path %s should be a directory, but is not." % (directory))
    pid_file = os.path.join(directory, file_name)
    if os.path.exists(pid_file):
        f = open(pid_file, 'r')
        pid = f.read()
        f.close()
        try:
            os.kill(int(pid), 0) # if it throws, it's dead
        except OSError: # no process with that ID
            os.remove(pid_file)
        except ValueError: # invalid int. (pidfile did not contain an int)
            os.remove(pid_file)
        else:
            # checks if it's really a lunch master that has this ID.
            command_check_master = "ps aux | grep %d | grep -v grep" % (int(pid))
            #d = run_and_wait("bash", ["-c", command_check_master])
            # blocking... it's easier to debug for now
            # TODO: get rid of subprocess here.
            output = subprocess.Popen(command_check_master, stdout=subprocess.PIPE, shell=True).communicate()[0]
            if "lunch" in output:
                raise RuntimeError("There is already a Lunch Master running using the same configuration file. Its PID is %s" % (pid))
            else:
                #print "found PID, but it's not lunch!"
                os.remove(pid_file)
                
    f = open(pid_file, 'w')
    f.write(str(os.getpid()))
    f.close()
    os.chmod(pid_file, 0600)
    return pid_file

def start_file_logging(identifier="lunchrc", directory="/var/tmp/lunch"):
    """
    Starts logging the Master infos to a file.
    @rettype: str
    """
    file_name = "master-%s.log" % (identifier)
    if not os.path.exists(directory):
        os.makedirs(directory)
    full_path = os.path.join(directory, file_name)
    f = open(full_path, 'w')
    f.close()
    os.chmod(full_path, 0600)
    _log_file = logfile.DailyLogFile(file_name, directory)
    log.startLogging(_log_file)
    return _log_file.path

def run_master(config_file, log_to_file=False, log_dir=DEFAULT_LOG_DIR, chmod_config_file=True, verbose=False):
    """
    Runs the master that calls commands using ssh or so.

    This happens only on the master computer.
     * reads config file
     * uses multiprocessing to create many workers. (calling start_worker)
       Those worker launch the "lunch" program in a xterm terminal.
       (maybe through ssh, if on a remote host)
     * If ctrl-C is pressed from any worker, dies.
    @rettype Master
    
    Might raise a RuntimeError or a FileNotFoundError
    """
    identifier = gen_id_from_config_file_name(config_file)
    # TODO: make this non-blocking. (return a Deferred)
    pid_file = write_master_pid_file(identifier=identifier, directory=log_dir)
    if log_to_file:
        log_file = start_file_logging(identifier=identifier, directory=log_dir)
    else:
        start_stdout_logging()
        log_file = None
    log.msg("-------------------- Starting master -------------------")
    log.msg("Using lunch master module %s" % (__file__))
    global _commands
    if os.path.exists(config_file):
        if chmod_config_file:
            mode = stat.S_IMODE(os.stat(config_file)[0])
            new_mode = (mode & stat.S_IRUSR) + (mode & stat.S_IWUSR) + (mode & stat.S_IXUSR)
            # user hase read/write/execute permissions
            # 256, 128 and 64
            try:
                os.chmod(config_file, new_mode)
            except OSError, e:
                print("WARNING: Could not chmod configuration file. %s" % (e))
        try:
            execfile(config_file) # config is plain python using the globals defined here. (the add_process function)
        except Exception, e:
            print("ERROR: Error in user configuration file.")
            raise
    else:
        # create the directory ?
        raise FileNotFoundError("ERROR: Could not find the %s file." % (config_file))
    m = Master(log_dir=log_dir, pid_file=pid_file, log_file=log_file, config_file=config_file, verbose=verbose)
    reactor.addSystemEventTrigger("before", "shutdown", m.before_shutdown)
    # TODO: return a Deferred
    return m 

