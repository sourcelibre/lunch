"""
Tests for lunch Master
"""
from twisted.trial import unittest

class Test_Master(unittest.TestCase):
    def test_read_config(self):
        pass
    def test_add_command(self):
        pass
    def test_remove_command(self):
        pass
    test_read_config.skip = "TODO."
    test_add_command.skip = "TODO."
    test_remove_command.skip = "TODO."

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
