#!/usr/bin/env python
"""
setup.py for Lunch
Also sets up the man pages.

To update the version number : 
vim -o lunch/runner.py scripts/lunch-slave setup.py lunch/gui.py
"""
from setuptools import setup
import subprocess
import sys
import lunch


setup(
    name="lunch",
    version=lunch.__version__,
    description="The Lunch Distributed Process Launcher",
    author="SAT",
    author_email="alexandre@quessy.net",
    url="https://svn.sat.qc.ca/trac/lunch",
    packages=["lunch"],
    scripts=["scripts/lunch", "scripts/lunch-slave"]
    )

if sys.argv[1] == "build":
    commands = [
        #'convert -geometry 48x48 -background none lunch.svg lunch.png',
        'help2man --no-info --include=man_lunch.txt --name="The Lunch Distributed Process Manager" ./scripts/lunch --output=lunch.1',
        'help2man --no-info --include=man_lunch-slave.txt --name="Lunch Slave" ./scripts/lunch-slave --output=lunch-slave.1'
        ]
    for c in commands:
        print("$ %s" % (c))
        retcode = subprocess.call(c, shell=True)
        print("The help2man command returned %s" % (retcode))

