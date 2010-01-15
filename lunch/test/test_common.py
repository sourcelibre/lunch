"""
Tests for lunch Master
"""
from twisted.trial import unittest
from lunch import master

class Test_Master(unittest.TestCase):
    def test_read_config(self):
        pass
    test_read_config.skip = "TODO."

    def test_add_command(self):
        master.add_command(command="xeyes -geometry 100x100")
        if len(master.Master._commands["default"]) != 1:
            self.fail("Did not add command.")
        # empty the commands
        master._commands["default"] = []
    test_add_command.skip = "Too much changes to test it right now."

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
