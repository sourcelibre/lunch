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
import signal
import socket
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
#from twisted.python import log
from twisted.python import logfile
from twisted.python import procutils

import lunch
from lunch import sig
from lunch import graph
from lunch.states import *
from lunch import logger

log = None
LOG_NAME = 'master'

def start_stdout_logging(log_level='info'):
    #log.startLogging(sys.stdout)
    global log
    log = logger.start(level=log_level, name=LOG_NAME, to_stdout=True, to_file=False)

class FileNotFoundError(Exception):
    """
    Thrown when the given config file could not be found.
    """
    pass

def _guess_user_name():
    """
    Guesses $USER.
    @rtype: str
    """
    ret = ""
    try:
        ret = os.environ["USER"]
    except OSError, e:
        log.error("Cannot get $USER because %s" % (str(e)))
    return ret

def get_default_log_dir_full_path():
    # file_name = lunch.DEFAULT_LOG_PREFIX + _guess_user_name()
    # return os.path.join(lunch.DEFAULT_LOG_DIR, file_name)
    return lunch.DEFAULT_LOG_DIR

def get_default_pid_dir_full_path():
    # file_name = lunch.DEFAULT_PID_PREFIX + _guess_user_name()
    # return os.path.join(lunch.DEFAULT_PID_DIR, file_name)
    return lunch.DEFAULT_PID_DIR

