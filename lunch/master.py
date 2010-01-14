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
import warnings

from twisted.internet import protocol
from twisted.internet import error
from twisted.internet import reactor
from twisted.internet import defer
from twisted.python import procutils
from twisted.python import log
from twisted.python import logfile

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
        self.slave_state_changed_signal = sig.Signal()
        self.child_state_changed_signal = sig.Signal()
        if command is None:
            raise MasterError("You must provide a command to be run.")
            #self.send_stop()
        self._process_protocol = None
        self._process_transport = None
        
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
        Starts the slave Lunch
        """
        if self.slave_state in [STATE_RUNNING, STATE_STARTING, STATE_STOPPING]:
            self.log("Cannot start slave %s that is %s." % (self.identifier, self.slave_state))
            return # XXX
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
        """
        Here, we send all the commands to the slave.
        """
        if self.slave_state == STATE_STARTING:
            self.set_slave_state(STATE_RUNNING)
        else:
            msg = "Connection made with slave %s, even if not expecting it." % (self.identifier)
            self.log(msg, logging.ERROR)

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
    
    def send_logdir(self):
        self.send_message("logdir", self.child_log_dir)

    def send_message(self, key, data=""):
        """
        Sends a command to the slave.
        @param key: string
        @param data: string
        """
        msg = "%s %s\n" % (key, data)
        self.log("Master sends to slave: " + msg.strip())
        self._process_transport.write(msg)
    
    def __del__(self):
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
            self.log("Index error parsing message from slave. %s" % (e), logging.ERROR)
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
                    self.log('No callback for "%s" got from slave %s. Got: %s' % (key, self.identifier, line), logging.ERROR)
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
        self.log("%8s: %s" % (self.identifier, mess))

    def recv_error(self, mess):
        """
        Callback for the "error" message from the slave.
        """
        self.log("%8s: %s" % (self.identifier, mess), logging.ERROR)
    
    def recv_pong(self, mess):
        """
        Callback for the "pong" message from the slave.
        """
        pass #self.log("pong from %s" % (self.identifier))

    def recv_bye(self, mess):
        """
        Callback for the "bye" message from the slave.
        """
        self.log("%8s: %s" % (self.identifier, "QUITTING !!!"), logging.ERROR)

    def recv_state(self, mess):
        """
        Callback for the "state" message from the slave.
        Received child state.
        """
        words = mess.split(" ")
        previous_state = self.child_state
        new_state = words[0]
        self.set_child_state(new_state) # IMPORTANT !
        self.log("Child %8s: %s" % (self.identifier, "state: %s" % (new_state)))
        if new_state == STATE_STOPPED and self.enabled and self.respawn:
            child_running_time = float(words[1])
            if child_running_time < self.minimum_lifetime_to_respawn:
                self.log("Not respawning child since its running time of %s has been shorter than the minimum of %s." % (child_running_time, self.minimum_lifetime_to_respawn))
            else:
                self.send_all_startup_commands()
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
            self.child_state = new_state
            self.child_state_changed_signal(self.child_state)

    def stop(self):
        """
        Tells the slave to stop its child.
        """
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
                    self.send_stop()
                elif self.child_state == STATE_STOPPED:
                    self._process_transport.signalProcess(15) # signal.SIGTERM
                self.set_slave_state(STATE_STOPPING)
                self.log('Master will stop slave %s.' % (self.identifier))
            elif self.slave_state == STATE_STOPPING:
                # second time this is called, force-quitting:
                self.log("kill -9 Slave %s" % (self.identifier))
                self._process_transport.signalProcess(9) # signal.SIGKILL

    def _on_process_ended(self, exit_code):
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
        if self.respawn and self.enabled:
            self.log("Restarting the slave %s." % (self.identifier), logging.INFO)
            self.start()
        
    def log(self, msg, level=logging.DEBUG):
        """Logs both to the slave's log file, and to the main app log. """
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
    
def add_command(command=None, title=None, env=None, user=None, host=None, group=None, order=100, sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None, sleep=None, priority=None):
    """
    This is the only function that users use from within the configuration file.
    It adds a Command instance to the list of commands to run. 
    
    Default priority is 100. The lowest the earliest.
    """
    # TODO: remove priority and sleep kwargs in a future version
    #FIXME: Changed back identifier to title.
    #global _commands
    #log.msg("DEBUG: adding %s %s %s %s %s %s %s %s to group %s" % (command, env, host, user, order, sleep_after, respawn, log_dir, group)) # EDIT ME

    log.msg("Adding %s (%s) %s@%s to group %s" % (title, command, user, host, group), logging.INFO)
    if group is None:
        group = "default" # default group is "default"
    if not Master.groups.has_key(group):
        log.msg("Adding group %s" % (group))
        Master.groups[group] = Group(group)
    if sleep is not None:
        warnings.warn("The sleep keyword argument has been renamed to sleep_after.", DeprecationWarning)
        sleep_after = sleep
    if priority is not None:
        warnings.warn("The priority keyword argument does not exist anymore. Only the order in which add_command calls are done is considered.", DeprecationWarning)
    # check if addr is local, set it to none if so.
    if host in Master.local_addresses:
        log.msg("Filtering out host %s since it is in list of local addresses." % (host))
        _host = None    
    else:
        _host = host
    # set default names if they are none:
    if title is None:
        title = "default-%d" % (Master.i)
        Master.i += 1
    Master.groups[group].commands.append(Command(command=command, env=env, host=_host, user=user, order=order, sleep_after=sleep_after, respawn=respawn, log_dir=log_dir, identifier=title)) # EDIT ME
    
