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
from twisted.internet import error
from twisted.internet import reactor
from twisted.internet import defer
from twisted.python import procutils
from twisted.python import log

from lunch import sig

# constants for the slave process
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING"
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED"
STATE_NOSLAVE = "NOSLAVE" # for master only

# Keys of the commands from the master :

def start_logging():
    #_log_file = twisted.python.logfile.DailyLogFile("lunch.log", os.getcwd())
    log.startLogging(sys.stdout)
    # usage: log.msg("qweqwe", logLevel=logging.INFO)

class MasterError(Exception):
    """
    Raised by the L{Master} when dealing with the L{SlaveProcessprotocol}
    """
    pass

class FileNotFoundError(Exception):
    """
    Thrown when the given config file could not be found.
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

    def processEnded(self, reason):
        """
        Called when the managed process has exited.
        status is probably a twisted.internet.error.ProcessTerminated
        "A process has ended with a probable error condition: process ended by signal 1"
        
        This is called when all the file descriptors associated with the child 
        process have been closed and the process has been reaped. This means it 
        is the last callback which will be made onto a ProcessProtocol. 
        The status parameter has the same meaning as it does for processExited.
        """
        exit_code = reason.value.exitCode
        log.msg("Slave %s process ended with %s." % (self.command.identifier, exit_code))
        self.command._on_process_ended(reason.value.exitCode)
    
    def inConnectionLost(self, data):
        pass #log.msg("Slave stdin has closed. %s" % (str(data)))

    def outConnectionLost(self, data):
        pass #log.msg("Slave stdout has closed. %s" % (str(data)))
    
    def errConnectionLost(self, data):
        pass #log.msg("Slave stderr has closed. %s" % (str(data)))

    def processExited(self, reason):
        """
        This is called when the child process has been reaped, and receives 
        information about the process' exit status. The status is passed in the form 
        of a Failure instance, created with a .value that either holds a ProcessDone 
        object if the process terminated normally (it died of natural causes instead 
        of receiving a signal, and if the exit code was 0), or a ProcessTerminated 
        object (with an .exitCode attribute) if something went wrong.
        """
        exit_code = reason.value.exitCode
        log.msg("process has exited : %s." % (str(exit_code)))
    
class Command(object):
    """
    Command that a slave needs to run.
    Handles a SlaveProcessProtocol, which controls a lunch-slave process.
    """
    #TODO: add gid
    #TODO: add uid
    #TODO: add delay_kill
    #TODO: add clear_old_logs
    #TODO: add time_started
    #TODO: add enabled. (for respawning or not a process, without changing its respawn attribute.
    
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
        self.enabled = True 
        self.minimum_lifetime_to_respawn = minimum_lifetime_to_respawn #FIXME: rename
        self.log_dir = log_dir
        # ------- private attributes:
        self.slave_state = STATE_STOPPED # state of the Slave, not the process the slave handles
        self.child_state = STATE_STOPPED # state of the child process of the slave.
        self.slave_state_changed_signal = sig.Signal()
        self.child_state_changed_signal = sig.Signal()
        if command is None:
            raise MasterError("You must provide a command to be run.")
            #self.send_stop()
        self._process_protocol = None
        self._process_transport = None
    
    def start(self):
        """
        Starts the slave Lunch
        """
        if self.slave_state in [STATE_RUNNING, STATE_STARTING, STATE_STOPPING]:
            log.msg("Cannot start slave %s that is %s." % (self.identifier, self.slave_state))
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
        proc_path = _command[0]
        args = _command
        environ = {}
        for key in ['HOME', 'DISPLAY', 'PATH']: # passing a few env vars
            if os.environ.has_key(key):
                environ[key] = os.environ[key]
        self.set_slave_state(STATE_STARTING)
        log.msg("Starting: %s" % (self.identifier))
        self._process_transport = reactor.spawnProcess(self._process_protocol, proc_path, args, environ, usePTY=True)
    
    def _format_env(self):
        txt = ""
        for k, v in self.env.iteritems():
            txt += "%s=%s " % (k, v)
        return txt 
    
    def _on_connection_made(self):
        """
        Here, we send all the commands to the slave.
        """
        if self.slave_state == STATE_STARTING:
            self.set_slave_state(STATE_RUNNING)
        else:
            msg = "Connection made with slave %s, even if not expecting it." % (self.identifier)
            log.msg(msg, logging.ERROR)

    def send_do(self):
        """
        Send to the slave the command line to luanch its child.
        """
        self.send_message("do", self.command) # FIXME sends a string
    
    def send_ping(self):
        self.send_message("ping") # for fun

    def send_run(self):
        self.send_message("run")
        
    def send_env(self):
        self.send_message("env", self._format_env())

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
        except IndexError, e:
            log.msg("Index error parsing message from slave. %s" % (e), logging.ERROR)
        else:
            # Dispatch the command to the appropriate method.  Note that all you
            # need to do to implement a new command is add another do_* method.
            try:
                method = getattr(self, 'recv_' + key)
            except AttributeError, e:
                log.msg('No callback for "%s" got from slave %s.' % (key, self.identifier), logging.ERROR)
            else:
                method(mess)

    def recv_ok(self, mess):
        """
        Callback for the "ok" message from the slave.
        """
        pass

    def recv_msg(self, mess):
        """
        Callback for the "msg" message from the slave.
        """
        pass
    
    def recv_log(self, mess):
        """
        Callback for the "log" message from the slave.
        """
        log.msg("%8s: %s" % (self.identifier, mess))

    def recv_error(self, mess):
        """
        Callback for the "error" message from the slave.
        """
        log.msg("%8s: %s" % (self.identifier, mess), logging.ERROR)
    
    def recv_pong(self, mess):
        """
        Callback for the "pong" message from the slave.
        """
        pass #log.msg("pong from %s" % (self.identifier))

    def recv_bye(self, mess):
        """
        Callback for the "bye" message from the slave.
        """
        log.msg("%8s: %s" % (self.identifier, "QUITTING !!!"), logging.ERROR)

    def recv_state(self, mess):
        """
        Callback for the "state" message from the slave.
        Received child state.
        """
        words = mess.split(" ")
        previous_state = self.child_state
        new_state = words[0]
        self.set_child_state(new_state) # IMPORTANT !
        log.msg("Child %8s: %s" % (self.identifier, "state: %s" % (new_state)))
        if new_state == STATE_STOPPED and self.enabled and self.respawn:
            self.send_all_startup_commands()
        elif new_state == STATE_RUNNING:
            log.msg("Child %s is running." % (self.identifier))

    def recv_ready(self, mess):
        """
        Callback for the "ready" message from the slave.
        The slave sends that to the master when launched.
        It means it is ready to received commands.
        """
        if self.enabled:
            self.send_all_startup_commands()

    def send_all_startup_commands(self):
        """
        Tells the slave to launch its child process.
        Sets up the environment and command so that the slave can launch the child.
        """
        self.send_do()
        self.send_env()
        #self.send_ping()
        self.send_run()

    def set_child_state(self, new_state):
        """
        Called when it is time to change the state of the child of the slave.
        """
        if self.child_state != new_state:
            self.child_state = new_state
            self.child_state_changed_signal(self.child_state)

    def stop(self):
        """
        Tells the slave to stop its child.
        """
        if self.child_state in [STATE_RUNNING, STATE_STARTING]:
            log.msg('Will stop process %s.' % (self.identifier))
            self.send_stop()
        else:
            msg = "Cannot stop child %s that is %s." % (self.identifier, self.child_state)
            log.msg(msg, logging.ERROR)

    def send_stop(self):
        self.send_message("stop")
    
    def quit_slave(self):
        """
        Stops the slave Lunch
        """
        def _cl_sigint(self):
            def _cl_sigkill(self):
                if self.slave_state == STATE_STOPPING:
                    self._process_transport.signalProcess(9) # signal.SIGKILL
        
        if self.slave_state == STATE_STOPPED:
            log.msg("Cannot stop the slave process %s that is in \"%s\" state." % (self.identifier, self.slave_state), logging.ERROR)
        else:
            if self.slave_state in [STATE_RUNNING, STATE_STARTING]:
                if self.child_state in [STATE_RUNNING, STATE_STARTING]:
                    self.send_stop()
                elif self.child_state == STATE_STOPPED:
                    self._process_transport.signalProcess(15) # signal.SIGTERM
                self.set_slave_state(STATE_STOPPING)
                log.msg('Master will stop slave %s.' % (self.identifier))
            elif self.slave_state == STATE_STOPPING:
                # second time this is called, force-quitting:
                log.msg("kill -9 Slave %s" % (self.identifier))
                self._process_transport.signalProcess(9) # signal.SIGKILL

    def _on_process_ended(self, exit_code):
        #log.msg("Exit code: " % (exit_code))
        former_slave_state = self.slave_state
        if former_slave_state == STATE_STARTING:
            log.msg("Slave %s died during startup." % (self.identifier), logging.ERROR)
        elif former_slave_state == STATE_RUNNING:
            if exit_code == 0:
                log.msg("Slave %s exited." % (self.identifier))
            else:
                log.msg('Slave %s exited with error %s.' % (self.identifier, exit_code))
        elif former_slave_state == STATE_STOPPING:
            log.msg('Slave exited as expected.')
        self.set_slave_state(STATE_STOPPED)
        self._process_transport.loseConnection()
        if self.respawn and self.enabled:
            log.msg("Restarting the slave %s." % (self.identifier), logging.INFO)
            self.start()
        
    def set_slave_state(self, new_state):
        log.msg("Slave %s is %s." % (self.identifier, new_state))
        if self.slave_state != new_state:
            self.slave_state = new_state
            self.slave_state_changed_signal(self.slave_state)
    

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

class Group(object):
    def __init__(self, name):
        self.state = STATE_STOPPED
        self.commands = []

class Master(object):
    def __init__(self):
        global _commands
        reactor.callLater(0.025, self._cl)
        self.commands = _commands
        self.groups = {"default": Group("default")}
    
    def _cl(self):
        """
        Called once reactor is running.
        """
        self.start_all()

    def start_all(self, group_name=None):
        groups = self._get_all_in_group(group_name)
        i = 0 # for default identifiers
        for group in groups:
            commands_in_group = self.commands[group]
            commands_in_group.sort(_sorting_callback)
            for c in commands_in_group:
                if c.identifier is None:
                    c.identifier = "default-%d" % (i)
                    i += 1
                c.start() # FIXME TODO: sleep between each !!!!
    
    def _get_all_in_group(self, group_name=None):
        """
        If group_name is None, returns all groups.
        """
        if group_name is not None:
            groups = [self.commands[group_name]] # a 1-element list
        else:
            groups = self.commands.keys()
        return groups
    
    def stop_all(self, group_name=None):
        groups = self._get_all_in_group(group_name)
        for group in groups:
            commands_in_group = self.commands[group]
            commands_in_group.sort(_sorting_callback) # FIXME: we should use an other sorting callback here.
            for c in commands_in_group:
                s.enabled = False
                # TODO: callLaters...
                c.stop()

    def restart_all(self, group_name=None):
        groups = self._get_all_in_group(group_name)
        for group in groups:
            commands_in_group = self.commands[group]
            commands_in_group.sort(_sorting_callback) # FIXME: we should use an other sorting callback here.
            for c in commands_in_group:
                s.enabled = False
                c.stop()
            all = self.commands[group_name]
            iterator = iter(all)

    def quit_master(self):
        """
        Stops all slaves and quits the application.
        """
        reactor.stop()

    def before_shutdown(self):
        now = time.time()
        _shutdown_data = {
                "shutdown_started" : now,
                "shutdown_time": now + 1.0
            }
        deferred = defer.Deferred()
        def _later(self, data):
            again = False
            for group in self.commands.iterkeys():
                commands_in_group = self.commands[group]
                commands_in_group.sort(_sorting_callback) # FIXME: we should use an other sorting callback here.
                for c in commands_in_group:
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
    start_logging()
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

