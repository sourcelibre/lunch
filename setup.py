#!/usr/bin/env python
from distutils.core import setup

__version__ = "0.2.18"

setup(
    name="lunch",
    version=__version__,
    description="The Lunch Distributed Process Launcher",
    author="SAT",
    author_email="alexandre@quessy.net",
    url="https://svn.sat.qc.ca/trac/lunch",
    packages=["lunch"],
    scripts=["scripts/lunch", "scripts/lunch-slave"]
    )

