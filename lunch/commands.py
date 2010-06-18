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
Commands and slaves that run them.
Author: Alexandre Quessy <alexandre@quessy.net>
"""
import os
import stat
import time
import logging
import warnings

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

from lunch import sig
from lunch import graph
from lunch.states import *
from lunch import logger

log = logger.start(name='commands')

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
        return failure.Failure(RuntimeError(msg))
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
                log.debug("stderr: " + line + "\n")

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
        log.info("Slave %s process ended with %s." % (self.command.identifier, exit_code))
        self.command._on_process_ended(reason.value.exitCode)
    
    def inConnectionLost(self):
        pass #log.msg("Slave stdin has closed.")

    def outConnectionLost(self):
        pass #log.msg("Slave stdout has closed.")
    
    def errConnectionLost(self):
        pass #log.msg("Slave stderr has closed.")

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
        log.info("process has exited : %s." % (str(exit_code)))
    
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
    
    def __init__(self, command=None, identifier=None, env=None, user=None, host=None, order=None, sleep_after=0.25, respawn=True, minimum_lifetime_to_respawn=0.5, log_dir=None, depends=None, verbose=False, try_again_delay=0.25, give_up_after=0):
        """
        @param command: Shell string. The first item is the name of the name of the executable.
        @param depends: Commands to which this command depends on. List of strings.
        @param env: dict with environment variables to set for the process to run.
        @param host: Host name or IP address, if spawned over SSH.
        @param identifier: Any string. Used as a file name, so avoid spaces and exotic characters.
        @param log_dir: Full path to the directory to save log files in.
        @param minimum_lifetime_to_respawn: Minimum time a process must have lasted to be respawned.
        @param respawn: Set to False if this is a command that must be ran only once.
        @param sleep_after: How long to wait before launching next command after this one.
        @param user: User name, if spawned over SSH.
        @param verbose: Prints more information if set to True.
        @type command: str
        @type depends: list
        @type env: dict
        @type host: str
        @type identifier: str
        @type log_dir: str
        @type minimum_lifetime_to_respawn: float
        @type respawn: bool
        @type sleep_after: float
        @type user: str
        @type verbose: bool
        """
        #TODO:
        #@param try_again_delay: Time to wait before trying again if it crashes at startup.
        #@type try_again_delay: C{float}
        #@param give_up_after: How many times to try again before giving up.
        #@type give_up_after: C{int}
        self.command = command
        self.identifier = identifier
        self.env = {}
        if env is not None:
            self.env.update(env)
        self.user = user
        self.host = host
        self.order = order
        self.sleep_after = sleep_after
        self.respawn = respawn
        self.enabled = True 
        self.to_be_deleted = False
        self.depends = depends
        self.how_many_times_run = 0
        self.how_many_times_tried = 0
        self.verbose = verbose
        self.retval = 0
        self.gave_up = False
        self.try_again_delay = try_again_delay
        self._current_try_again_delay = try_again_delay # doubles up each time we try
        self._next_try_time = 0
        self._previous_launching_time = 0
        self.give_up_after = give_up_after # 0 means infinity of times
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
            raise RuntimeError("You must provide a command to be run.")
        log.info("Creating command %s ($ %s) on %s@%s" % (self.identifier, self.command, self.user, self.host))
            #self.send_stop()
        self._process_protocol = None
        self._process_transport = None
        # Some attributes might be changed by the master, namely identifier and host.
        # That's why we sait until start() is called to initiate the slave_logger.
        self.slave_logger = None

    def is_ready_to_be_started(self):
        # self.enabled
        ret = self._next_try_time <= time.time()
        return ret
    
    def _start_logger(self):
        """
        Creates a log file for the slave's stdout.
        """
        if self.slave_logger is None:
            # the slave log file
            slave_log_file = "slave-%s.log" % (self.identifier)
            if not os.path.exists(self.slave_log_dir):
                try:
                    os.makedirs(self.slave_log_dir)
                except OSError, e:
                    raise RuntimeError("You need to be able to write in the current working directory in order to write log files. %s" % (e))
            self.slave_logger = logfile.LogFile(slave_log_file, self.slave_log_dir)
    
    def start(self):
        """
        Starts the slave Lunch and its child if not started. If started, starts its child.
        """
        self.enabled = True
        self.gave_up = False
        if self.how_many_times_tried == 0:
            self._current_try_again_delay = self.try_again_delay
        self.how_many_times_tried += 1
        self._start_logger()
        if self.child_state == STATE_RUNNING:
            self.log("%s: Child is already running." % (self.identifier))
            return
        if self.slave_state == STATE_RUNNING and self.child_state == STATE_STOPPED:
            self.send_all_startup_commands()
        elif self.child_state in [STATE_STOPPING, STATE_STARTING]:
            self.log("Cannot start child %s that is %s." % (self.identifier, self.child_state))
        else:
            if self.slave_state in [STATE_STARTING, STATE_STOPPING]:
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
                    raise RuntimeError("Could not find path of executable %s." % (_command[0]))
                log.info("%s: $ %s" % (self.identifier, " ".join(_command)))
                self._process_protocol = SlaveProcessProtocol(self)
                #try:
                proc_path = _command[0]
                args = _command
                environ = {}
                environ.update(os.environ) # passing the whole env (for SSH keys and more)
                self.set_slave_state(STATE_STARTING)
                self.log("Starting slave: %s" % (self.identifier))
                self._previous_launching_time = time.time()
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
        self.log("%s: $ %s" % (self.identifier, self.command), logging.INFO)
        
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
        if self.verbose:
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
            self.log('IndexError From slave %s: %s' % (self.identifier, line), logging.ERROR)
        else:
            try:
                if words[1] == "password:":
                    self.log(line, logging.ERROR)
                    self.log("SSH ERROR: Trying to connect using SSH, but the SSH server is asking for a password.", logging.ERROR)
                    return
            except IndexError:
                pass
            # Dispatch the command to the appropriate method.  Note that all you
            # need to do to implement a new command is add another do_* method.
            if key in ["do", "env", "run", "logdir", "stop"]: # FIXME: receiving in stdin what we send to stdin slave !!!
                pass #warnings.warn("We receive from the slave's stdout what we send to its stdin !")
            else:
                try:
                    method = getattr(self, 'recv_' + key)
                except AttributeError, e:
                    self.log('AtributeError: From slave %s: %s' % (self.identifier, line), logging.ERROR)
                    #self.log(line)
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
    
    def recv_retval(self, mess):
        """
        Callback for the "retval" message from the slave.
        """
        self.log("%s->Master: retval %s" % (self.identifier, mess))
        words = mess.split(" ")
        self.retval = int(words[0])
        self.log("%s: Return value of child is %s" % (self.identifier, self.retval), logging.INFO)
    
    def recv_log(self, mess):
        """
        Callback for the "log" message from the slave.
        """
        self.log("%s->Master: log %s" % (self.identifier, mess))

    def recv_error(self, mess):
        """
        Callback for the "error" message from the slave.
        """
        self.log("%s->Master: %s" % (self.identifier, mess), logging.ERROR)
    
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
    
    def get_state_info(self):
        """
        Returns a high-level comprehensive state for the user to see in the GUI.
        """
        #log.debug("gave up: %s" % (self.gave_up))
        if self.child_state == STATE_STOPPED:
            if self.how_many_times_run == 0:
                return INFO_TODO
            elif self.gave_up:
                return INFO_GAVEUP
            elif not self.respawn:
                return INFO_DONE
            elif not self.enabled:
                return STATE_STOPPED
            elif self.retval != 0:
                return INFO_FAILED
            else:
                return STATE_STOPPED # INFO_FAILED?
        else:
            return self.child_state
    
    def _give_up_if_we_should(self):
        """
        Check if we should give up and give up if so.
        """
        # double the time to wait before trying again.
        # self.wait_before_trying_again -- this one never changes
        # self._wait_before_trying_again_next_time -- this one is doubled each time.
        if self.give_up_after != 0 and self.how_many_times_tried >= self.give_up_after:
            self.gave_up = True
            self.enabled = False
            log.info("Gave up restarting command %s" % (self.identifier))
        else:
            self._next_try_time = time.time() + self._current_try_again_delay
            log.info("%s: Will wait %f seconds before trying again." % (self.identifier, self._current_try_again_delay))
            self._current_try_again_delay *= 2
            self.how_many_times_tried += 1

    def recv_state(self, mess):
        """
        Callback for the "state" message from the child.
        Received child state.
        """
        words = mess.split(" ")
        previous_state = self.child_state
        new_state = words[0]
        #print("%s's child state: %s" % (self.identifier, new_state))
        self.log("%s->Master: child STATE is %s" % (self.identifier, new_state))
        if new_state == STATE_STOPPED and self.enabled and self.respawn:
            child_running_time = float(words[1])
            if child_running_time < self.minimum_lifetime_to_respawn:
                self.log("Child running time of %s has been shorter than its minimum of %s." % (child_running_time, self.minimum_lifetime_to_respawn))
                self._give_up_if_we_should()
            #else:
            #    self.send_all_startup_commands()
        elif new_state == STATE_RUNNING:
            self.log("Child %s is running." % (self.identifier))
        self.set_child_state(new_state) # IMPORTANT !

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

    def reset(self):
        """
        Do not give up anymore and reset the trials thing.
        """
        self.how_many_times_tried += 1
        self.gave_up = False
        self._next_try_time = 0
        self._current_try_again_delay = self.try_again_delay
    
    def stop(self):
        """
        Tells the slave to stop its child.
        """
        self.reset()
        self.enabled = False
        if self.child_state in [STATE_RUNNING, STATE_STARTING]:
            self.log('%s: stop' % (self.identifier), logging.INFO)
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
        log_number_to_name = {
            logging.DEBUG: 'debug',
            logging.INFO: 'info',
            logging.WARNING: 'warning',
            logging.ERROR: 'error',
            logging.CRITICAL: 'critical',
            }
        if level == logging.DEBUG:
            log.debug(msg)
        elif level == logging.INFO:
            log.info(msg)
        elif level == logging.WARNING:
            log.warning(msg)
        elif level == logging.ERROR:
            log.error(msg)
        elif level == logging.CRITICAL:
            log.critical(msg)

        #log.msg(msg, logLevel=level)

    def set_slave_state(self, new_state):
        msg = "Slave %s is %s." % (self.identifier, new_state)
        self.log(msg)
        if self.slave_state != new_state:
            self.slave_state = new_state
            self.slave_state_changed_signal(self.slave_state)

    def __str__(self):
        return "%s" % (self.identifier)
    
