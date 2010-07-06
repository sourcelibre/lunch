"""
Tests for lunch Master
"""
from twisted.trial import unittest
from twisted.internet import defer
from twisted.python import failure
from twisted.internet import reactor
from lunch import master
from lunch import commands

master.start_stdout_logging()

#TODO: add the path to lunch-slave to $PATH

class Test_Master(unittest.TestCase):
    def test_read_config(self):
        pass
    test_read_config.skip = "TODO."

    def test_add_remove_command(self):
        _deferred = defer.Deferred()
        _master = master.Master()
        
        def _later1():
            # checks the the command has been added
            # removes the command
            if len(_master.get_all_commands()) != 1:
                self.fail("The command did not get added.")
                _deferred.callback(None)
            else:
                _master.remove_command("xeyes")
                print("remove_command")
                reactor.callLater(0.1, _later2)
        
        def _later2():
            print("_later2")
            # checks the the command has been removed
            if len(_master.get_all_commands()) != 0:
                msg = "The command did not get removed"
                print(msg)
                _deferred.errback(failure.Failure(failure.DefaultException(msg)))
                print("failed")
            else:
                print("removing the looping call")
                if _master._looping_call.running:
                    d = _master._looping_call.deferred
                    _master._looping_call.stop() # FIXME
                    d.addCallback(_cb3)
                else:
                    _deferred.callback(None)
        
        def _cb3(result):
            # Called when the looping call has been stopped
            print("quit all slaves")
            for command in _master.get_all_commands():
                command.quit_slave()
            reactor.callLater(0.1, _later4)
        
        def _later4():
            _deferred.callback(None)
            
        
        _master.add_command(commands.Command("xeyes -geometry 100x100", identifier="xeyes"))
        print("added command")
        reactor.callLater(0.1, _later1)
        return _deferred

    test_add_remove_command.skip = "This test is still not working."
        
class Test_Command(unittest.TestCase):
    def test_configure(self):
        pass
    def test_start(self):
        pass
    def test_stop(self):
        pass
    test_configure.skip = "TODO."
    test_start.skip = "TODO."
    test_stop.skip = "TODO."