class Master(object):
    """
    The Lunch Master launches slaves, which in turn launch childs.
    """
    def __init__(self, log_dir=None, pid_dir=None, pid_file=None, log_file=None, config_file=None, verbose=False):
        """
        @param log_dir: str Path.
        @param pid_dir: str Path.
        @param pid_file: str Path.
        @param log_file: str Path.
        @param config_file: str Path.
        """
        # attributes:
        self.commands = {} # dict of str identifier: L{lunch.commands.Command}
        self.tree = graph.DirectedGraph()
        # For counting default names if they are none :
        self.i = 0
        # IP to which not use SSH with :
        self.local_addresses = [
            "localhost",
            "127.0.0.1",
            ]
        self._guess_local_ip_and_hostname_for_local_host()
        
        # These are all useless within this class, but might be useful to be read from the GUI:
        self.log_dir = log_dir
        self.pid_dir = pid_dir
        if self.log_dir is None:
            self.log_dir = get_default_log_dir_full_path()
        if self.pid_dir is None:
            self.pid_dir = get_default_pid_dir_full_path()
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
        self.command_added_signal = sig.Signal() # param: Command object
        self.command_removed_signal = sig.Signal() # param: command object -- Called when actually deleted from the graph
        # actions:
        self.start_all()
        self._shutdown_event_id = reactor.addSystemEventTrigger("before", "shutdown", self.before_shutdown)

    #def __del__(self):
    #    self._looping_call.stop()

    def _guess_local_ip_and_hostname_for_local_host(self):
        """
        Lunch master guesses the hostname of the local machine, and should at least guess one IP (for one interface) 
        It adds it to the list local_addresses so that it doesn't use SSH to launch command here, in case the 
        programmer has added some commands on the localhost
        """
        # TODO: When the username is different than the current one, we should use a different uid, gid or SSH to our own host.
        self.local_addresses.append(socket.gethostname())
        try:
            self.local_addresses.append(socket.gethostbyname(socket.gethostname()))
        except socket.gaierror, e:
            log.error("Error getting IP of the local machine: " + str(e))

    def start_all(self):
        """
        Sets the master so that it starts all the slaves.
        """
        log.debug("Using %s" % (__file__))
        for c in self.commands.values():
            c.enabled = True
        self.prepare_all_commands()
        self.wants_to_live = True
    
    def add_command(self, command):
        """
        This method is wrapped (called) by the add_command function.
        @param command: L{lunch.commands.Command} object.
        """    
        # check if addr is local, set it to none if so.
        if command.host in self.local_addresses:
            log.info("Filtering out host %s since it is in list of local addresses." % (command.host))
            command.host = None    
        # set default names if they are none:
        if command.identifier is None:
            command.identifier = "default_%d" % (self.i) #TODO: use the first word of the command
            self.i += 1
        while command.identifier in self.commands: # making sure it is unique
            command.identifier += "X"
        self.tree.add_node(command.identifier, command.depends) # Adding it the the dependencies tree.
        self.commands[command.identifier] = command
        # calls the signal
        self.command_added_signal(command)

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
        #orphans = self.tree.get_supported_by(self.tree.ROOT)
        #self._manage_siblings(orphans, should_run=self.wants_to_live)
        #log.info("----- Managing slaves LOOP ----")

        self._time_now = time.time()
        iterator = graph.iter_from_root_to_leaves(self.tree)
        for current in iterator:
            if current != self.tree.ROOT:
                self._treat_node(current)

    def _treat_node(self, node):
        """
        Called once for each command on each main loop iteration.
        """
        command = self.commands[node]
        all_dependencies = self.tree.get_all_dependencies(node)
        all_dependees = self.tree.get_all_dependees(node)

        has_dependees_to_wait_for = False # to wait so that they quit
        for dependee_name in all_dependees:
            dependee = self.commands[dependee_name]
            if dependee.child_state != STATE_STOPPED:
                has_dependees_to_wait_for = True
        
        # If RUNNING, check if we should stop it:
        if command.child_state == STATE_RUNNING:
            self._stop_node_if_needed(node)
        elif command.child_state == STATE_STOPPED:
            self._start_node_if_needed(node)
            self._stop_nodes_that_depend_on_this_one(node)
        if command.to_be_deleted:
            self._delete_command(node)

    def _node_has_dependees_that_are_stopped(self, node):
        """
        Checks if this node has nodes which depend on it which are running.
        @rtype: C{bool}
        """
        command = self.commands[node]
        all_dependees = self.tree.get_all_dependees(node)

        ret = False 
        for dependee_name in all_dependees:
            dependee = self.commands[dependee_name]
            if dependee.child_state != STATE_STOPPED:
                ret = True
        return ret

    def _stop_nodes_that_depend_on_this_one(self, current_node):
        """
        Pre-condition: Node is not running. (might have changed a second ago)
        """
        all_dependees = self.tree.get_all_dependees(current_node)
        command = self.commands[current_node]
        if command.child_state == STATE_STOPPED:
            for dependee in all_dependees:
                other = self.commands[dependee]
                if other.child_state == STATE_RUNNING:
                    other.stop()
                    other.enabled = True # FIXME: that's very important
    
    def _stop_node_if_needed(self, node):
        """
        Pre-condition: Node is running.
        """
        command = self.commands[node]
        all_dependencies = self.tree.get_all_dependencies(node)
        all_dependees = self.tree.get_all_dependees(node)
        has_dependees_to_wait_for = self._node_has_dependees_that_are_stopped(node)
        
        if self.wants_to_live is False:
            command.stop()
        else:
            # check all node on which this node depends
            has_unsatisfied_dependency = False
            for dependency in all_dependencies:
                dep_command = self.commands[dependency]
                if dep_command.child_state != STATE_RUNNING and dep_command.respawn is False and dep_command.how_many_times_run != 0:
                    has_unsatisfied_dependency = True
                    break
            if has_unsatisfied_dependency:
                log.info("Got to stop %s since it has unsatisfied dependencies." % (command.identifier)) 
                command.stop()
                        
    def _start_node_if_needed(self, node):
        """
        Pre-condition: Node is not running.
        """
        command = self.commands[node]
        all_dependencies = self.tree.get_all_dependencies(node)
        all_dependees = self.tree.get_all_dependees(node)
        has_dependees_to_wait_for = self._node_has_dependees_that_are_stopped(node)
        
        # self.launch_next_time is for launching the next process... so it must be updated as 
        # soon as we start one.
        if self.wants_to_live and self.launch_next_time <= self._time_now and command.enabled and command.is_ready_to_be_started():
            if has_dependees_to_wait_for: # We cannot start this node if there are nodes that depend on this one to be running.
                pass #command.stop()
            else:
                start_it = True
                if not command.is_ready_to_be_started():
                    start_it = False
                if not command.respawn and command.how_many_times_run >= 1:
                    start_it = False # already ran this once
                #
                # Do not start it if not enabled !
                # (maybe lived for not long enough)
                #if not command.enabled:
                #    start_it = False
                for dependency in all_dependencies:
                    dep_command = self.commands[dependency]
                    if dep_command.child_state != STATE_RUNNING and dep_command.respawn is True: 
                        start_it = False
                    elif dep_command.respawn is False and dep_command.how_many_times_run == 0:
                        start_it = False
                # Finally, start it if we are ready to.
                if start_it:
                    self.launch_next_time = self._time_now + command.sleep_after
                    log.info("Will start %s." % (command.identifier))
                    command.start()
    
    def _delete_command(self, node):
        """
        Actually deletes it.
        """
        ref = self.commands[node]
        del self.commands[node]
        #log.debug(self.commands)
        self.tree.remove_node(node) # XXX ?
        log.info("Removed command %s from the graph" % (node))
        self.command_removed_signal(ref)
        ref.quit_slave()

    def _get_all(self):
        """
        Returns all commands.
        """
        return self.commands.values()
    
    def get_command(self, identifier):
        """
        Returns a command identified by its identifier.
        Might raise a KeyError if it does not exist.
        
        @rtype: L{lunch.commands.Command}
        @param identifier: The identifier of the command to get.
        @type identifier: str
        """
        return self.commands[identifier]

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
        _commands = self._get_all()
        self.wants_to_live = False
        for c in _commands:
            if c.child_state in [STATE_RUNNING, STATE_STARTING]:
                c.stop()
            else:
                log.info("Command %s is already stopped." % (c))
        log.info("Done stopping all commands.")

    def remove_command(self, identifier):
        """
        Removes a command
        """
        if identifier in self.commands.keys():
            command = self.commands[identifier]
            if command.get_state_info() == STATE_RUNNING: #FIXME
                command.stop()
            command.to_be_deleted = True

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
        _commands = self._get_all()
        ready_to_restart = True
        for c in _commands:
            if c.child_state != STATE_STOPPED:
                ready_to_restart = False
                log.debug("Not yet ready to restart all since %s is still %s." % (c, c.child_state))
        if ready_to_restart:
            self.start_all()
            log.info("Restarting all.")
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
        MAXIMUM_TIME_TO_WAIT = 20.0
        if self.pid_file is not None:
            log.info("Will now erase the %s PID file" % (self.pid_file))
            try:
                os.remove(self.pid_file)
            except OSError, e:
                log.error("Error removing lunch master PID file: " + str(e))
            else:
                log.info("Erased %s" % (self.pid_file))
        now = time.time()
        _shutdown_data = {
                "shutdown_started" : now,
                "shutdown_time": now + MAXIMUM_TIME_TO_WAIT
            }
        deferred = defer.Deferred()
        def _later(self, data):
            again = False
            for c in self._get_all():
                if c.child_state == STATE_RUNNING:
                    log.info("Please wait... Slave %s is still running." % (c.identifier))
                    again = True
                    c.enabled = False
                    if c.slave_state == STATE_RUNNING:
                        # c.quit_slave()
                        c.send_stop()
            if not again:
                log.info("All child processes are successfully stopped.")
            if time.time() >= (data["shutdown_time"]):
                log.info("Max shutdown time expired.", logging.ERROR)
                for c in self._get_all():
                    if c.child_state != STATE_STOPPED:
                        log.critical("CHILD PROCESS %s IS IN STATE %s." % (c.identifier, c.child_state))
                again = False
            # -------------------- Finally:
            if again:
                reactor.callLater(0.1, _later, self, data)
            else:
                log.info("Done stopping the Lunch Master.")
                deferred.callback(True) # stops reactor
        
        _later(self, _shutdown_data)
        return deferred

    def cleanup(self):
        """
        Cleans up the reactor stuff.
        @rtype: L{twisted.defer.DeferredList}
        """
        log.info("_cleanup the Master")
        deferreds = []
        reactor.removeSystemEventTrigger(self._shutdown_event_id)
        # quit all slaves
        for command in self.get_all_commands():
            if command.slave_state == STATE_RUNNING:
                deferreds.append(command.quit_slave())
        # stop the master's loop
        if self._looping_call.running:
            d = self._looping_call.deferred
            self._looping_call.stop() # FIXME
            deferreds.append(d)
        return defer.DeferredList(deferreds)
        
