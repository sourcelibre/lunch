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
import os
import time
import sys
import logging

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import defer
from twisted.python import procutils
from twisted.python import log

#_log_file = twisted.python.logfile.DailyLogFile("lunch.log", os.getcwd())
log.startLogging(sys.stdout)
# usage: log.msg("qweqwe", logLevel=logging.INFO)


from lunch import sig
from lunch import constants as const

class MasterError(Exception):
    """
    Raised by the L{Master} when dealing with the L{SlaveProcessprotocol}
    """
    pass

class FileNotFoundError(Exception):
    """
    Thrown when a file could not be found.
    """
    pass

class SlaveProcessProtocol(protocol.ProcessProtocol):
    """
    Process of a Lunch Slave. (probably through SSH)
 
    The Lunch Master controls it by its stdin and monitors it with its stdout.
    """
    def __init__(self, command):
        """
        @param command: L{Command} instance.
        """
        self.command = command

    def connectionMade(self):
        """
        Called once the process is started.
        """
        self.command._on_connection_made()

    def outReceived(self, data):
        """
        Called when text is received from the managed process stdout
        Twisted will not splitlines, it gives an arbitrary amount of
        data at a time. This way, our manager only gets one line at 
        a time.
        """
        for line in data.splitlines():
            if line != "":
                self.command._received_message(line)

    def errReceived(self, data):
        """
        Called when text is received from the managed process stderr
        """
        for line in data.splitlines().strip():
            if line != "":
                log.msg("stderr: " + line + "\n")

    def processEnded(self, status):
        """
        Called when the managed process has exited.
        status is probably a twisted.internet.error.ProcessTerminated
        "A process has ended with a probable error condition: process ended by signal 1"
        
        This is called when all the file descriptors associated with the child 
        process have been closed and the process has been reaped. This means it 
        is the last callback which will be made onto a ProcessProtocol. 
        The status parameter has the same meaning as it does for processExited.
        """
        log.msg("Slave process ended." + str(status))
        self.command._on_process_ended(status)
    
    def inConnectionLost(self, data):
        log.msg("Slave stdin has closed." + str(data))

    def outConnectionLost(self, data):
        log.msg("Slave stdout has closed." + str(data))
    
    def errConnectionLost(self, data):
        log.msg("Slave stderr has closed." + str(data))

    def processExited(self, reason):
        """
        This is called when the child process has been reaped, and receives 
        information about the process' exit status. The status is passed in the form 
        of a Failure instance, created with a .value that either holds a ProcessDone 
        object if the process terminated normally (it died of natural causes instead 
        of receiving a signal, and if the exit code was 0), or a ProcessTerminated 
        object (with an .exitCode attribute) if something went wrong.
        """
        log.msg("process has exited " + str(reason))
    
