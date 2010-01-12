#!/usr/bin/env python
from distutils.core import setup

setup(
    name="lunch",
    version="0.2.0",
    description="The Lunch Distributed Process Manager",
    author="SAT",
    author_email="alexandre@quessy.net",
    url="https://svn.sat.qc.ca/trac/lunch",
    packages=["lunch"],
    scripts=["scripts/lunch", "scripts/lunch-0.1", "scripts/lunch-slave"]
    )

