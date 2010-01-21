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
        list_store = self.model_sort.get_model()
        tree_iter_0 = list_store.append(
            [
                "Milhouse_r_remote",
                "milhouse -s --videoport 12309 --address 12.3.2.3 --videosource v4l2 --videocodec mpeg4 --videodevice /dev/video0",
                "example.org",
                4,
                "RUNNING"
            ])
        # select the new row
        selection = self.tree_view.get_selection()
        tree_iter_1 = self.model_sort.convert_child_iter_to_iter(None, tree_iter_0)
        selection.select_iter(tree_iter_1)

    def add_row_in_tree(self, command):
        """
        adds a row with the data of the command.
        """
        list_store = self.model_sort.get_model()
        list_store.append(self._format_command(command))
        self.commands[command.identifier] = command

    def _format_command(self, command):
        """
        Returns a list of values for the cells in the row of a command
        """
        host = "localhost"
        if command.host is not None:
            host = command.host
        executions = 2
        state = command.state
        return [
                command.identifier, 
                command.command,
                host,
                executions,
                state
            ]

    ROW_IDENTIFIER = 0

    def update_row(self, command):
        list_store = self.model_sort.get_model()
        looking_for = command.identifier
        print "lllllllllllllopoook for:", looking_for
        for row in iter(list_store):
            identifier = row[self.ROW_IDENTIFIER]
            if identifier == looking_for:
                print identifier, "MATCHES!!!!!!!!!"
                cells = self._format_command(command)
                for i in range(len(cells)):
                    row[i] = cells[i]
                break
            for v in row:
                print v
        
    def _setup_treeview(self):
        """
        Needs attributes;
         * self.tree_view
         * self.model_sort
        """
        # Set initial sorting column and order.
        sorting_column_number = 0
        self.model_sort.set_sort_column_id(sorting_column_number, gtk.SORT_ASCENDING)

        NUM_COLUMNS = 5
        columns = [None] * NUM_COLUMNS
        # Set column title
        columns[0] = gtk.TreeViewColumn("Title")
        columns[1] = gtk.TreeViewColumn("Command")
        columns[2] = gtk.TreeViewColumn("Host")
        columns[3] = gtk.TreeViewColumn("Executions") # How many times
        columns[4] = gtk.TreeViewColumn("State") # str
        
        # Set default properties for each column
        cells = [None] * NUM_COLUMNS
        for i in range(NUM_COLUMNS):
            self.tree_view.append_column(columns[i])
            columns[i].set_expand(True)
            columns[i].set_max_width(400)
            columns[i].set_resizable(True)
            columns[i].set_sort_column_id(i)

            cells[i] = gtk.CellRendererText()
            cells[i].set_property("width-chars", 20) 
            columns[i].pack_start(cells[i], False) #True)
            columns[i].set_attributes(cells[i], text=i)
        # Set some custom properties
        cells[0].set_property("width-chars", 14) # Title
        cells[1].set_property("width-chars", 20) # Lifetime
        cells[2].set_property("width-chars", 12) # host
        cells[3].set_property("width-chars", 8) # Executions
        cells[4].set_property("width-chars", 8) # State
        #cells[4].set_property("foreground", 'green')


    def __init__(self):
        # Create new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Lunch Box")
        self.window.set_size_request(640, 480)
        self.window.connect("delete_event", self.delete_event)
        self.vbox = gtk.VBox()
        self.window.add(self.vbox)
        self.scrollable = gtk.ScrolledWindow()
        self.scrollable.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.scrollable.set_shadow_type(gtk.SHADOW_IN)
        self.vbox.pack_start(self.scrollable, expand=True, fill=True)
        
        # The ListStore contains the data.
        list_store = gtk.ListStore(str, str, str, int, str)
        # The TreeModelSort sorts the data
        self.model_sort = gtk.TreeModelSort(list_store)
        # The TreeView displays the sorted data in the GUI.
        self.tree_view = gtk.TreeView(self.model_sort)
        self._setup_treeview()
        self.scrollable.add(self.tree_view)
        
        self.commands = {} # for lunch

        # Add button
        self.add_button = gtk.Button('Add a Row')
        self.add_button.connect('clicked', self.add_button_clicked)
        self.vbox.pack_start(self.add_button, False)
        
        # Done. Showing the window.
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
        obj.identifier = title
        obj.command = command
        obj.host = host
        obj.state = state
        return obj

    example = Example()
    example.add_row_in_tree(factory('qweqweqwe', 'ls -lrt /'))
    example.add_row_in_tree(factory('milhouse', "milhouse -s --videoport 12309 --address 12.3.2.3 --videosource v4l2 --videocodec mpeg4 --videodevice /dev/video0"))
    example.add_row_in_tree(factory('milhouse-rekjfho9er=', 'milhouse -r '))
    example.add_row_in_tree(factory('qweqweqwe', 'ls -lrt /'))
    comm = factory('unique', 'ls -lrt /')
    example.add_row_in_tree(comm)

    comm.command = 'i changed'
    reactor.callLater(1, example.update_row, comm)
    reactor.run()