class Command(object):
    """
    Command that a slave needs to run.
    Handles a SlaveProcessProtocol, which controls a lunch-slave process.
    """
    def __init__(self, command=None, identifier=None, env=None, user=None, host=None, group=None, order=100, sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None):
        """
        @param command: Shell string. The first item is the name of the name of the executable.
        @param identifier: Any string. Used as a file name, so avoid spaces and exotic characters.
        @param env: dict with environment variables to set for the process to run.
        """
        self.command = command
        self.identifier = identifier
        self.env = {}
        if env is not None:
            self.env.update(env)
        self.user = user
        self.host = host
        self.group = group
        self.order = order
        self.sleep_after = sleep_after
        self.respawn = respawn
        self.minimum_lifetime_to_respawn = minimum_lifetime_to_respawn #FIXME: rename
        self.log_dir = log_dir
        # ------- private attributes:
        self.state = const.STATE_IDLE # state of the Slave, not the process the slave handles
        self.state_changed_signal = sig.Signal()
        self.exitted_itself_signal = sig.Signal()
        if command is None:
            raise MasterError("You must provide a command to be run.")
        self._process_protocol = None
        self._process_transport = None
        self._slave_state = const.STATE_IDLE
    
    def start(self):
        """
        Starts the slave Lunch
        """
        if self.state == const.STATE_RUNNING:
            log.msg("Cannot start slave %s that is running." % (self.identifier))
            return # XXX
        if self.host is None and self.user is None:
            is_remote = False # not using SSH
            _command = ["lunch-slave", "--id", self.identifier]
        else:
            is_remote = True # using SSH
            _command = ["ssh"]
            if self.user is not None:
                _command.extend(["-l", self.user])
            _command.extend(["lunch-slave", "--id", self.identifier])
            # I hope you put your SSH key on the remote host !
            # FIXME: we should pop-up a terminal if keys are not set up.
        try:
            _command[0] = procutils.which(_command[0])[0]
        except IndexError:
            raise MasterError("Could not find path of executable %s." % (_command[0]))
        log.msg("Will run command %s" % (str(_command)))
        self._process_protocol = SlaveProcessProtocol(self)
        #try:
        if True:
            proc_path = _command[0]
            args = _command
            environ = {}
            for key in ['HOME', 'DISPLAY', 'PATH']: # passing a few env vars
                if os.environ.has_key(key):
                    environ[key] = os.environ[key]
            self.set_state(const.STATE_STARTING)
            log.msg("Starting: %s" % (self.identifier))
            self._process_transport = reactor.spawnProcess(self._process_protocol, proc_path, args, environ, usePTY=True)
    
    def _format_env(self):
        txt = ""
        for k, v in self.env.iteritems():
            txt += "%s=%s " % (k, v)
        return txt 
    
    def _on_connection_made(self):
        if const.STATE_STARTING:
            self.set_state(const.STATE_RUNNING)
        else:
            self.set_state(const.STATE_ERROR)
        def _later(self):
            self.send_message(const.COMMAND_COMMAND, self.command) # FIXME sends a string
            self.send_message(const.COMMAND_PING) # for fun
            self.send_message(const.COMMAND_ENV, self._format_env())
            self.send_message(const.COMMAND_START)
        reactor.callLater(0.1, _later, self) # FIXME !!!! not using callLater, but when it is really time !! we don't want self._process_transport to be None

    def send_message(self, key, data=""):
        """
        Sends a command to the slave.
        @param key: string
        @param data: string
        """
        self._process_transport.write("%s %s\n" % (key, data))
    
    def _received_message(self, line):
        """
        Received one line of text from the slave through its stdout.
        """
        #log.msg("%8s: %s" % (self.identifier, line))
        try:
            key = line.split(" ")[0]
            mess = line[len(key) + 1:]
        except IndexError:
            pass
        else:
            if key == const.MESSAGE_MSG:
                pass
            elif key == "log":
                log.msg("%8s: %s" % (self.identifier, mess))
            elif key == const.MESSAGE_ERROR:
                log.msg("%8s: %s" % (self.identifier, mess), logging.ERROR)
            elif key == const.MESSAGE_DIED:
                log.msg("%8s: %s" % (self.identifier, "DIED"), logging.ERROR)
            elif key == "pong":
                pass
                #log.msg("pong from %s" % (self.identifier))
            elif key == const.ANSWER_QUIT:
                log.msg("%8s: %s" % (self.identifier, "QUITTING !!!"), logging.ERROR)
            elif key == const.MESSAGE_STATE:
                words = mess.split(" ")
                previous_state = self._slave_state
                new_state = words[0]
                self._slave_state = new_state # IMPORTANT !
                log.msg("%8s: %s" % (self.identifier, "state: %s" % (new_state)))
                if new_state in [const.STATE_STOPPED, const.STATE_ERROR]:
                    log.msg("Master will now force-quit the slave %s." % (self.identifier))
                    # XXX FIXME
                    self.quit_slave() # FIXME restarts once it is dead

    def stop(self):
        """
        Tells the slave to stop its process.
        """
        if self._slave_state == const.STATE_RUNNING:
            log.msg('Will stop process %s.' % (self.identifier))
            self.send_message(const.COMMAND_STOP)
    
    def quit_slave(self):
        """
        Stops the slave Lunch
        """
        if self.state == const.STATE_SLAVE_DEAD:
            log.msg("Cannot stop the slave process %s that is in \"%s\" state." % (self.identifier, self.state))
            self.state = const.STATE_STOPPED
        else:
            if self.state in [const.STATE_RUNNING, const.STATE_STARTING, const.STATE_STARTING]:
                self.set_state(const.STATE_STOPPING)
                log.msg('Master will stop process of Lunch slave %s.' % (self.identifier))
                self._process_transport.loseConnection()
            else:
                self.state = const.STATE_STOPPED

    def _on_process_ended(self, reason):
        if self.state == const.STATE_STARTING:
            log.msg("Slave %s died during startup." % (self.identifier), logging.ERROR)
            #self.set_state(const.STATE_ERROR)
            self.set_state(const.STATE_STOPPED)
        elif self.state == const.STATE_RUNNING:
            """ Don't error out if we exitted with exit code 0 (for now) """
            if str(reason).find('exit code 0') != -1:
                log.msg('Luncher %s exited cleanly.' % (self.identifier))
                self.exitted_itself_signal()
            else:
                log.msg('Luncher %s exited with error.' % (self.identifier))
                #self.set_state(const.STATE_ERROR)
                self.set_state(const.STATE_STOPPED)
        if self.state == const.STATE_STOPPING:
            log.msg('Luncher exited as expected.')
            self.set_state(const.STATE_STOPPED)
        #if self.verbose:
        #    print("%s process ended. Reason: \n%s" % (self.name, str(reason)))
        if self.respawn:
            # XXX FIXME
            log.msg("Restarting the slave %s." % (self.identifier), logging.INFO)
            self.start()
        
    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            self.state_changed_signal(self.state)

