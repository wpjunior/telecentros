#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2011 Wilson Pinto Júnior <wilsonpjunior@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import logging
import getopt

from TeleCentros.globals import *
from TeleCentros.utils import mkdir
_ = gettext.gettext

disable_autodebug = False
verbose = False

try:
    opts, args = getopt.getopt(sys.argv[1:], 'hvp:', ['help', 'verbose',
        'disable-autoverbose', 'version'])

except getopt.error, msg:
    print msg
    print _('for help use --help')
    sys.exit(2)

for o, a in opts:
    
    if o in ('-h', '--help'):
        print sys.argv[0], '[--help] [--verbose] [--disable-autoverbose] [--version]'
        sys.exit()
        
    elif o == '--verbose':
        verbose = False
    
    elif o == '--disable_autoverbose':
        disable_autodebug = True
    
    elif o == '--version':
        print APP_NAME, APP_VERSION
        sys.exit()

try:
    import pygtk
    pygtk.require('2.0')
    
    import gtk
except ImportError:
    print >> sys.stderr, _('OpenLanhouse needs PyGTK to run. Please install '+
                           'the latest stable version from ' +
                           'http://www.pygtk.org')
    sys.exit(3)

from TeleCentros.ConfigClient import config_init, get_default_client
from TeleCentros.defaults import defaults
config_init("TeleCentros", CONFIG_FILE, defaults)

from time import strftime
from TeleCentros import main
from TeleCentros.utils import rename_process, pid_alive
from TeleCentros.utils import generate_id_bytime #USE MAC
from TeleCentros.ui import dialogs

# Check OpenlhClient is already running
if pid_alive('TeleCentros', CLIENT_PID_FILE):
    dialogs.ok_only(_('TeleCentros is already running'),
                    ICON=dialogs.gtk.MESSAGE_ERROR)
    sys.exit(3)

pid_dir =  os.path.dirname(CLIENT_PID_FILE)
if not os.path.exists(pid_dir):
    mkdir(pid_dir)

f = open(CLIENT_PID_FILE, 'w')
f.write(str(os.getpid()))
f.close()
del pid_dir
del f

class TeleCentros:
    
    def __init__(self):
        
        rename_process('telecentros')
        mkdir(CACHE_PATH)
        logging.info('Starting Telecentros Client')
        self.conf_client = get_default_client()
        
        if not self.conf_client.get_string('hash_id'):
            self.conf_client.set_string('hash_id',
                                         generate_id_bytime()) #Generate Hash_ID
        
        if not self.conf_client.get_string('server'):
            dlg = dialogs.ConnectServer()
            host = dlg.run()
            
            if host:
                self.conf_client.set_string('server',
                                             host)
            else:
                sys.exit(0)
    
    def stop_gnome_screensaver(self):
        try:
            import dbus
            s = dbus.SessionBus()
            services = s.get_object('org.freedesktop.DBus',
                                    '/org/freedesktop/DBus').ListNames()
    
            if not "org.gnome.ScreenSaver" in services:
                return
        
            s.get_object("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver").Quit()
        except:
            pass
    
    def run(self):
        
        app = main.Client()
        self.stop_gnome_screensaver()
        
        try:
            gtk.threads_init()
            gtk.main()
        except:
            pass
        

if __name__ == "__main__":
    app = TeleCentros()
    app.run()
