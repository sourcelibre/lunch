#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pygtk
pygtk.require('2.0')
import gtk
import webbrowser

__version__ = "0.2.6"

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

class About(object):
    """
    About dialog
    """
    def __init__(self):
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
        self.about_dialog.set_authors(['Alexandre Quessy <alexandre@quessy.net>'])
        self.about_dialog.set_artists(['Rocket000'])
        gtk.about_dialog_set_url_hook(self.show_website)
        self.about_dialog.set_website("http://svn.sat.qc.ca/trac/lunch")
        large_icon = gtk.gdk.pixbuf_new_from_file(self.icon_file)
        self.about_dialog.set_logo(large_icon)
        # Add button to show keybindings:
        #shortcut_button = ui.button(text=_("_Shortcuts"))
        #self.about_dialog.action_area.pack_start(shortcut_button)
        #self.about_dialog.action_area.reorder_child(self.about_dialog.action_area.get_children()[-1], -2)
        # Connect to callbacks
        self.about_dialog.connect('response', self.destroy)
        self.about_dialog.connect('delete_event', self.destroy)
        #shortcut_button.connect('clicked', self.about_shortcuts)
        self.about_dialog.connect("delete-event", self.destroy)
        self.about_dialog.show_all()
     
    def show_website(self, widget, data):
        webbrowser.open(data)

    def destroy(self, *args):
        self.about_dialog.destroy()

class Example(object):
    """
    ----------------------
    | Window
    | Menu_______________
    | ScrollWindow ------
    | | ViewPort --------
    | | | Table ---------
    | | | | Label, Label, Button
    """
    def __init__(self):
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Lunch")
        self.window.connect("delete_event", self.delete_event)
        self.window.set_default_size(320, 480)
        #self.window.set_size_request(300, 200)

        scroller = gtk.ScrolledWindow()
        self.window.add(scroller)
        
        dimen = 10
        NUM_EXTRA = 2
        table = gtk.Table(dimen + NUM_EXTRA, 2, True)
        scroller.add_with_viewport(table)

        menubar = self.get_main_menu(self.window)
        table.attach(menubar, 0, 2, 0, 1)

        menubar.show()
        for i in range(dimen):
            button = gtk.Button("button 1")
            button.connect("clicked", self.on_clicked, "button 1")
            table.attach(button, 0, 1, i + 1, i + 2)
            button.show()

            button = gtk.Button("button 2")
            button.connect("clicked", self.on_clicked, "button 2")
            table.attach(button, 1, 2, i + 1, i + 2)
            button.show()

        button = gtk.Button("Quit")
        button.connect("clicked", lambda w: gtk.main_quit())
        table.attach(button, 0, 2, i + 2, i + 3)
        button.show()

        table.show()
        scroller.show()
        self.window.show()

    def on_open_logs(self, widget, data):
        print "open logs"

    def on_quit(self, widget, data):
        print 'quit'

    def get_main_menu(self, window):
        menu_items = (
            ( "/_File", None, None, 0, "<Branch>" ),
            #( "/File/_New", "<control>N", self.print_hello, 0, None),
            ( "/File/_Open Logs", "<control>O", self.on_open_logs, 0, None),
            #( "/File/_Save", "<control>S", self.print_hello, 0, None),
            #( "/File/Save _As", None, None, 0, None),
            #( "/File/sep1", None, None, 0, "<Separator>"),
            ( "/File/Quit", "<control>Q", self.on_quit, 0, None),
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
        print "on about"
        About().show_about_dialog()
    
    def on_clicked(self, widget, data=None):
        """
        Our callback.
        The data passed to this method is printed to stdout
        """
        print "Hello again - %s was pressed" % data
    
    def delete_event(self, widget, event, data=None):
        # This callback quits the program
        gtk.main_quit()
        return False


if __name__ == "__main__":
    Example()
    gtk.main()
