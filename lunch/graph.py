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
Module for handling dependencies between processes in a launching sequence.

Example : sc needs jackd. We would start jackd first, then sc. If jackd crashes, 
we stop both, start jackd again, and then sc.
"""

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
        Raises a GraphError if creating circular dependencies.
        """
        if node not in self.get_all_nodes():
            self.deps.append([node, []])
        if deps is not None:
            if type(deps) is list:
                self.add_dependencies(node, deps)
            else:
                self.add_dependency(node, deps)
        else:
            self.add_dependency(node, self.ROOT)

    def add_dependencies(self, node_from, nodes_to):
        for d in nodes_to:
            self.add_dependency(node_from, d)
        
    def add_dependency(self, node_from, node_to):
        """
        Adds a dependency between node_from and node_to.
        See networks.digraph.DiGraph.add_edge(node_from, node_to)
        @param node_from: str
        @param node_to: str
        """
        # makes sure we don't already have this node
        dependencies = self.get_dependencies(node_from)
        if node_to not in dependencies:
            # prevent from circular dependencies
            if self.depends_on(node_to, node_from):
                raise GraphError("Circular dependency detected. A node cannot depend on itself.")
            else:
                dependencies.append(node_to)
        elif node_to not in self.deps:
            raise GraphError("The is no %s node in the dependencies graph." % (node_to))

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

    def get_supported_by(self, node=None):
        """
        Returns the list of nodes that are directly supported by the given one.
        @param node: str or None. If None, will return the nodes supported by the root.
        """
        if node is None:
            node = self.ROOT
        ret = []
        for k, v in self.deps:
            if node in v:
                ret.append(k)
        return ret

    def get_all_dependees(self, node=None):
        """
        Returns the list of all the nodes that are supported by the given one, recursively !
        @param node: str or None. If None, will return the nodes supported by the root.
        """
        if node is None:
            node = self.ROOT
        ret = []
        for k, v in self.deps:
            if node in v:
                ret.append(k)
                ret.extend(self.get_all_dependees(k))
        return ret
        
    def get_all_dependencies(self, node):
        """
        Returns the list of all the nodes that are supported by the given one, recursively !
        @param node: str 
        """
        ret = []
        for k in self.get_dependencies(node):
            if k != self.ROOT:
                ret.append(k)
                ret.extend(self.get_all_dependencies(k))
        return ret

    def depends_on(self, node, searched):
        """
        Checks if a node depends on another.
        Recursive method. (might be limited by sys.getrecursionlimit())
        """
        if node is self.ROOT:
            return False
        #elif node is searched:
        #    raise GraphError("Both given nodes are the same.")
        else:
            li = self.get_dependencies(node)
            for i in li:
                if i is searched:
                    return True
                else:
                    if i is not self.ROOT:
                        res = self.depends_on(i, searched)
                        if res:
                            return True
            # if not found
            return False

    def _traverse(self, node, indent=0):
        """
        Useful for printing an ASCII tree
        Recursive method ! (might be limited by sys.getrecursionlimit())
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

def iter_from_root_to_leaves(graph):
    """
    Generator function to iterate through all nodes of a graph, 
    from the root to its leaves, prioritizing each next node on the same
    level by the order in which it was added.
    @return: An iterator.
    """
    current = graph.ROOT
    visited = [] # list of visited nodes.
    stack = [] # stack of iterators
    while True:
        if current not in visited:
            visited.append(current)
            # DO YOUR STUFF HERE
            yield current
            children = graph.get_supported_by(current)
            stack.append(iter(children))
        try:
            current = stack[-1].next()
        except StopIteration:
            stack.pop()
        except IndexError:
            break
