INSTALLATION
============
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


DOCUMENTATION
=============
You can generate HTML out of this README.txt file using rst2html::

 rst2html README.txt readme.html

Pydoc can generate HTML documentation out of the Python script::

 pydoc -w ./lunch

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



