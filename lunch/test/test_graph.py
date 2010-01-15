"""
Tests for the oriented ordred graph. (for process dependencies between each other)
"""
from twisted.trial import unittest
from lunch import graph

print(graph.__file__)

class Test_Graph(unittest.TestCase):
    def test_nodes(self):
        g = graph.DirectedGraph()
        root = g.get_root()
        
        g.add_node("a")
        a = g.get_supported_by(root)
        self.failUnlessEqual(a, ["a"])
        # a should depend on root
        
        g.add_node("b", ["a"])
        a2 = g.get_dependencies("b")
        self.failUnlessEqual(a, ["a"])
        # b should depend on a
       
        g.add_node("c", ["a"])
        print(str(g)) 
        li = g.get_supported_by("a")
        self.failUnlessEqual(li, ["b", "c"])
        # b and c rely on a