def _validate_identifier(identifier):
    """
    Raises a RuntimeError if the identifier is not valid.
    
    Identifiers must not contain spaces or invalid characters for a file name.
    """
    if " " in identifier:
        raise RuntimeError("Identifier must not contain spaces: %s" % (identifier))
    if ":" in identifier:
        raise RuntimeError("Identifier must not contain colons: %s" % (identifier))
    if "/" in identifier:
        raise RuntimeError("Identifier must not contain slashes: %s" % (identifier))

def gen_id_from_config_file_name(config_file_name="lunchrc"):
    """
    Returns an identifier for the master using the config file name.
    Useful so that there is not two masters running with the same config file.
    @rettype str
    """
    file_name = os.path.split(config_file_name)[1] # remove dir name
    identifier = file_name.replace(".", "") # getting rid of the dot in file name
    return identifier

def gen_pid_file_path(identifier="lunchrc", directory=None):
    """
    Returns a PID file name. 

    Creates the directory if it does not exist.
    @return: Full path of the PID file for that master.
    """
    file_name = "lunch-pid-master-%s.pid" % (identifier)
    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.isdir(directory):
        raise RuntimeError("The path %s should be a directory, but is not." % (directory))
    pid_file = os.path.join(directory, file_name)
    return pid_file

def is_lunch_master_running(pid_file):
    """
    Checks if a master is running, given its PID file.
    Removes the PID file if it's not running.
    
    @param pid_file: Full path of a PID file for a master.
    @return: PID of the master if running. None if not. 
    """
    if os.path.exists(pid_file):
        f = open(pid_file, 'r')
        pid = f.read()
        f.close()
        try:
            os.kill(int(pid), 0) # if it throws, it's dead
        except OSError: # no process with that ID
            os.remove(pid_file)
            return None
        except ValueError: # invalid int. (pidfile did not contain an int)
            os.remove(pid_file)
            return None
        else:
            # checks if it's really a lunch master that has this ID.
            command_check_master = "ps aux | grep %d | grep -v grep" % (int(pid))
            #d = run_and_wait("bash", ["-c", command_check_master])
            # blocking... it's easier to debug for now
            # TODO: get rid of subprocess here.
            output = subprocess.Popen(command_check_master, stdout=subprocess.PIPE, shell=True).communicate()[0]
            if "python" in output:# used to be "lunch", but changed it to "python", since lunch.master is now a livrary as well.
                return int(pid)
            else:
                #print "found PID, but it's not lunch!"
                os.remove(pid_file)
                return None
    else:
        return None