# IMPORTANT global var !!
_commands = {"default": []} # keys are group names, values are a list of Command objects.

def add_command(command=None, title=None, env=None, user=None, host=None, group=None, order=100, sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None):
    """
    This is the only function that users use from within the configuration file.
    It adds a Command instance to the list of commands to run. 
    
    Default priority is 100. The lowest the earliest.
    """
    #FIXME: Changed back identifier to title.
    global _commands
    log.msg("DEBUG: adding %s %s %s %s %s %s %s %s" % (command, env, host, user, order, sleep_after, respawn, log_dir)) # EDIT ME
    if group is None:
        group = "default" # default group is 0
    if not _commands.has_key(group):
        log.msg("Adding group %s" % (group))
        _commands[group] = []
    _commands[group].append(Command(command=command, env=env, host=host, user=user, order=order, sleep_after=sleep_after, respawn=respawn, log_dir=log_dir, identifier=title)) # EDIT ME

def _sorting_callback(x, y):
    """
    Sorts Command objects using their order attribute.
    
    To define a compare function for sort(), you must follow certain pattern.
    1. Compare function must take TWO param: x and y,
    2. It should return positive number if x > y, return negative number if x< y and return 0 if they are equal for Ascending sort.
    """
    if x.order > y.order:
        return 1
    elif x.order < y.order:
        return -1
    else:
        return 0

class Master(object):
    def __init__(self):
        global _commands
        reactor.callLater(0.025, self._cl)
        self.commands = _commands
    
    def _cl(self):
        """
        Called once reactor is running.
        """
        self.start_all()

    def start_all(self):
        i = 0 # for default identifiers
        
        for group in self.commands.iterkeys():
            commands_in_group = self.commands[group]
            commands_in_group.sort(_sorting_callback)
            for c in commands_in_group:
                if c.identifier is None:
                    c.identifier = "default-%d" % (i)
                    i += 1
                c.start() # FIXME TODO: sleep between each !!!!

    def stop_all(self):
        for group in self.commands.iterkeys():
            commands_in_group = self.commands[group]
            commands_in_group.sort(_sorting_callback) # FIXME: we should use an other sorting callback here.
            for c in commands_in_group:
                s.respawn = False
                c.stop()

    def quit_master(self):
        """
        Stops all slaves and quits the application.
        """
        reactor.stop()

    def before_shutdown(self):
        _shutdown_data = {
                "time" : time.time(),
                "max_shutdown_time": 2.0
            }
        deferred = defer.Deferred()
        def _later(self, data):
            again = False
            for group in self.commands.iterkeys():
                commands_in_group = self.commands[group]
                commands_in_group.sort(_sorting_callback) # FIXME: we should use an other sorting callback here.
                for c in commands_in_group:
                    if c._slave_state == const.STATE_RUNNING:
                        log.msg("Slave %s is still running. Stopping it." % (c.identifier))
                        again = True
                        c.respawn = False
                        c.quit_slave()
            if data["time"] + time.time() >= data["max_shutdown_time"]:
                log.msg("Max shutdown time expired.", logging.ERROR)
                again = False
            if again:
                reactor.callLater(0.1, _later, self, data)
            else:
                log.msg("Stopping Lunch.")
                deferred.callback(True) # stops reactor
        
        _later(self, _shutdown_data)
        return deferred

def run_master(config_file):
    """
    Runs the master that calls commands using ssh or so.

    This happens only on the master computer.
     * reads config file
     * uses multiprocessing to create many workers. (calling start_worker)
       Those worker launch the "lunch" program in a xterm terminal.
       (maybe through ssh, if on a remote host)
     * If ctrl-C is pressed from any worker, dies.
    @rettype Master
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
    m = Master()
    reactor.addSystemEventTrigger("before", "shutdown", m.before_shutdown)
    return m

