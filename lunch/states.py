#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Lunch
# Copyright (C) 2009 Société des arts technologiques (SAT)
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
# along with Lunch.  If not, see <http://www.gnu.org/licenses/>.
"""
Constants for the states of the slave processes
"""
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING"
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED"
STATE_NOSLAVE = "NOSLAVE" # for master only
# these two are not states per se, but returned by the get_state_info() method
INFO_DONE = "DONE"
INFO_FAILED = "FAILED"
INFO_TODO = "TODO"
INFO_GAVEUP = "GAVE UP"
