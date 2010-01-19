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

# constants for the slave process
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING"
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED"
STATE_NOSLAVE = "NOSLAVE" # for master only

def start_stdout_logging():
    log.startLogging(sys.stdout)

class MasterError(Exception):
    """
    Raised by the L{Master} when dealing with the L{SlaveProcessprotocol}
    """
    pass

def run_and_wait(executable, *arguments):
    """
    Runs a command and trigger its deferred with the output when done.
    Returns a deferred.
    """
    # TODO: use it.
    try:
        executable = procutils.which(executable)[0]
    except IndexError:
        msg = "Could not find executable %s" % (executable)
        return failure.Failure(MasterError(msg))
    d = utils.getProcessOutput(executable, arguments)
    def cb(result, executable, arguments):
        print 'Call to %s %s returned.\nResult: %s\n' % (executable, arguments, result)
        return result
    def eb(reason, executable, arguments):
        print 'Calling %s %s failed.\nError: %s' % (executable, arguments, reason)
        return reason
    d.addCallback(cb, executable, list(arguments))
    d.addErrback(eb, executable, list(arguments))
    return d

#reactor.callLater(0, run_and_wait, 'echo', 'Hello')
#reactor.callLater(1.0, reactor.stop)
#reactor.run()

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
    #TODO: move send_* and recv_* methods to the SlaveProcessProtocol.
    #TODO: add wait_returned attribute. (commands after which we should wait them to end before calling next)
    
    def __init__(self, command=None, identifier=None, env=None, user=None, host=None, group=None, order=None, sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None, depends=None):
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
        self.depends = depends
        self.how_many_times_run = 0
        self.minimum_lifetime_to_respawn = minimum_lifetime_to_respawn #FIXME: rename
        if log_dir is None:
            log_dir = "/var/tmp/lunch"# XXX Overriding the child's log dir.
            # XXX: used to be something like:
            #SLAVE_LOG_SUBDIR = "lunch_log"
            #slave_log_dir = os.path.join(os.getcwd(), SLAVE_LOG_SUBDIR)
        self.child_log_dir = log_dir # for both slave and child. If not set, defaults to $PWD/lunch_log
        self.slave_log_dir = self.child_log_dir
        # ------- private attributes:
        self.slave_state = STATE_STOPPED # state of the Slave, not the process the slave handles
        self.child_state = STATE_STOPPED # state of the child process of the slave.
        self.slave_state_changed_signal = sig.Signal() # param: self, new_state
        self.child_state_changed_signal = sig.Signal() # param: self, new_state
        if command is None:
            raise MasterError("You must provide a command to be run.")
            #self.send_stop()
        self._process_protocol = None
        self._process_transport = None
        # Some attributes might be changed by the master, namely identifier and host.
        # That's why we sait until start() is called to initiate the slave_logger.
        self.slave_logger = None
        self.scheduled_launch_time = None # None or float (if planning to launch, None otherwise) 
    
    def _start_logger(self):
        if self.slave_logger is None:
            # the slave log file
            slave_log_file = "slave-%s.log" % (self.identifier)
            if not os.path.exists(self.slave_log_dir):
                try:
                    os.makedirs(self.slave_log_dir)
                except OSError, e:
                    raise MasterError("You need to be able to write in the current working directory in order to write log files. %s" % (e))
            self.slave_logger = logfile.LogFile(slave_log_file, self.slave_log_dir)
    
    def start(self):
        """
        Starts the slave Lunch and its child if not started. If started, starts its child.
        """
        self.enabled = True
        self._start_logger()
        if self.slave_state == STATE_RUNNING and self.child_state == STATE_STOPPED:
            self.send_all_startup_commands()
        elif self.child_state in [STATE_STOPPING, STATE_STARTING]:
            self.log("Cannot start child %s that is %s." % (self.identifier, self.child_state))
        else:
            if self.slave_state in [STATE_RUNNING, STATE_STARTING, STATE_STOPPING]:
                self.log("Cannot start slave %s that is %s." % (self.identifier, self.slave_state))
                return # XXX
            else: # slave is STOPPED
                if self.host is None:
                    # if self.user is not None:
                        # TODO: Set gid if user is not None...
                    is_remote = False # not using SSH
                    _command = ["lunch-slave", "--id", self.identifier]
                else:
                    self.log("We will use SSH since host is %s" % (self.host))
                    is_remote = True # using SSH
                    _command = ["ssh"]
                    if self.user is not None:
                        _command.extend(["-l", self.user])
                    _command.extend([self.host])
                    _command.extend(["lunch-slave", "--id", self.identifier])
                    # I hope you put your SSH key on the remote host !
                    # FIXME: we should pop-up a terminal if keys are not set up.
                try:
                    _command[0] = procutils.which(_command[0])[0]
                except IndexError:
                    raise MasterError("Could not find path of executable %s." % (_command[0]))
                log.msg("Will run command: %s" % (" ".join(_command)))
                self._process_protocol = SlaveProcessProtocol(self)
                #try:
                proc_path = _command[0]
                args = _command
                environ = {}
                environ.update(os.environ) # passing the whole env (for SSH keys and more)
                self.set_slave_state(STATE_STARTING)
                self.log("Starting: %s" % (self.identifier))
                self._process_transport = reactor.spawnProcess(self._process_protocol, proc_path, args, environ, usePTY=True)
    
    def _format_env(self):
        txt = ""
        for k, v in self.env.iteritems():
            txt += "%s=%s " % (k, v)
        return txt 
    
    def _on_connection_made(self):
        if self.slave_state == STATE_STARTING:
            self.set_slave_state(STATE_RUNNING)
        else:
            msg = "Connection made with slave %s, even if not expecting it." % (self.identifier)
            self.log(msg, logging.ERROR)

    def send_do(self):
        """
        Send to the slave the command line to launch its child.
        """
        self.send_message("do", self.command) 
    
    def send_ping(self):
        self.send_message("ping") # for fun

    def send_run(self):
        self.send_message("run")
        
    def send_env(self):
        self.send_message("env", self._format_env())
    
    def send_logdir(self):
        self.send_message("logdir", self.child_log_dir)

    def send_message(self, key, data=""):
        """
        Sends a command to the slave.
        @param key: string
        @param data: string
        """
        msg = "%s %s\n" % (key, data)
        self.log("Master->%s: %s" % (self.identifier, msg.strip()))
        self._process_transport.write(msg)
    
    def __del__(self):
        if self.slave_logger is not None:
            self.slave_logger.close()
        
    def _received_message(self, line):
        """
        Received one line of text from the slave through its stdout.
        """
        #self.log("%8s: %s" % (self.identifier, line))
        
        try:
            words = line.split(" ")
            key = words[0]
            mess = line[len(key) + 1:]
        except IndexError, e:
            #self.log("Index error parsing message from slave. %s" % (e), logging.ERROR)
            self.log('From slave %s: %s' % (self.identifier, line), logging.ERROR)
        else:
            try:
                if words[1] == "password:":
                    self.log(line)
                    self.log("SSH ERROR: Trying to connect using SSH, but the SSH server is asking for a password.")
                    return
            except IndexError:
                pass
            # Dispatch the command to the appropriate method.  Note that all you
            # need to do to implement a new command is add another do_* method.
            if key in ["do", "env", "run", "logdir"]: # FIXME: receiving in stdin what we send to stdin slave !!!
                warnings.warn("We receive from the slave's stdout what we send to its stdin !")
            else:
                try:
                    method = getattr(self, 'recv_' + key)
                except AttributeError, e:
                    self.log('From slave %s: %s' % (self.identifier, line), logging.ERROR)
                    self.log(line)
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
        self.log("%s->Master: log %s" % (self.identifier, mess))

    def recv_error(self, mess):
        """
        Callback for the "error" message from the slave.
        """
        self.log("%8s->Master: %s" % (self.identifier, mess), logging.ERROR)
    
    def recv_pong(self, mess):
        """
        Callback for the "pong" message from the slave.
        """
        pass #self.log("pong from %s" % (self.identifier))

    def recv_bye(self, mess):
        """
        Callback for the "bye" message from the slave.
        """
        self.log("%s->Master: %s" % (self.identifier, "BYE (slave quits)"), logging.ERROR)

    def recv_state(self, mess):
        """
        Callback for the "state" message from the child.
        Received child state.
        """
        words = mess.split(" ")
        previous_state = self.child_state
        new_state = words[0]
        #print("%s's child state: %s" % (self.identifier, new_state))
        self.set_child_state(new_state) # IMPORTANT !
        self.log("%s->Master: child STATE is %s" % (self.identifier, new_state))
        if new_state == STATE_STOPPED and self.enabled and self.respawn:
            child_running_time = float(words[1])
            if child_running_time < self.minimum_lifetime_to_respawn:
                self.log("Not respawning child since its running time of %s has been shorter than the minimum of %s." % (child_running_time, self.minimum_lifetime_to_respawn))
                self.enabled = False # XXX
            #else:
            #    self.send_all_startup_commands()
        elif new_state == STATE_RUNNING:
            self.log("Child %s is running." % (self.identifier))

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
        self.send_logdir()
        self.send_env()
        #self.send_ping()
        self.send_run()

    def set_child_state(self, new_state):
        """
        Called when it is time to change the state of the child of the slave.
        """
        if self.child_state != new_state:
            if new_state == STATE_RUNNING:
                self.how_many_times_run += 1
            self.child_state = new_state
        #    log.msg(" --------------- XXX Trigerring signal %s" % (self.child_state))
            self.child_state_changed_signal(self, self.child_state)

    def stop(self):
        """
        Tells the slave to stop its child.
        """
        self.enabled = False
        if self.child_state in [STATE_RUNNING, STATE_STARTING]:
            self.log('Will stop process %s.' % (self.identifier))
            self.send_stop()
        else:
            msg = "Cannot stop child %s that is %s." % (self.identifier, self.child_state)
            self.log(msg, logging.ERROR)

    def send_stop(self):
        self.send_message("stop")
    
    def quit_slave(self):
        """
        Stops the slave Lunch
        If called for a second time, send kill -9 to slave.
        """
        def _cl_sigint(self):
            def _cl_sigkill(self):
                if self.slave_state == STATE_STOPPING:
                    self._process_transport.signalProcess(9) # signal.SIGKILL
        
        if self.slave_state == STATE_STOPPED:
            self.log("Cannot stop the slave process %s that is in \"%s\" state." % (self.identifier, self.slave_state), logging.ERROR)
        else:
            if self.slave_state in [STATE_RUNNING, STATE_STARTING]:
                if self.child_state in [STATE_RUNNING, STATE_STARTING]:
                    self.stop() # self.send_stop()
                elif self.child_state == STATE_STOPPED:
                    self._process_transport.signalProcess(15) # signal.SIGTERM
                self.set_slave_state(STATE_STOPPING)
                self.log('Master will stop slave %s.' % (self.identifier))
            elif self.slave_state == STATE_STOPPING:
                # second time this is called, force-quitting:
                self.log("kill -9 Slave %s" % (self.identifier))
                self._process_transport.signalProcess(9) # signal.SIGKILL

    def _on_process_ended(self, exit_code):
        """
        The slave died ! Its child is probably dead too.
        """
        #self.log("Exit code: " % (exit_code))
        former_slave_state = self.slave_state
        if former_slave_state == STATE_STARTING:
            self.log("Slave %s died during startup." % (self.identifier), logging.ERROR)
        elif former_slave_state == STATE_RUNNING:
            if exit_code == 0:
                self.log("Slave %s exited." % (self.identifier))
            else:
                self.log('Slave %s exited with error %s.' % (self.identifier, exit_code))
        elif former_slave_state == STATE_STOPPING:
            self.log('Slave exited as expected.')
        self.set_slave_state(STATE_STOPPED)
        self._process_transport.loseConnection()
        #if self.respawn and self.enabled:
        #    self.log("Restarting the slave %s." % (self.identifier), logging.INFO)
        #    self.start()
        
    def log(self, msg, level=logging.DEBUG):
        """
        Logs both to the slave's log file, and to the main app log. 
        """
        if self.slave_logger is not None:
            prefix = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.slave_logger.write("%s %s\n" % (prefix, msg))
            self.slave_logger.flush()
        log.msg(msg, level)

    def set_slave_state(self, new_state):
        msg = "Slave %s is %s." % (self.identifier, new_state)
        self.log(msg)
        if self.slave_state != new_state:
            self.slave_state = new_state
            self.slave_state_changed_signal(self.slave_state)

    def __str__(self):
        return "%s" % (self.identifier)
    
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
    c = Command(command=command, env=env, host=host, user=user, order=order, sleep_after=sleep_after, respawn=respawn, log_dir=log_dir, identifier=title, depends=depends)
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
        @param command: L{Command} object.
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
    
    def __init__(self, log_dir=None, pid_file=None, log_file=None, config_file=None):
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

        self._looping_call = task.LoopingCall(self._manage_slaves)
        self._looping_call.start(0.5, False) # checks process to start/stop 20 times a second.
        self.wants_to_live = True # The master is either trying to make every child live or die. 
        reactor.callLater(0, self.start_all)

    def _manage_slaves(self):
        """
        Called in a looping call.
        This is actually the main loop of the application.
        """
        # Trying to make all child live. (False if in the process of quitting)
        #orphans = Master.tree.get_supported_by(Master.tree.ROOT)
        #self._manage_siblings(orphans, should_run=self.wants_to_live)
        
        current = Master.tree.ROOT
        visited = [] # list of visited nodes.
        stack = [] # stack of iterators
        while True:
            if current not in visited:
                visited.append(current)
                # DO YOUR STUFF HERE
                self._treat_node(current)
                children = g.get_supported_by(current)
                stack.append(iter(children))
            try:
                current = stack[-1].next()
            except StopIteration:
                stack.pop()
            except IndexError:
                break
    
    def _treat_node(self, node):
        command = Master.commands[node]
        if command.child_state == STATE_RUNNING:
            if self.wants_to_live is False:
                command.stop()
            else:
                kill_it = False
                for dependency in Master.tree.get_all_dependees(node):
                    dep_command = Master.commands[dependency]
                    if dep_command.child_state != STATE_RUNNING and dep_command.respawn is False and dep_command.how_many_times_run != 0:
                        kill_it = True
                if kill_it:
                    command.stop()
        elif command.child_state == STATE_STOPPED:
            if self.wants_to_live:
                start_it = True
                for dependency in Master.tree.get_all_dependees(node):
                    dep_command = Master.commands[dependency]
                    if dep_command.child_state != STATE_RUNNING and dep_command.respawn is True: 
                        start_it = False
                    elif dep_command.respawn is False and dep_command.how_many_times_run == 0:
                        start_it = False
                if start_it:
                    command.start()
                command.stop()
            
            
                    
            
        

    def _manage_siblings(self, siblings, should_run=True):
        """
        Starts/stops commands in a branch of the dependency tree.
        @param siblings: list of str. Command identifiers.
        """
        # get children of the root
        # get time now
        # if not started give them a time to be started, if it doesn't have one
        # if started, check if it has children
        # if so, give it a time to be started.
        time_to_wait = 0.0 # adding up sleep_after value of each slave
        now = time.time()
        for command_name in siblings:
            command = Master.commands[command_name]
            dependees = Master.tree.get_supported_by(command.identifier) # direct dependees
            all_dependees = Master.tree.get_all_dependees(command.identifier) # the whole subtree
            #log.msg("Dependees on %s are : %s" % (command.identifier, dependees))
            dependees_should_run = False
            
            if command.child_state == STATE_STOPPED:
                if command.enabled and should_run:
                    to_start = True
                    if command.respawn is False and command.how_many_times_run == 1:
                        to_start = False
                        dependees_should_run = True
                    if to_start and command.scheduled_launch_time is None: # avoiding to reschedule twice the same
                        # stop dependees!
                        self._manage_siblings(dependees, should_run=False)
                        # schedule this one to start.
                        time_to_wait += command.sleep_after
                        command.scheduled_launch_time = now + time_to_wait
                        log.msg("Scheduled %s to start in %f seconds." % (command.identifier, time_to_wait))
                    if command.scheduled_launch_time is not None:
                        if command.scheduled_launch_time >= now:
                            command.scheduled_launch_time = None
                            log.msg("Time to start %s" % (command.identifier))
                            command.start()
            else:
                if command.child_state == STATE_RUNNING:
                    if not should_run:
                    #    pass #command.start()
                    #else:
                        log.msg("Will stop %s since a process its depends on is dead." % (command.identifier))
                        command.stop()
                    self._manage_siblings(dependees, should_run=should_run) # TODO: stop children if this node is dead.
        
    def start_all(self):
        """
        Starts all slaves, iterating asynchronously.
        """
        # FIXME: right now, the commands are not in the right order.
        # TODO: delete this, use _manage_slaves 
        log.msg("Master.start_all()")
        self.wants_to_live = True
