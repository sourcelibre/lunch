#!/usr/bin/env python
# example treemodelsort.py
if __name__ == "__main__":
    from twisted.internet import gtk2reactor
    gtk2reactor.install() # has to be done before importing reactor
from twisted.internet import reactor
import gtk

class Example:

    # close the window and quit
    def delete_event(self, widget, event, data=None):
        reactor.stop()
        return False

    def add_button_clicked(self, widget):
        i0 = self.model_sort.get_model().append(
            [
                "Milhouse_r_remote",
                "milhouse -s --videoport 12309 --address 12.3.2.3 --videosource v4l2 --videocodec mpeg4 --videodevice /dev/video0",
                "example.org",
                4234.4334,
                4,
                "RUNNING"
            ])
        # select the new row
        selection = self.tree_view.get_selection()
        i1 = self.model_sort.convert_child_iter_to_iter(None, i0)
        selection.select_iter(i1)

    def add_row(self, command):
        host = "localhost"
        if command.host is not None:
            host = command.host
        life_time = 1.000 # TODO: remove
        executions = 2
        state = command.state
        self.list_store.append(
            [
                command.title, 
                command.command,
                host,
                life_time, 
                executions,
                state
            ])
        

    def __init__(self):

        # Create new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Lunch Box")
        self.window.set_size_request(220, 200)
        self.window.connect("delete_event", self.delete_event)
        self.vbox = gtk.VBox()
        self.window.add(self.vbox)
        self.scrollable = gtk.ScrolledWindow()
        self.scrollable.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.scrollable.set_shadow_type(gtk.SHADOW_IN)
        self.vbox.pack_start(self.scrollable, expand=True, fill=True)
        
        # The ListStore contains the data.
        self.list_store = gtk.ListStore(str, str, str, float, int, str)
        # The TreeModelSort sorts the data
        self.model_sort = gtk.TreeModelSort(self.list_store)
        # Set initial sorting column and order.
        sorting_column_number = 0
        self.model_sort.set_sort_column_id(sorting_column_number, gtk.SORT_ASCENDING)
        # The TreeView displays the sorted data in the GUI.
        self.tree_view = gtk.TreeView(self.model_sort)
        
        # Add button
        self.add_button = gtk.Button('Add a Row')
        self.add_button.connect('clicked', self.add_button_clicked)
        self.vbox.pack_start(self.add_button, False)
        # TreeView widget.
        self.scrollable.add(self.tree_view)
        
        NUM_COLUMNS = 6
        columns = [None] * NUM_COLUMNS
        # Set column title
        columns[0] = gtk.TreeViewColumn("Title")
        columns[1] = gtk.TreeViewColumn("Command")
        columns[2] = gtk.TreeViewColumn("Host")
        columns[3] = gtk.TreeViewColumn("Lifetime")
        columns[4] = gtk.TreeViewColumn("Executions") # How many times
        columns[5] = gtk.TreeViewColumn("State") # str
        
        # Leave that as it is...
        cells = [None] * NUM_COLUMNS
        for i in range(NUM_COLUMNS):
            self.tree_view.append_column(columns[i])
            columns[i].set_expand(True)
            columns[i].set_max_width(400)
            columns[i].set_resizable(True)
            columns[i].set_sort_column_id(i)

            cells[i] = gtk.CellRendererText()
            cells[i].set_property("width-chars", 20) # FIXME
            columns[i].pack_start(cells[i], False) #True)
            columns[i].set_attributes(cells[i], text=i)
        # Done with the table. Showing the window.
        self.window.show_all()

if __name__ == "__main__":
    def factory(title="", command="", host=None, state="RUNNING"):
        class O:
            def __init__(self):
                self.title = None
                self.command = None
                self.host = None
                self.state = None
        obj = O()
        obj.title = title
        obj.command = command
        obj.host = host
        obj.state = state
        return obj

    example = Example()
    example.add_row(factory('qweqweqwe', 'ls -lrt /'))
    example.add_row(factory('milhouse', "milhouse -s --videoport 12309 --address 12.3.2.3 --videosource v4l2 --videocodec mpeg4 --videodevice /dev/video0"))
    example.add_row(factory('milhouse-rekjfho9er=', 'milhouse -r '))
    example.add_row(factory('qweqweqwe', 'ls -lrt /'))
    example.add_row(factory('qweqweqwe', 'ls -lrt /'))

    reactor.run()