class Group(object):
    """
    A group contains commands.
    """
    def __init__(self, name):
        #self.state = STATE_STOPPED
        self.commands = []
        self.name = name
    
    def __str__(self):
        txt = "Group %s: " % (self.name)
        for c in self.commands:
            txt += str(self.commands) + " "
        return txt

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
    The master manages slaves, grouped in groups.
    """
    # static class variable :
    # All the commands are stored in groups of commands :
    groups = {"default":Group("default")}
    # For counting default names if they are none :
    i = 0
    # IP to which not use SSH with :
    local_addresses = [
        "localhost",
        "127.0.0.1"
        ] # TODO: check IP of each network interface.
    
    def __init__(self):
        reactor.callLater(0, self.start_all)

    def start_all(self, group_name=None):
        """
        Starts all slaves in a group, iterating asynchronously.
        If group is None, iterates over all commands slaves.
        """
        if group_name is None:
            groups = Master.groups.keys()
        else:
            groups = group_name
        iter_groups = iter(groups)
        iter_commands = iter([]) # at first empty
        reactor.callLater(0, self._start_next, iter_groups, iter_commands)

    def _start_next(self, iter_groups, iter_commands, group_name=None):
        # define asynchronous iterating function
        c = None
        try:
            c = iter_commands.next()
        except StopIteration:
            if group_name is not None:
                log.msg("Done iterating through commands of group %s." % (group_name))
            try:
                group_name = iter_groups.next()
            except StopIteration:
                log.msg("Done iterating through groups.")
                return
            else:
                log.msg("Iterating through commands of group %s." % (group_name))
                g = Master.groups[group_name]
                iter_commands = iter(g.commands)
                log.msg("Next command in group %s : %s" % (g.name, g.commands))
                try:
                    c = iter_commands.next()
                except StopIteration:
                    if group_name is not None:
                        log.msg("Done iterating through commands in group %s." % (group_name))
                else:
                    log.msg("Got command %s" % (c.identifier))
        sleep = 0
        if c is not None:
            log.msg("Starting command %s" % (c.identifier))
            c.start()
            sleep = c.sleep_after
        reactor.callLater(sleep, self._start_next, iter_groups, iter_commands, group_name)
    
    def _get_all(self, group_name=None):
        """
        Returns all commands in a group, or in every groups. (all commands)
        If group_name is None, returns commands from all groups.
        """
        if group_name is None: # returns commands from all groups
            ret = []
            for g in self.groups.itervalues():
                ret.extend(g.commands)
        else:
            ret = self.groups[group_name].commands
        return ret
    
    def stop_all(self, group_name=None):
        """
        Stops all commands
        """
        commands = self._get_all(group_name)
        for c in commands:
            c.enabled = False
            c.stop()
            # TODO: callLaters...

    def restart_all(self, group_name=None):
        self.stop_all(group_name)
        commands = self._get_all(group_name)
        for c in commands:
            s.enabled = False
            c.stop()
        reactor.callLater(0.1, _start_if_all_stopped, group_name)

    def _start_if_all_stopped(self, group_name=None):
        """
        Checks in loop if all got stopped, if so, start them over.
        """
        commands = self._get_all(group_name)
        ready_to_restart = True
        for c in commands:
            if c.child_state != STATE_STOPPED:
                ready_to_restart = False
        if ready_to_restart:
            self.start_all(group_name)
        else:
            reactor.callLater(0.1, _start_if_all_stopped, group_name)

    def quit_master(self):
        """
        Stops all slaves and quits the application.
        """
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
                log.msg("Stopping Lunch.")
                deferred.callback(True) # stops reactor
        
        _later(self, _shutdown_data)
        return deferred

def write_master_pid_file(config_file_name="lunchrc", directory="/tmp"):
    """
    Writes master's PID in a file.
    """
    config_file_name = os.path.split(config_file_name)[1] # remove dir name
    # TODO: remote non-alnum chars in config_file_name
    config_file_name = config_file_name.replace(".", "") # getting rid of the dot in file name
    file_name = "lunch-master-%s.pid" % (config_file_name)
    if not os.path.exists(directory):
        os.makedirs(directory)
    pid_file = os.path.join(directory, file_name)
    f = open(pid_file, 'w')
    f.write(str(os.getpid()))
    f.close()

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
    write_master_pid_file(config_file)
    start_logging()
    log.msg("Using lunch master module %s" % (__file__))
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