def write_master_pid_file(identifier="lunchrc", directory=None):
    """
    Writes master's PID in a file.
    
    Raises an error if a master with that PID already exists.
    @return: pid file name.
    """
    # Check if there is already a master running
    pid_file = gen_pid_file_path(identifier, directory)
    if os.path.exists(pid_file):
        log.warning("PID file for master %s found!" % (pid_file))
        pid = is_lunch_master_running(pid_file)
        if pid is not None:
            raise RuntimeError("There is already a Lunch Master running using the same configuration file. Its PID is %s" % (pid))
        else:
            pass
    # Write our PID file
    f = open(pid_file, 'w')
    pid = os.getpid()
    f.write(str(pid))
    f.close()
    os.chmod(pid_file, 0600)
    log.info("Wrote master's PID %d to file %s." % (pid, pid_file))
    return pid_file

def kill_master_if_running(identifier="lunchrc", directory=None):
    """
    Given a lunch master identifier and a PID file directory, kills the master.
    """
    pid_file = gen_pid_file_path(identifier, directory)
    deferred = defer.Deferred()
    send_sigkill_at = time.time() + 20.0 # wait 20 seconds before to use kill -9 
    is_first_time_called = True
    
    def _kill(is_first_time_called=False):
        #we check if running several time before to send it SIGKILL
        if os.path.exists(pid_file):
            log.info("PID file for master %s found!" % (pid_file))
            pid = is_lunch_master_running(pid_file)
            if pid is not None:
                if is_first_time_called:
                    log.warning("Sending SIGINT to the lunch master %s." % (identifier))
                    os.kill(pid, signal.SIGINT)
                    reactor.callLater(0.2, _kill)
                else:
                    if time.time() > send_sigkill_at:
                        log.warning("Sending SIGKILL to the lunch master %s." % (identifier))
                        os.kill(signal.SIGKILL)
                        deferred.callback(None)
                    else:
                        log.debug("The lunch master %s is not dead yet." % (identifier))
                        reactor.callLater(0.2, _kill)
            else:
                if is_first_time_called:
                    log.warning("The lunch master %s was not running." % (identifier))
                deferred.callback(None)
        else:
            if is_first_time_called:
                log.info("Could not find a PID file for master %s." % (identifier))
            deferred.callback(None)
    
    reactor.callLater(0.01, _kill, True)
    return deferred

