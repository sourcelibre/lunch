#!/usr/bin/env python
# example treemodelsort.py
if __name__ == "__main__":
    from twisted.internet import gtk2reactor
    gtk2reactor.install() # has to be done before importing reactor
from twisted.internet import reactor
import gtk
import random

class TreeModelSortExample:

    # close the window and quit
    def delete_event(self, widget, event, data=None):
        #gtk.main_quit()
        reactor.stop()
        return False

    def add_row(self, b):
        rand = self.rand
        # add a row of random ints
        i0 = self.model_sort.get_model().append([
            self.rand.randint(0, 1000),
            self.rand.randint(0, 1000000),
            self.rand.randint(-10000, 10000)
            ])
        # select the new row in each view
        sel = self.tree_view.get_selection()
        i1 = self.model_sort.convert_child_iter_to_iter(None, i0)
        sel.select_iter(i1)

    def __init__(self):
        # create a liststore with three int columns
        self.list_store = gtk.ListStore(int, int, int)
        # create a random number generator
        self.rand = random.Random()

        # Create new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("TreeModelSort Example")
        self.window.set_size_request(220, 200)
        self.window.connect("delete_event", self.delete_event)
        self.vbox = gtk.VBox()
        self.window.add(self.vbox)
        self.scrollable = gtk.ScrolledWindow()
        self.model_sort = gtk.TreeModelSort(self.list_store)
        # Set sort column
        n = 0
        self.model_sort.set_sort_column_id(n, gtk.SORT_ASCENDING)
        self.tree_view = gtk.TreeView(self.model_sort)
        self.vbox.pack_start(self.scrollable)
        self.b = gtk.Button('Add a Row')
        self.b.connect('clicked', self.add_row)
        self.vbox.pack_start(self.b, False)
        self.scrollable.add(self.tree_view)
        self.tree_view.column = [None] * 3
        self.tree_view.column[0] = gtk.TreeViewColumn('0-1000')
        self.tree_view.column[1] = gtk.TreeViewColumn('0-1000000')
        self.tree_view.column[2] = gtk.TreeViewColumn('-10000-10000')
        self.tree_view.cell = [None] * 3
        for i in range(3):
            self.tree_view.cell[i] = gtk.CellRendererText()
            self.tree_view.append_column(self.tree_view.column[i])
            self.tree_view.column[i].set_sort_column_id(i)
            self.tree_view.column[i].pack_start(self.tree_view.cell[i], True)
            self.tree_view.column[i].set_attributes(self.tree_view.cell[i], text=i)
        self.window.show_all()

if __name__ == "__main__":
    example = TreeModelSortExample()
    reactor.run()
