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
        self.assertEqual(a, ["a"])
        # a should depend on root
        
        g.add_node("b", ["a"])
        a2 = g.get_dependencies("b")
        self.assertEqual(a, ["a"])
        # b should depend on a
       
        g.add_node("c", ["a"])
        #print(str(g)) 
        li = g.get_supported_by("a")
        self.assertEqual(li, ["b", "c"])
        # b and c rely on a

    def test_clear(self):
        g = graph.DirectedGraph()
        g.add_node("x")
        g.add_node("y")
        g.add_node("z")
        root = g.get_root()
        li = g.get_supported_by(root)
        self.assertEqual(li, ["x", "y", "z"])
        li2 = g.get_all_nodes()
        self.assertEqual(li2, [root, "x", "y", "z"])
        g.clear()
        li3 = g.get_all_nodes()
        self.assertEqual(li3, [root])
        
    def test_traverse(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        g.add_node("d", ["b"])
        g.add_node("e", ["b"])
        
        li = g.get_supported_by("a")
        self.assertEqual(li, ["b", "c"])
        li = g.get_supported_by("b")
        self.assertEqual(li, ["d", "e"])

    def test_remove_dep(self):
        g = graph.DirectedGraph()
        g.add_node("aaa")
        g.add_node("b", "aaa")
        
        li = g.get_supported_by("aaa")
        self.assertEqual(li, ["b"])
        
        g.remove_dependency("b", "aaa")
        
        li = g.get_supported_by("aaa")
        self.assertEqual(li, [])

        li = g.get_dependencies("b")
        self.assertEqual(li, [g.get_root()])
        
    def test_detect_circularity(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["b"])
        # root <-- a <-- b <-- c
        if not g.depends_on("c", "a"):
            self.fail("Did not detect dependency.")
    #test_detect_circularity.skip = "Not ready yet."
        
    def test_detect_circularity_when_adding(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        # root <-- a <-- b
        try:
            g.add_dependency("a", "b")
        except graph.GraphError as e:
            pass
        else:
            self.fail("Adding dep a->b should have raised an error.")
        
        g.add_node("c", ["b"])
        # root <-- a <-- b <-- c
        
        try:
            g.add_dependency("a", "c")
        except graph.GraphError as e:
            pass
        else:
            self.fail("Adding dep a->c should have raised an error.")
        
    def test_get_all_dependees(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["b"])
        g.add_node("d", ["b"])
        # root <-- a <-- b <-- c,d
        all = g.get_all_dependees("a")
        self.assertEqual(all, ["b", "c", "d"])

class Test_Traversal(unittest.TestCase):
    """
    Many tests using the same tree which contains all the cases.
    """
    def setUp(self):
        self.g = graph.DirectedGraph()
        self.g.add_node("a")
        self.g.add_node("b", ["a"])
        self.g.add_node("c", ["b"])
        self.g.add_node("d", ["b"])
        self.g.add_node("e")
        self.g.add_node("f", ["e"])
        self.g.add_node("g")
        self.g.add_node("h")
        self.g.add_node("j")
        self.g.add_node("i", ['h', 'j'])
        #  a -- b -- c
        #        `-- d
        #  e -- f
        #  g
        #  h -\
        #  j -- i
        
    def test_get_all_dependencies(self):
        li = self.g.get_all_dependencies("d")
        self.assertEqual(li, ["b", "a"])
        
        li = self.g.get_all_dependencies("i")
        self.assertEqual(li, ["h", "j"])
        
        li = self.g.get_all_dependencies("g")
        self.assertEqual(li, [])
        
    def test_get_all_dependees(self):
        li = self.g.get_all_dependees("a")
        self.assertEqual(li, ["b", "c", "d"])
        
        li = self.g.get_all_dependees("e")
        self.assertEqual(li, ["f"])

    def test_iterator(self):
        iterator = graph.iter_from_root_to_leaves(self.g)
        visited = []
        for n in iterator:
            visited.append(n)
        self.assertEqual(visited, [self.g.ROOT, "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])

