"""
Tests for lunch Master
"""
from twisted.trial import unittest
from twisted.internet import defer
from twisted.python import failure
from twisted.internet import reactor
from lunch import master
from lunch import commands

master.start_stdout_logging("warning") # "debug"
from lunch import logger
log = logger.start(name="test")

#TODO: add the path to lunch-slave to $PATH

class Test_Master(unittest.TestCase):
    timeout = 4.0 # so that we don't wait in case of a problem
    def test_read_config(self):
        pass
    test_read_config.skip = "TODO."

    def test_add_remove_command(self):
        COMMAND_IDENTIFER = "test"
        COMMAND_LINE = "man man"
        _deferred = defer.Deferred()
        _master = master.Master()
        self.the_command = None
        
        def _later1():
            # checks the the command has been added
            # removes the command
            self.the_command = _master.get_command(COMMAND_IDENTIFER)
            log.info("Set self.the_command to %s" % (self.the_command))
            _master.remove_command(COMMAND_IDENTIFER)
            log.info("remove_command")
            reactor.callLater(0.1, _later2)
        
        def _later2():
            log.info("_later2")
            # checks the the command has been removed
            if len(_master.get_all_commands()) != 0:
                msg = "The command did not get removed"
                log.info(msg)
                _deferred.errback(failure.Failure(failure.DefaultException(msg)))
                log.info("failed")
            else:
                log.info("removing the looping call")
                if _master._looping_call.running:
                    d = _master._looping_call.deferred
                    _master._looping_call.stop() # FIXME
                    d.addCallback(_cb3)
                else:
                    _deferred.callback(None)
        
        def _cb3(result):
            # Called when the looping call has been stopped
            log.info("quit all slaves")
            for command in _master.get_all_commands():
                command.quit_slave()
            self.the_command.quit_slave()
            reactor.callLater(0.1, _later4)
        
        def _later4():
            _deferred.callback(None)
            
        
        _master.add_command(commands.Command(COMMAND_LINE, identifier=COMMAND_IDENTIFER))
        log.info("added command $ %s" % (COMMAND_LINE))
        reactor.callLater(0.1, _later1)
        return _deferred

    #test_add_remove_command.skip = "This test is still not working."
        
#class Test_Command(unittest.TestCase):
#    def test_configure(self):
#        pass
#    def test_start(self):
#        pass
#    def test_stop(self):
#        pass
#    test_configure.skip = "TODO."
#    test_start.skip = "TODO."
#    test_stop.skip = "TODO."
