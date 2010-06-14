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
Main GUI of the Lunch Master 
"""
if __name__ == "__main__":
    from twisted.internet import gtk2reactor
    gtk2reactor.install() # has to be done before importing reactor
from twisted.internet import reactor
from twisted.internet import defer
from twisted.internet import utils
from twisted.python import procutils

import gtk
import sys
import os
import webbrowser
from lunch import __version__
from lunch import dialogs

__license__ = """Lunch
Copyright (C) 2009 Society for Arts and Technology (SAT)
http://www.sat.qc.ca
All rights reserved.

This file is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

Lunch is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lunch.  If not, see <http://www.gnu.org/licenses/>."""

def run_once(executable, *args):
    """
    Runs a command, without looking at its output or return value.
    Returns a Deferred or None.
    """
    def _cb(result):
        #print(result)
        pass
    try:
        executable = procutils.which(executable)[0]
    except IndexError:
        print("Could not find executable %s" % (executable))
        return None
    else:
        print("Calling %s %s" % (executable, list(args)))
        d = utils.getProcessValue(executable, args, os.environ, '.', reactor)
        d.addCallback(_cb)
        return d

def open_path(path):
    """
    Opens a directory or file using gnome-open.
    Returns a Deferred or None.
    """
    return run_once("gnome-open", path)

def tail_child_log(command):
    """
    Opens a terminal window with the tail of the log file for the child 
    process of a command. Uses SSH if needed.
    @param command: L{lunch.commands.Command}
    """
    #TODO: really need to make a valid path in add_command and keep it.
    child_log_path = os.path.join(command.child_log_dir, "child-%s.log" % (command.identifier))
    xterm_title = 'tail -F %s' % (command.identifier)
    cmd = []
    cmd.extend(["xterm", "-title", '%s' % (xterm_title), "-e"])
    if command.host is not None: # using SSH
        cmd.extend(["ssh"])
        if command.user is not None:
            cmd.extend(["-l", command.user])
        cmd.extend([command.host])
        xterm_title += " on " + command.host
    cmd.extend(["tail", "-F", child_log_path])
    print("$ %s" % (" ".join(cmd)))
    run_once(*cmd)

def tail_master_log(master):
    log_path = master.log_file
    if log_path is None:
        print("No master log file to tail -F") # TODO: error dialog.
    else:
        cmd = []
        xterm_title = "tail -F Lunch Master Log File"
        cmd.extend(["xterm", "-title", '%s' % (xterm_title), "-e"])
        cmd.extend(["tail", "-F", log_path])
        print("$ %s" % (" ".join(cmd)))
        run_once(*cmd)
    
class About(object):
    """
    About dialog
    """
    def __init__(self):
        # FIXME
        self.icon_file = "/usr/share/pixmaps/lunch.png"
        self.about_dialog = gtk.AboutDialog()

    def show_about_dialog(self):
        self.about_dialog.set_name('Lunch')
        self.about_dialog.set_role('about')
        self.about_dialog.set_version(__version__)
        commentlabel = 'Simple Process Launcher for Complex Launching Setup.'
        self.about_dialog.set_comments(commentlabel)
        self.about_dialog.set_copyright("Copyright 2009 Society for Arts and Technology")
        self.about_dialog.set_license(__license__)
        self.about_dialog.set_authors([
            'Alexandre Quessy <alexandre@quessy.net>', 
            'Simon Piette <simonp@sat.qc.ca>'
            ])
        self.about_dialog.set_artists(['Rocket000'])
        gtk.about_dialog_set_url_hook(self.show_website)
        self.about_dialog.set_website("http://svn.sat.qc.ca/trac/lunch")
        if not os.path.exists(self.icon_file):
            print("Could not find icon file %s." % (self.icon_file))
        else:
            large_icon = gtk.gdk.pixbuf_new_from_file(self.icon_file)
            self.about_dialog.set_logo(large_icon)
        # Connect to callbacks
        self.about_dialog.connect('response', self.destroy_about)
        self.about_dialog.connect('delete_event', self.destroy_about)
        self.about_dialog.connect("delete-event", self.destroy_about)
        self.about_dialog.show_all()
     
    def show_website(self, widget, data):
        webbrowser.open(data)

    def destroy_about(self, *args):
        self.about_dialog.destroy()

