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
import gtk
import sys
import os

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
        self.window.connect("destroy", self.destroy)
        self.window.set_default_size(320, 480)
        
        scroller = gtk.ScrolledWindow()
        self.window.add(scroller)
        
        self.commands = master.get_all_commands()
        num_rows = len(self.commands) + 1
        num_columns = 2
        offset = 0
        self.table = gtk.Table(num_rows, num_columns, True)
        scroller.add_with_viewport(self.table)
        
        #TODO:
        #menubar = self.get_main_menu(self.window)
        #self.table.attach(menubar, 0, 2, 0, 1)
        

        # Buttons
        self.title_labels = {}
        self.state_labels = {}
        #self.start_buttons = {}
        
        for i in range(len(self.commands)):
            command = self.commands[i]

            self.title_labels[i] = gtk.Label()
            txt = "%s\n<small>%s</small>" % (command.identifier, command.command)
            self.title_labels[i].set_markup(txt) # pango markup
            #self.title_labels[i].set_line_wrap(True)
            self.title_labels[i].set_justify(gtk.JUSTIFY_LEFT)

            self.table.attach(self.title_labels[i], 0, 1, i + offset, i + offset + 1)
            self.title_labels[i].set_width_chars(20)
            self.title_labels[i].show()

            if hasattr(command, "child_state_changed_signal"):
                print("Connecting state changed signal to GUI.")
                command.child_state_changed_signal.connect(self.on_command_status_changed)
            
            self.state_labels[i] = gtk.Label("%s" % (command.child_state))
            self.table.attach(self.state_labels[i], 1, 2, i + offset, i + offset + 1)
            self.state_labels[i].set_width_chars(20)
            self.state_labels[i].show()
            
            #self.start_buttons[i] = gtk.Button("Stop")
            #self.hboxes[i].pack_start(self.start_buttons[i], True, True, 0)
            #self.start_buttons[i].connect("clicked", self.on_start_clicked, i)
            #self.start_buttons[i].show()

        #self.stopall_button = gtk.Button("Stop All")
        #self.stopall_button.connect("clicked", self.on_stopall_clicked)
        #self.box1.pack_start(self.stopall_button, True, True, 0)
        #self.stopall_button.show()

        self.quitbutton = gtk.Button("Quit")
        self.quitbutton.connect("clicked", self.destroy)
        self.table.attach(self.quitbutton, 0, 2, num_rows - 1, num_rows)
        self.quitbutton.show()
        
        # Show the box
        self.table.show()
        scroller.show()

        # Show the window
        self.window.show()

    def on_start_clicked(self, widget, info): # index as info
        #print "Button %s was pressed" % (info)
        print("Toggle start/stop %d" % (info))

    def on_stopall_clicked(self, widget): # index as info
        print("Stop All")

    def on_command_status_changed(self, command, new_state):
        """
        Called when the child_state_changed_signal of the command is triggered.
        @param command L{Command} 
        @param new_state str
        """
        txt = new_state
        i = self.commands.index(command)
        self.state_labels[i].set_label(txt)
        print("GUI: Child %s changed its state to %s" % (command.identifier, new_state))

    def destroy(self, widget, data=None):
        """
        Destroy method causes appliaction to exit
        when main window closed
        """
        print("Destroying the window.")
        gtk.main_quit()
        print("reactor.stop()")
        reactor.stop()

    def main(self):
        """
        All PyGTK applications need a main method - event loop
        """
        pass
        #print("pre-gtk.main()")
        #gtk.main()
        #print("post-gtk.main()")

def start_gui(lunch_master):
    """
    Starts the GTK GUI
    :rettype: L{LunchApp}
    """
    print("Starting the GUI.")
    app = LunchApp(lunch_master)
    #self.slave_state_changed_signal = sig.Signal()
    #reactor.callLater(0, app.main)
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
