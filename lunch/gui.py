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

if __name__ == "__main__":
    from twisted.internet import gtk2reactor
    gtk2reactor.install() # has to be done before importing reactor
from twisted.internet import reactor
from twisted.internet import defer
from twisted.internet import utils
from twisted.python import procutils

#import glib
import gtk
import sys
import os
import webbrowser

__version__ = "0.2.10"

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

def open_path(path):
    """
    Opens a directory or file using gnome-open.
    Returns a Deferred or None.
    """
    def _cb(result):
        #print(result)
        pass
    try:
        executable = procutils.which("gnome-open")[0]
    except IndexError:
        print("Could not find gnome-open")
        return None
    else:
        print("Calling %s %s" % (executable, path))
        d = utils.getProcessValue(executable, [path], os.environ, '.', reactor)
        d.addCallback(_cb)
        return d

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
        #try:
            large_icon = gtk.gdk.pixbuf_new_from_file(self.icon_file)
            self.about_dialog.set_logo(large_icon)
        #except glib.GError, e:
        #    print(str(e))
        # Add button to show keybindings:
        #shortcut_button = ui.button(text=_("_Shortcuts"))
        #self.about_dialog.action_area.pack_start(shortcut_button)
        #self.about_dialog.action_area.reorder_child(self.about_dialog.action_area.get_children()[-1], -2)
        # Connect to callbacks
        self.about_dialog.connect('response', self.destroy_about)
        self.about_dialog.connect('delete_event', self.destroy_about)
        #shortcut_button.connect('clicked', self.about_shortcuts)
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
        # Window and framework
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Lunch")
        self.window.connect("destroy", self.destroy_app)
        WIDTH = 400
        HEIGHT = 600
        self.window.set_default_size(WIDTH, HEIGHT)
        
        # Vertical Box
        vbox = gtk.VBox(False)
        self.window.add(vbox)
        
        # Menu bar
        self.menubar = self.create_main_menu(self.window)
        vbox.pack_start(self.menubar, expand=False, fill=False)
        self.menubar.show()

        # Scrollable
        scroller = gtk.ScrolledWindow()
        vbox.add(scroller)
        
        self.commands = master.get_all_commands()
        row_per_command = 2
        num_rows = len(self.commands) * row_per_command
        num_columns = 2
        offset = 0
        self.table = gtk.Table(num_rows, num_columns, True)
        scroller.add_with_viewport(self.table)
        current_row = 0
        
        # Buttons
        self.title_labels = {}
        self.state_labels = {}
        #self.start_buttons = {}
        
        for i in range(len(self.commands)):
            command = self.commands[i]

            self.title_labels[i] = gtk.Label()
            user_host = ""
            #if command.host is not None:
            #    if command.user is not None:
            #        user_host = "(%s@%s)" % (command.user, command.host)
            #    else:
            #        user_host = "(%s)" % (command.host)
            txt = "%s\n<small>%s</small>" % (command.identifier, command.command)
            #txt = "%s <small>%s<small>\n<small>%s</small>" % (command.identifier, user_host, command.command)
            self.title_labels[i].set_markup(txt) # pango markup
            #self.title_labels[i].set_line_wrap(True)
            #self.title_labels[i].set_selectable(True)
            self.title_labels[i].set_justify(gtk.JUSTIFY_LEFT)
            gtk.Misc.set_alignment(self.title_labels[i], 0.0, 0.0) # withinin range [0.,1.]

            self.table.attach(self.title_labels[i], 0, 1, current_row, current_row + 1)
            #self.title_labels[i].set_width_chars(20)
            self.title_labels[i].show()

            if hasattr(command, "child_state_changed_signal"):
                print("Connecting state changed signal to GUI.")
                command.child_state_changed_signal.connect(self.on_command_status_changed)
            
            self.state_labels[i] = gtk.Label()
            self.state_labels[i].set_markup("%s\n<small>(ran 0 time)</small>" % (command.child_state))
            self.table.attach(self.state_labels[i], 1, 2, current_row, current_row + 1)
            #self.state_labels[i].set_width_chars(20)
            gtk.Misc.set_alignment(self.state_labels[i], 1.0, 1.0) # withinin range [0.,1.]
            self.state_labels[i].show()
            current_row += 1
            
            # separator
            sep = gtk.HSeparator()
            sep.set_size_request(WIDTH - 30, 4)
            self.table.attach(sep, 0, 2, current_row, current_row + 1, yoptions=gtk.FILL)
            current_row += 1
            sep.show()

            #self.start_buttons[i] = gtk.Button("Stop")
            #self.hboxes[i].pack_start(self.start_buttons[i], True, True, 0)
            #self.start_buttons[i].connect("clicked", self.on_start_clicked, i)
            #self.start_buttons[i].show()

        #self.stopall_button = gtk.Button("Stop All")
        #self.stopall_button.connect("clicked", self.on_stopall_clicked)
        #self.table.attach(self.stopall_button, 0, 2, num_rows - 1, num_rows)
        #self.stopall_button.show()

        self.table.show()
        scroller.show()
        vbox.show()
        self.window.show()

    def on_menu_open_logs(self, widget, data):
        #TODO:
        if hasattr(self.master, "log_dir"):
            open_path(self.master.log_dir)
        #print "open logs"

    def create_main_menu(self, window):
        menu_items = (
            ( "/_File", None, None, 0, "<Branch>" ),
            #( "/File/_New", "<control>N", self.print_hello, 0, None),
            ( "/File/_Open Logs", "<control>O", self.on_menu_open_logs, 0, None),
            #( "/File/_Save", "<control>S", self.print_hello, 0, None),
            #( "/File/Save _As", None, None, 0, None),
            #( "/File/sep1", None, None, 0, "<Separator>"),
            ( "/File/Quit", "<control>Q", self.destroy_app, 0, None),
            #( "/_Options", None, None, 0, "<Branch>"),
            #( "/Options/Test",  None, None, 0, None),
            ( "/_Help", None, None, 0, "<LastBranch>"),
            ( "/_Help/About", None, self.on_about, 0, None),
            )
        accel_group = gtk.AccelGroup()
        item_factory = gtk.ItemFactory(gtk.MenuBar, "<main>", accel_group)
        item_factory.create_items(menu_items)
        window.add_accel_group(accel_group)
        # need to keep a reference to item_factory to prevent its destruction
        self.item_factory = item_factory
        return item_factory.get_widget("<main>")

    def on_about(self, widget, data):
        #print "on about"
        About().show_about_dialog()
    
    def on_start_clicked(self, widget, info): # index as info
        #print "Button %s was pressed" % (info)
        print("Toggle start/stop %d" % (info))

    #def on_stopall_clicked(self, widget): # index as info
    #    print("Stop All")

    def on_command_status_changed(self, command, new_state):
        """
        Called when the child_state_changed_signal of the command is triggered.
        @param command L{Command} 
        @param new_state str
        """
        txt = "%s\n<small>(ran %d times)</small>" % (new_state, command.how_many_times_run)
        i = self.commands.index(command)
        self.state_labels[i].set_markup(txt)
        print("GUI: Child %s changed its state to %s" % (command.identifier, new_state))

    def destroy_app(self, widget, data=None):
        """
        Destroy method causes appliaction to exit
        when main window closed
        """
        print("Destroying the window.")
        try:
            gtk.main_quit()
        except RuntimeError, e:
            print(str(e))
        if reactor.running:
            print("reactor.stop()")
            reactor.stop()

def start_gui(lunch_master):
    """
    Starts the GTK GUI
    :rettype: L{LunchApp}
    """
    print("Starting the GUI.")
    app = LunchApp(lunch_master)
    #self.slave_state_changed_signal = sig.Signal()
    return app

if __name__ == "__main__":
    class Command(object):
        def __init__(self):
            self.state = "RUNNING"
            self.identifier = "/usr/bin/hello"
            
    class DummyMaster(object):
        def get_all_commands(self):
            """
            @rettype: list
            """
            data = []
            for i in range(10):
                data.append(Command())
            return data

    dummy_master = DummyMaster()
    start_gui(dummy_master)
    reactor.run()
