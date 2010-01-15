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

class GraphError(Exception):
    """
    Any error thrown by handling graph nodes.
    """
    pass

class DirectedGraph(object):
    """
    Directed Graph with ordered edges between nodes.
    Useful for handling dependencies between processes.

    Some nodes can have two parents.
    """
    ROOT = "__ROOT__" # the root node, to which all depend
    def __init__(self):
        self.deps = {} # dict node: list of nodes
        self.add_node(self.ROOT)
    
    def add_node(self, node, deps=None):
        """
        @param node: str
        @param deps: list of str.
        """
        if node not in self.deps:
            self.deps[node] = []
        if deps is not None:
            self.add_dep(node, self.ROOT)
        else:
            for dep in deps:
                self.add_dep(node, dep)
                # every node depends on the ROOT node...

    def add_dep(self, node_from, node_to):
        """
        Adds a dependency between node_from and node_to.
        See networks.digraph.DiGraph.add_edge(node_from, node_to)
        @param node_from: str
        @param node_to: str
        """
        # makes sure we already have this node
        self.deps[node_from].append(node_to)

    def get_deps(self, node):
        """
        Return nodes to which a node depends.
        
        See networks.digraph.DiGraph.successors(node)
        @rettype list
        @param node: str
        """
        return self.deps[node]

    def get_root(self):
        return self.ROOT

    def remove_dep(self, node_from, node_to):
        self.deps[node_from].remove(node_to)
        
    def remove_node(self, node):
        del self.deps[node] 
        for deps in self.deps.itervalues():
            if node in deps:
                deps.remove(node)
            

    def get_dependees(self, node):
        ret = []
        for k, v in self.deps.iteritems():
            if node in v:
                ret.append(k)
        return ret