def start_file_logging(identifier="lunchrc", directory=None, log_level='info'):
    """
    Starts logging the Master infos to a file.
    @rettype: str
    """
    global log
    file_name = "master-%s.log" % (identifier)
    if not os.path.exists(directory):
        os.makedirs(directory)
    full_path = os.path.join(directory, file_name)
    f = open(full_path, 'w')
    f.close()
    os.chmod(full_path, 0600)
    #_log_file = logfile.BaseLogFile(file_name, directory)
    #_log_file = logfile.DailyLogFile(file_name, directory) #FIXME: do not use that DailyLogFile ! 
    #log.startLogging(_log_file)
    full_path = os.path.join(directory, file_name)
    log = logger.start(level=log_level, name=LOG_NAME, to_stdout=True, to_file=True, log_file_name=full_path)
    return full_path #_log_file.path

def chmod_file_not_world_writable(config_file):
    """
    Make a file not writable by other users.
    """
    mode = stat.S_IMODE(os.stat(config_file)[0])
    new_mode = (mode & stat.S_IRUSR) + (mode & stat.S_IWUSR) + (mode & stat.S_IXUSR)
    # user hase read/write/execute permissions
    # 256, 128 and 64
    try:
        os.chmod(config_file, new_mode)
    except OSError, e:
        log.warning("WARNING: Could not chmod configuration file. %s" % (e))

