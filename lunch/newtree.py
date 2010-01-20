#!/usr/bin/env python
# example treemodelsort.py
if __name__ == "__main__":
    from twisted.internet import gtk2reactor
    gtk2reactor.install() # has to be done before importing reactor
from twisted.internet import reactor
import gtk
import random

class Example:

    # close the window and quit
    def delete_event(self, widget, event, data=None):
        reactor.stop()
        return False

    def add_button_clicked(self, widget):
        rand = self.rand
        # add a row of random ints
        i0 = self.model_sort.get_model().append(
            [
                "Milhouse_r_remote",
                "milhouse -s --videoport 12309 --address 12.3.2.3 --videosource v4l2 --videocodec mpeg4 --videodevice /dev/video0",
                "example.org",
                4234.4334,
                4,
                "RUNNING"
            ])
        # select the new row in each view
        selection = self.tree_view.get_selection()
        i1 = self.model_sort.convert_child_iter_to_iter(None, i0)
        selection.select_iter(i1)

    def __init__(self):

        # Create new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Lunch Box")
        self.window.set_size_request(220, 200)
        self.window.connect("delete_event", self.delete_event)
        self.vbox = gtk.VBox()
        self.window.add(self.vbox)
        self.scrollable = gtk.ScrolledWindow()
        
        # The ListStore contains the data.
        self.list_store = gtk.ListStore(str, str, str, float, int, str)
        # The TreeModelSort sorts the data
        # TODO: get rid of the TreeModelSort, use a TreeSortable instead.
        self.model_sort = gtk.TreeModelSort(self.list_store)
        self.rand = random.Random() #TODO: remove
        # Set initial sorting column and order.
        sorting_column_number = 0
        self.model_sort.set_sort_column_id(sorting_column_number, gtk.SORT_ASCENDING)
        # The TreeView displays the sorted data in the GUI.
        self.tree_view = gtk.TreeView(self.model_sort)
        
        self.vbox.pack_start(self.scrollable)
        # Add button
        self.add_button = gtk.Button('Add a Row')
        self.add_button.connect('clicked', self.add_button_clicked)
        self.vbox.pack_start(self.add_button, False)
        # TreeView widget.
        self.scrollable.add(self.tree_view)
        
        NUM_COLUMNS = 6
        self.columns = [None] * NUM_COLUMNS
        # Set column title
        self.columns[0] = gtk.TreeViewColumn("Title")
        self.columns[1] = gtk.TreeViewColumn("Command")
        self.columns[2] = gtk.TreeViewColumn("Host")
        self.columns[3] = gtk.TreeViewColumn("Lifetime")
        self.columns[4] = gtk.TreeViewColumn("Executions") # How many times
        self.columns[5] = gtk.TreeViewColumn("State") # str
        
        # Leave that as it is...
        self.cells = [None] * NUM_COLUMNS
        for i in range(NUM_COLUMNS):
            self.cells[i] = gtk.CellRendererText()
            self.tree_view.append_column(self.columns[i])
            
            self.columns[i].set_expand(True)
            self.columns[i].set_max_width(400)
            self.columns[i].set_resizable(True)
            self.columns[i].set_sort_column_id(i)
            self.columns[i].pack_start(self.cells[i], False) #True)
            self.columns[i].set_attributes(self.cells[i], text=i)
        # Done with the table. Showing the window.
        self.window.show_all()

if __name__ == "__main__":
    example = Example()
    reactor.run()