class LunchApp(object):
    """
    Simple GTK2 GUI for Lunch Master.
    
    Defines the main window
    """
    def __init__(self, master=None):
        self.master = master
        self.confirm_close = True # should we ask if the user is sure to close the app?
        _commands = master.get_all_commands()

        # Window and framework
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Lunch")
        self.window.connect("delete-event", self.destroy_app)
        #self.window.connect("destroy", self.destroy_app)
        WIDTH = 640
        HEIGHT = 480
        self.window.set_default_size(WIDTH, HEIGHT)

        #TODO: more robust icon handling.
        icon_file = "/usr/share/pixmaps/lunch.png"
        if not os.path.exists(icon_file):
            print("Warning: Could not find icon file %s." % (icon_file))
        else:
            icon = gtk.gdk.pixbuf_new_from_file(icon_file)
            self.window.set_icon_list(icon)
        
        # Vertical Box
        vbox = gtk.VBox(False)
        self.window.add(vbox)
        
        # Menu bar
        self.menubar = self.create_main_menu(self.window)
        vbox.pack_start(self.menubar, expand=False, fill=False)
        self.menubar.show()

        # Scrollable
        scroller = gtk.ScrolledWindow()
        scroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scroller.set_shadow_type(gtk.SHADOW_IN)
        vbox.pack_start(scroller, expand=True, fill=True)
        #vbox.add(scroller)

        # The ListStore contains the data.
        list_store = gtk.ListStore(str, str, str, int, str)
        # The TreeModelSort sorts the data
        self.model_sort = gtk.TreeModelSort(list_store)
        # The TreeView displays the sorted data in the GUI.
        self.tree_view = gtk.TreeView(self.model_sort)
        self._setup_treeview()
        scroller.add(self.tree_view)
        for command in _commands:
            self._add_command_in_tree(command)

        self.master.command_added_signal.connect(self.on_command_added)
        self.master.command_removed_signal.connect(self.on_command_removed)
        
        # Box with buttons.
        hbox = gtk.HBox(homogeneous=True)
        vbox.pack_start(hbox, expand=False)
        
        openlog_button = gtk.Button("Open child process log file")
        openlog_button.connect("clicked", self.on_openlog_clicked)
        hbox.pack_start(openlog_button)
        
        stop_command_button = gtk.Button("Stop child process")
        stop_command_button.connect("clicked", self.on_stop_command_clicked)
        hbox.pack_start(stop_command_button)

        start_command_button = gtk.Button("Start child process")
        start_command_button.connect("clicked", self.on_start_command_clicked)
        hbox.pack_start(start_command_button)
        
        self.window.show_all()

    #def _create_buttons(self): 
        #TODO: open log
        #TODO: disable/enable/restart
        #self.stopall_button = gtk.Button("Stop All")
        #self.stopall_button.connect("clicked", self.on_stopall_clicked)
        #self.table.attach(self.stopall_button, 0, 2, num_rows - 1, num_rows)
        #self.stopall_button.show()

    IDENTIFIER_COLUMN = 0 # the row in the treeview that contains the command identifier.

    def on_command_added(self, command):
        print("on_command_added")
        self._add_command_in_tree(command)
        
    def on_command_removed(self, command):
        print("on_command_removed")
        self._remove_command_from_tree(command)

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

    def _add_command_in_tree(self, command):
        """
        adds a row with the data of the command.
        """
        list_store = self.model_sort.get_model()
        list_store.append(self._format_command(command))
        #self.commands[command.identifier] = command
        #print("Connecting state changed signal to GUI.")
        command.child_state_changed_signal.connect(self.on_command_status_changed)

    def _remove_command_from_tree(self, command):
        """
        When a command is removed, removes it from the tree view.
        """
        list_store = self.model_sort.get_model()
        looking_for = command.identifier
        #list_store.append(self._format_command(command))
        row_number = 0
        for row in iter(list_store):
            identifier = row[self.IDENTIFIER_COLUMN]
            if identifier == looking_for:
                # Delete it!
                break
            row_number += 1
        
        print("Removing a row from the list store.")
        list_store.remove(list_store.get_iter(row_number))
        #print("Removing GUI's slot for state changed signal.")
        command.child_state_changed_signal.disconnect(self.on_command_status_changed)

    def _update_row(self, command):
        list_store = self.model_sort.get_model()
        looking_for = command.identifier
        #print "look for:", looking_for
        for row in iter(list_store):
            identifier = row[self.IDENTIFIER_COLUMN]
            if identifier == looking_for:
                #print identifier, "MATCHES!!!!!!!!!"
                #TODO: update only columns how_many_times_run and child_state
                cells = self._format_command(command)
                for i in range(len(cells)):
                    row[i] = cells[i]
                break
            for v in row:
                print v

    def _format_command(self, command):
        """
        Returns a list of values for the cells in the row of a command
        """
        host = "localhost"
        if command.host is not None:
            host = command.host
        executions = command.how_many_times_run
        state = command.child_state
        return [
                command.identifier, 
                command.command,
                host,
                executions,
                state
            ]
    

    def on_menu_open_logs(self, widget, data):
        #TODO:
        if hasattr(self.master, "log_dir"):
            open_path(self.master.log_dir)
        #print "open logs"

    def on_menu_view_master_log(self, widget, data):
        tail_master_log(self.master)

    def create_main_menu(self, window):
        menu_items = (
            ( "/_File", None, None, 0, "<Branch>" ),
            #( "/File/_New", "<control>N", self.print_hello, 0, None),
            ( "/File/_Open Logging Directory", "<control>O", self.on_menu_open_logs, 0, None),
            ( "/File/_View Master Log File", None, self.on_menu_view_master_log, 0, None),
            #( "/File/Save _As", None, None, 0, None),
            #( "/File/sep1", None, None, 0, "<Separator>"),
            ( "/File/Quit", "<control>Q", self.destroy_app, 0, None),
            #( "/_Options", None, None, 0, "<Branch>"),
            #( "/Options/Test",  None, None, 0, None),
            ( "/_Help", None, None, 0, "<LastBranch>"),
            ( "/_Help/About", None, self.on_about, 0, None),
            )
        accel_group = gtk.AccelGroup()
        #FIXME: the following line causes a exceptions.DeprecationWarning: use gtk.UIManager
        item_factory = gtk.ItemFactory(gtk.MenuBar, "<main>", accel_group)
        item_factory.create_items(menu_items)
        window.add_accel_group(accel_group)
        # need to keep a reference to item_factory to prevent its destruction
        self.item_factory = item_factory
        return item_factory.get_widget("<main>")

    def on_about(self, widget, data):
        #print "on about"
        About().show_about_dialog()
    
    def _get_currently_selected_command(self, show_error_if_none=True):
        """
        Returns a lunch.commands.Command object or None.
        """
        ret = None
        selection = self.tree_view.get_selection()
        model, rows = selection.get_selected()
        if rows is None:
            ret = None
            if show_error_if_none:
                msg = "Please select a process in the list."
                d = defer.Deferred()
                dialog = dialogs.ErrorDialog(d, msg)
        else:
            print 'getting the currently selected row in the tree view.'
            row = rows # only one row selected at a time in this version
            identifier = model.get_value(row, self.IDENTIFIER_COLUMN)
            print 'id', identifier
            ret = self.master.commands[identifier]
        return ret
        
    def on_openlog_clicked(self, widget):
        command = self._get_currently_selected_command()
        if command is not None:
            tail_child_log(command)

    def on_stop_command_clicked(self, widget):
        command = self._get_currently_selected_command()
        if command is not None:
            command.stop()
    
    def on_start_command_clicked(self, widget):
        command = self._get_currently_selected_command()
        if command is not None:
            command.start()

    #def on_stopall_clicked(self, widget): # index as info
    #    print("Stop All")

    def on_command_status_changed(self, command, new_state):
        """
        Called when the child_state_changed_signal of the command is triggered.
        @param command L{lunch.commands.Command} 
        @param new_state str
        """
        #txt = "%s\n<small>(ran %d times)</small>" % (new_state, command.how_many_times_run)
        #i = self.commands.index(command)
        #self.state_labels[i].set_markup(txt)
        print("GUI: Child %s changed its state to %s" % (command.identifier, new_state))
        self._update_row(command)

    def destroy_app(self, widget, data=None):
        """
        Destroy method causes appliaction to exit
        when main window closed
        """
        def _cb(result):
            if result:
                print("Destroying the window.")
                if reactor.running:
                    print("reactor.stop()")
                    reactor.stop()
            else:
                print("Not quitting.")
        # If you return FALSE in the "delete_event" signal handler,
        # GTK will emit the "destroy" signal. Returning TRUE means
        # you don't want the window to be destroyed.
        # This is useful for popping up 'are you sure you want to quit?'
        # type dialogs. 
        if self.confirm_close:
            d = dialogs.YesNoDialog.create("Really quit ?\nAll launched processes will quit as well.")
            d.addCallback(_cb)
            return True
        else:
            _cb(True)
            return False

def start_gui(lunch_master):
    """
    Starts the GTK GUI
    :rettype: L{LunchApp}
    """
    print("Starting the GUI.")
    app = LunchApp(lunch_master)
    #self.slave_state_changed_signal = sig.Signal()
    return app

