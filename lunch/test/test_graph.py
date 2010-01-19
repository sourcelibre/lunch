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
        g.add_node("aaa")
        g.add_node("b", "aaa")
        
        li = g.get_supported_by("aaa")
        self.failUnlessEqual(li, ["b"])
        
        g.remove_dependency("b", "aaa")
        
        li = g.get_supported_by("aaa")
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
    #test_detect_circularity.skip = "Not ready yet."
        
    def test_detect_circularity_when_adding(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        # root <-- a <-- b
        try:
            g.add_dependency("a", "b")
        except graph.GraphError, e:
            pass
        else:
            self.fail("Adding dep a->b should have raised an error.")
        
        g.add_node("c", ["b"])
        # root <-- a <-- b <-- c
        
        try:
            g.add_dependency("a", "c")
        except graph.GraphError, e:
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
        self.failUnlessEqual(all, ["b", "c", "d"])

    def test_no_recursion(self):
        g = graph.DirectedGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["b"])
        g.add_node("d", ["b"])
        g.add_node("e")
        g.add_node("f", ["e"])
        g.add_node("g")
        g.add_node("h")
        g.add_node("j")
        g.add_node("i", ['h', 'j'])
        #  a -- b -- c
        #        `-- d
        #  e -- f
        #  g
        #  h -.
        #  i -- j
        current = g.ROOT
        visited = [] # list of visited nodes.
        stack = [] # stack of iterators
        while True:
            if current not in visited:
                visited.append(current)
                # DO YOUR STUFF HERE
                children = g.get_supported_by(current)
                stack.append(iter(children))
            try:
                current = stack[-1].next()
            except StopIteration:
                stack.pop()
            except IndexError:
                break
        
        self.failUnlessEqual(visited, [g.ROOT, "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])