#        iter_commands = iter(self._get_all()) 
#        reactor.callLater(0, self._start_next, iter_commands)
#
#    def _start_next(self, iter_commands):
#        """
#        asynchronous iterating function
#        """
#        # TODO: delete this, use _manage_slaves 
#        c = None
#        try:
#            c = iter_commands.next()
#        except StopIteration:
#            log.msg("Done starting all commands.")
#        if c is not None:
#            #TODO: is c.respawn is False : slave.how_many_times_run == 0
#            log.msg("Starting command %s" % (c.identifier))
#            c.start()
#            sleep = c.sleep_after
#            reactor.callLater(sleep, self._start_next, iter_commands)
    
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
        reactor.callLater(0.1, _start_if_all_stopped)

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
            reactor.callLater(0.1, _start_if_all_stopped)

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
    """
    file_name = "master-%s.pid" % (identifier)
    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.isdir(directory):
        raise MasterError("The path %s should be a directory, but is not." % (directory))
    pid_file = os.path.join(directory, file_name)
    if os.path.exists(pid_file):
        f = open(pid_file, 'r')
        pid = f.read()
        f.close()
        try:
            os.kill(int(pid), 0) # if it throws, it's dead
        except OSError:
            os.remove(pid_file)
        else:
            raise MasterError("There is already a Lunch Master running using the same configuration file. Its PID is %s" % (pid))
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

def run_master(config_file, log_to_file=False, log_dir="/var/tmp/lunch", chmod_config_file=True):
    """
    Runs the master that calls commands using ssh or so.

    This happens only on the master computer.
     * reads config file
     * uses multiprocessing to create many workers. (calling start_worker)
       Those worker launch the "lunch" program in a xterm terminal.
       (maybe through ssh, if on a remote host)
     * If ctrl-C is pressed from any worker, dies.
    @rettype Master
    
    Might raise a MasterError or a FileNotFoundError
    """
    identifier = gen_id_from_config_file_name(config_file)
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
                print("WARNING: Could not chmod configuration file.")
        try:
            execfile(config_file) # config is plain python using the globals defined here. (the add_process function)
        except Exception, e:
            print("ERROR: Error in user configuration file.")
            raise
    else:
        # create the directory ?
        raise FileNotFoundError("ERROR: Could not find the %s file." % (config_file))
    m = Master(log_dir=log_dir, pid_file=pid_file, log_file=log_file, config_file=config_file)
    reactor.addSystemEventTrigger("before", "shutdown", m.before_shutdown)
    return m

