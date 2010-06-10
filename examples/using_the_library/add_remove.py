#!/usr/bin/env python
"""
This example demonstrate how to use lunch master as a library.
"""
from twisted.internet import reactor
from twisted.internet import task
from lunch import commands
from lunch import master

has_them = True

if __name__ == "__main__":
    unique_master_id = "example"
    log_dir = master.DEFAULT_LOG_DIR
    pid_file = master.write_master_pid_file(identifier=unique_master_id, directory=log_dir)
    # XXX add_command here
    m = master.Master(log_dir=log_dir, pid_file=pid_file)
    m.add_command(commands.Command("xeyes", identifier="xeyes"))
    m.add_command(commands.Command("xlogo", identifier="xlogo"))
    m.add_command(commands.Command("xcalc", identifier="xcalc"))
    def _test():
        global has_them
        if not has_them:
            print("Adding them again!")
            m.add_command(commands.Command("xeyes", identifier="xeyes"))
            m.add_command(commands.Command("xlogo", identifier="xlogo"))
            m.add_command(commands.Command("xcalc", identifier="xcalc"))
            has_them = True
        else:
            print("Removing them.")
            m.remove_command("xeyes")
            m.remove_command("xlogo")
            m.remove_command("xcalc")
            has_them = False
            
    looping_call = task.LoopingCall(_test)
    looping_call.start(3.0, False) 
    reactor.run()
