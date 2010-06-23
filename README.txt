The Lunch distributed process launcher
======================================

Lunch is a simple distributed process launcher and manager for GNU/Linux.

With Lunch, one can launch software processes on several different computers
and make sure they keep running. This software was created to suit the needs
of new media artists for live performances and interactive installations.
It respawns the software that crash and provides a mean to manage
dependencies between running processes.

It provides the command-line lunch utility which can be invoked with a GTK+
user interface.

See http://svn.sat.qc.ca/trac/lunch for more information.


USING LUNCH
===========

Here is a quick how-to. Make sure lunch is installed first. (see INSTALL)
There should be a Lunch icon in the Application/Other Gnome menu.

Copy the "config-sample" example config file to the local ~/.lunchrc ::

 cp doc/examples/config-sample ~/.lunchrc

Edit the configuration file to suit your needs::

 edit ~/.lunchrc

Start the lunch master::

 lunch

A remote lunch as a slave is started this way::

 lunch -s -c "xlogo"
 lunch -s -c "xdg-open /usr/local/share/pixmaps/lunch.png"

The .lunch/config file is written in Python and the only function needed is add_command. Here are some examples::

 add_command(command="xlogo", env={}, title="xlogo")
 add_command(command="mplayer /usr/share/example-content/Ubuntu_Free_Culture_Showcase/StopMotionUbuntu.ogv", env={}, title="mplayer")

Setting the user and host arguments make it be issued through SSH to a remote host::
 
 add_command(command="xlogo", env={"DISPLAY":":0.0"}, user=_user, host="example.org", title="remote_xlogo")

