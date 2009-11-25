INSTALLATION
============
You will need a few software. On Ubuntu, install them using the following command ::

  sudo apt-get install build-essential openssh-client openssh-server python-setuptools help2man
  sudo easy_install multiprocessing

Copy the "config-sample" example config file to the local ~/.lunch/config::

 mkdir ~/.lunch 
 cp config-sample ~/.lunch/config

Edit the configuration file to suit your needs::

 edit ~/.lunch/config

Install lunch to /usr/local/bin/lunch on both local and remote hosts::

 sudo make install

There should be a Lunch icon in the Application/Other Gnome menu.

Start the lunch master::

 lunch

A remote lunch as a slave is started this way::

 lunch -s -c "xlogo"
 lunch -s -c "xdg-open /usr/local/share/icons/Lunch.svg"

The .lunch/config file is written in Python and the only function needed is add_command. Here are some examples::

 add_command(command="xlogo", env={}, title="xlogo")
 add_command(command="mplayer /usr/share/example-content/Ubuntu_Free_Culture_Showcase/StopMotionUbuntu.ogv", env={}, title="mplayer")

Setting the user and host arguments make it be issued through SSH to a remote host::
 
 add_command(command="xlogo", env={"DISPLAY":":0.0"}, user=_user, host="example.org", title="remote_xlogo")

DOCUMENTATION
=============
You can generate HTML out of this README.txt file using rst2html::

 rst2html README.txt readme.html

Pydoc can generate HTML documentation out of the Python script::

 pydoc -w ./lunch

See the Makefile for more installation options::

 make doc

LICENSE 
=========
Lunch
Copyright (C) 2008 Société des arts technologiques (SAT)
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
along with Lunch. If not, see <http://www.gnu.org/licenses/>.


IMAGES 
=======
The source of Lunch's icon is http://commons.wikimedia.org/wiki/File:Fruit-cherries.svg and is in the public domain. Thank you Rocket000 !
