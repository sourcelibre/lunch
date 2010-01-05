#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Lunch
# Copyright (C) 2008 Société des arts technologiques (SAT)
# http://www.sat.qc.ca
# All rights reserved.
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Lunch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lunch. If not, see <http://www.gnu.org/licenses/>.

"""
Simply runs a process on the local machine.
Allows specifying environment variables.
"""
# TODO: use log instead of print
# TODO: create config dir/file if not found
from lunch import common

def run_slave(command_str, vars={}, log_file_name=None):
    """
    Runs a slave. (a command (on remote host) to start a single process)
    
    Alias to run_command, but called from 
    either the master on the local host of a slave "lunch" software on a remote host.
    """
    return common.run_command(command_str, vars, True, log_file_name) # Dies on ctrl-C
