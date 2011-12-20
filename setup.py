#!/usr/bin/env python
"""
setup.py for Lunch
Also sets up the man pages.

To update the version number : 
vim -o scripts/lunch-slave lunch/__init__.py
"""
from setuptools import setup
import subprocess
import sys
import os
import lunch

setup(
    name="lunch",
    version=lunch.__version__,
    description="The Lunch Distributed Process Launcher",
    author="SAT",
    author_email="alexandre@quessy.net",
    url="http://code.sat.qc.ca/trac/lunch",
    packages=["lunch"],
    scripts=["scripts/lunch", "scripts/lunch-slave"]
    )

# build man pages
if sys.argv[1] == "build":
    commands = [
        'help2man --no-info --include=man_lunch.txt --name="Distributed process launcher" ./scripts/lunch --output=lunch.1',
        'help2man --no-info --include=man_lunch-slave.txt --name="Process launcher" ./scripts/lunch-slave --output=lunch-slave.1'
        ]
    for c in commands:
        print("$ %s" % (c))
        retcode = subprocess.call(c, shell=True)
        print("The help2man command returned %s" % (retcode))

# Finally, we create logging directories if they don't exist already
if sys.argv[1] == "install":
    log_dir = "/var/log/lunch"
    pid_dir = "/var/run/lunch"

    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            os.chmod(log_dir, 01777) # T flag: users can create, write into, but not delete files. see man(1) chmod
        except OSError, e:
            print(e)
            sys.exit(1) # fail
    if not os.path.exists(pid_dir):
        try:
            os.makedirs(pid_dir)
            os.chmod(pid_dir, 01777)
        except OSError, e:
            print(e)
            sys.exit(1) # fail

