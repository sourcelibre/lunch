#!/usr/bin/env python
"""
This example demonstrate how to use lunch master as a library.
"""
from twisted.internet import reactor
from lunch import master

if __name__ == "__main__":
    unique_master_id = "example"
    log_dir = master.DEFAULT_LOG_DIR
    pid_file = master.write_master_pid_file(identifier=unique_master_id, directory=log_dir)
    # XXX add_command here
    master.add_command("xeyes")
    master.add_command("xlogo")
    master.add_command("xcalc")
    m = master.Master(log_dir=log_dir, pid_file=pid_file)
    reactor.run()
