#!/usr/bin/env python
"""
This example demonstrate how to use lunch master as a library.
"""
from twisted.internet import gtk2reactor
gtk2reactor.install() # has to be done before importing reactor
from twisted.internet import reactor
from twisted.internet import task
from lunch import commands
from lunch import master
from lunch import gui
import random

if __name__ == "__main__":
    unique_master_id = "example"
    log_dir = master.get_default_log_dir_full_path()
    master.start_stdout_logging(log_level="info")
    pid_file = master.write_master_pid_file(identifier=unique_master_id, directory=log_dir)
    # XXX add_command here
    m = master.Master(log_dir=log_dir, pid_file=pid_file)
    m.add_command(commands.Command("xeyes", identifier="xeyes"))
    m.add_command(commands.Command("xlogo", identifier="xlogo"))
    m.add_command(commands.Command("xcalc", identifier="xcalc"))
    def _test():
        print("Adding one more!")
        m.add_command(commands.Command("xeyes -geometry %dx%d" % (random.randint(20, 500), random.randint(20, 500))))
    looping_call = task.LoopingCall(_test)
    looping_call.start(1.0, False) 
    gui.start_gui(m)
    reactor.run()
