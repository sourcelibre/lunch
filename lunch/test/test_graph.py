"""
Tests for the oriented ordred graph. (for process dependencies between each other)
"""
from twisted.trial import unittest
from lunch import graph

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
        #print(str(g)) 
        li = g.get_supported_by("a")
        self.failUnlessEqual(li, ["b", "c"])
        # b and c rely on a

    def test_clear(self):
        g = graph.DirectedGraph()
        g.add_node("x")
        g.add_node("y")
        g.add_node("z")
        root = g.get_root()
        li = g.get_supported_by(root)
        self.failUnlessEqual(li, ["x", "y", "z"])
        li2 = g.get_all_nodes()
        self.failUnlessEqual(li2, [root, "x", "y", "z"])
        g.clear()
        li3 = g.get_all_nodes()
        self.failUnlessEqual(li3, [root])
        
    def test_traverse(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        g.add_node("d", ["b"])
        g.add_node("e", ["b"])
        
        li = g.get_supported_by("a")
        self.failUnlessEqual(li, ["b", "c"])
        li = g.get_supported_by("b")
        self.failUnlessEqual(li, ["d", "e"])

    def test_remove_dep(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        
        li = g.get_supported_by("a")
        self.failUnlessEqual(li, ["b"])
        
        g.remove_dependency("b", "a")
        
        li = g.get_supported_by("a")
        self.failUnlessEqual(li, [])

        li = g.get_dependencies("b")
        self.failUnlessEqual(li, [g.get_root()])
        
    def test_detect_circularity(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["b"])
        # root <-- a <-- b <-- c
        if not g.depends_on("c", "a"):
            self.fail("Did not detect dependency.")
    test_detect_circularity.skip = "Not ready yet."
        