def execute_config_file(lunch_master, config_file, chmod_config_file=True):
    """
    Reads the lunch file and execute it as Python code.
    Also makes it non-writable by everyone else, just in case.
    @param config_file: Path to the lunch file. (such as a .lunchrc)
    Might raise a FileNotFoundError.
    
    The functions to which the user can access in their lunch files are defined here.
     * add_command
     * add_local_address
    
    The user can also access the lunch_master variable, which is the Lunch Master.
    """
    from lunch import commands
    def add_local_address(address):
        """
        Adds an IP to which not use SSH with.
        :param address: str or list of str. IP address or host name
        """
        # FIXME: what is that list thing? Why would we store lists of str?
        if type(address) is not list:
            addresses = [address]
        else:
            addresses = address
        for address in addresses:
            if address not in lunch_master.local_addresses:
                log.info("Adding %s in list of local addresses." % (address))
                lunch_master.local_addresses.append(address)
    # --------------------------------
    def add_command(command=None, identifier=None, env=None, user=None, host=None, group=None, order=None,
        sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None, sleep=None, depends=None, try_again_delay=0.25, give_up_after=0, ssh_port=None):
        """
        This is the only function that users use from within the configuration file.
        It adds a Command instance to the list of commands to run. 

        This function calls the Master.add_command static method, passing to it a L{lunch.commands.Command} object
        """
        # TODO: remove priority and sleep kwargs in a future version
        log.debug("Adding %s (%s) %s@%s" % (identifier, command, user, host))
        # ------------- warnings ------------------
        if group is not None:
            raise RuntimeError("Groups are deprecated. Use dependencies instead.")
        if identifier is not None:
            _validate_identifier(identifier)
        if sleep is not None:
            raise RuntimeError("The sleep keyword argument has been renamed to sleep_after.")
            sleep_after = sleep
        #if priority is not None:
        #    warnings.warn("The priority keyword argument does not exist anymore. Only the order in which add_command calls are done is considered.", DeprecationWarning)
        if log_dir is None:
            log_dir = lunch_master.log_dir
        #TODO: if pid_dir is None:
        #         pid_dir = lunch_master.pid_dir
        c = commands.Command(command=command, env=env, host=host, user=user, order=order, sleep_after=sleep_after, respawn=respawn, minimum_lifetime_to_respawn=minimum_lifetime_to_respawn, log_dir=log_dir, identifier=identifier, depends=depends, try_again_delay=try_again_delay, give_up_after=give_up_after, ssh_port=ssh_port)
        lunch_master.add_command(c)
    # -------------------------------------
    #global _commands # is this necessary?
    if os.path.exists(config_file):
        if os.path.isdir(config_file):
            raise RuntimeError("The config file %s is a directory." % (config_file))
        if chmod_config_file:
            chmod_file_not_world_writable(config_file)
        try:
            execfile(config_file) # config is plain python using the globals defined here. (the add_process function)
        except Exception, e:
            log.error("ERROR: Error in user configuration file.")
            raise
    else:
        # create the directory ?
        raise FileNotFoundError("ERROR: Could not find the %s file." % (config_file))

def start_logging(identifier='lunchrc', log_to_file=False, log_dir=None, log_level='info'):
    """
    Starts logging - either to a file or not.
    """
    if log_to_file:
        log_file = start_file_logging(identifier=identifier, directory=log_dir, log_level=log_level)
    else:
        start_stdout_logging(log_level=log_level)
        log_file = None
    log.info("Started logging.")
    return log_file

def create_dir_and_make_writable(directory):
    """
    Creates a directory if it does not exist, and make sure it is writable by us.
    @rtype: bool
    @return: success
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError, e:
            return False
    if os.access(directory, os.W_OK):
        return True
    else:
        return False

def run_master(config_file, log_to_file=False, pid_dir=None, log_dir=None, chmod_config_file=True, verbose=False, log_level="info"):
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
    master_identifier = gen_id_from_config_file_name(config_file)
    # TODO: make this non-blocking. (return a Deferred)

    # log dir:
    if log_dir is None:
        log_dir = get_default_log_dir_full_path()
    if not create_dir_and_make_writable(log_dir):
        raise RuntimeError("Logging directory is not writable: %s. Use the --logging-directory option" % (log_dir))
    # pid dir:
    if pid_dir is None:
        pid_dir = get_default_pid_dir_full_path()
    if not create_dir_and_make_writable(pid_dir):
        raise RuntimeError("PID directory is not writable: %s. Use the --pid-directory option" % (pid_dir))

    log_file = start_logging(identifier=master_identifier, log_to_file=log_to_file, log_dir=log_dir, log_level=log_level)
    pid_file = write_master_pid_file(identifier=master_identifier, directory=pid_dir)
    log.debug("-------------------- Starting master -------------------")
    log.info("Using lunch master module %s" % (__file__))
    lunch_master = Master(log_dir=log_dir, pid_file=pid_file, log_file=log_file, config_file=config_file, verbose=verbose)
    execute_config_file(lunch_master, config_file, chmod_config_file=chmod_config_file)
    # TODO: return a Deferred
    return lunch_master

