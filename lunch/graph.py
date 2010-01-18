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

    Some nodes can have two parents, but orphans are children of the root.
    
    Inspired from networkx.digraph.DiGraph
    """
    ROOT = "__ROOT__" # the root node, to which all depend
    def __init__(self):
        self.deps = [] # dict node: list of [k, []] lists.
        self.deps.append([self.ROOT, []])

    def clear(self):
        """
        Removes all nodes and dependencies, except the root.
        """
        self.deps = [[self.ROOT, []]]
    
    def add_node(self, node, deps=None):
        """
        Adds a node to the graph, pointing to its dependencies. If no dependency is specified, it will point to the root.
        @param node: L{str} or L{str} The node to add.
        @param deps: :{list} of L{str} Its dependencies.
        """
        if node not in self.get_all_nodes():
            self.deps.append([node, []])
        if deps is not None:
            if type(deps) is not list:
                self.add_dependency(node, deps)
            for dep in deps:
                self.add_dependency(node, dep)
        else:
            self.add_dependency(node, self.ROOT)
        
    def add_dependency(self, node_from, node_to):
        """
        Adds a dependency between node_from and node_to.
        See networks.digraph.DiGraph.add_edge(node_from, node_to)
        @param node_from: str
        @param node_to: str
        """
        # makes sure we already have this node
        dependencies = self.get_dependencies(node_from)
        if node_to not in dependencies:
            dependencies.append(node_to)

    def get_dependencies(self, node):
        """
        Return a L{list} of nodes to which a node depends.
        
        @rettype list
        @param node: str
        """
        for k, v in self.deps:
            if k is node:
                return v
        # else:
        raise GraphError("No node %s in graph." % (node))

    def get_all_nodes(self):
        return [k for k, v in self.deps]

    def get_root(self):
        """
        Returns the root of the graph.  
        @rettype: L{str}
        """
        return self.ROOT

    def remove_dependency(self, node_from, node_to):
        """
        If no dependency if left, it will depend on the root.
        """
        # might raise a ValueError
        dependencies = self.get_dependencies(node_from)
        if node_to in dependencies:
            dependencies.remove(node_to) 
            if dependencies == []:
                dependencies.append(self.ROOT)
        else:
            raise GraphError("No dependency %s for node %s.", node_to, node_from)
        
    def remove_node(self, node):
        """
        Removes a node from the graph.
        Removes all the dependencies of other nodes to this one.
        """
        if node in self.get_all_nodes():
            for k, v in self.deps:
                if k is node:
                    self.deps.remove([k, v])
        else:
            raise GraphError("No node %s in graph." % (node))

    def get_supported_by(self, node):
        """
        Returns the list of nodes that are supported by the given one.
        """
        ret = []
        for k, v in self.deps:
            if node in v:
                ret.append(k)
        return ret

    #def depends_on(self, node, searched):
    #    curr = node
    #    while curr is not searched and curr is not self.root:
    #        if curr is searched:
    #            return True
    #        elif curr is self.root:
    #            return False
    #        curr = self.get
    #    return False

    def _traverse(self, node, indent=0):
        """
        Useful for printing an ASCII tree
        Recursive method !
        """
        txt = " " * indent
        txt += " * %s\n" % (node)
        for child in self.get_supported_by(node):
            txt += self._traverse(child, indent + 2)
        return txt
        
    def __str__(self):
        txt = "DirectedGraph:\n"
        txt += str(self.__dict__) + "\n"
        txt += "Graph nodes:\n"
        txt += self._traverse(self.ROOT)
        return txt
