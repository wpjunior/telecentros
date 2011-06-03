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
import time
import logging
import gtk
import gobject
import subprocess
from TeleCentros.ConfigClient import get_default_client

from TeleCentros.ui import icons
from TeleCentros.globals import *
from TeleCentros.utils import md5_cripto, kill_process
from TeleCentros.utils import get_os, humanize_time
from TeleCentros.ui import dialogs, login
from TeleCentros.ui.utils import get_gtk_builder
from TeleCentros.logout_actions import ActionManager
from TeleCentros.script_actions import ScriptManager
from TeleCentros.utils import HttpDownload
from TeleCentros.get_macaddr import get_route_mac_address
from TeleCentros.jsonrequester import JSONRequester
from TeleCentros.httpproxy import ProxySetter

try:
    import pynotify
except:
    pynotify = None

# Check DBus
try:
    from TeleCentros.dbus_manager import DbusManager
except ImportError:
    
    def gambiarra_caller(*args):
        pass
    
    #gambiarra
    class DbusManager:
        def __init__(self, *args, **kwargs):
            pass
        
        def __getattr__(self, *args):
            return gambiarra_caller
        
        def __setattr__(self, *args):
            pass

from os import remove
from os import path as ospath
_ = gettext.gettext

class Client:
    locked = False
    informations = {}
    visible = False
    update_time_handler_id = 0
    cleanup_apps_id = 0
    cleanup_apps_timeout = 30
    interative = True
    login_attempts = 0
    blocked = True
    
    limited = False
    registred = False
    os_name = ""
    os_version = ""
    sign_url = None
    cleanup_apps = []
    notification = None
    
    def __init__(self):
        
        self.logger = logging.getLogger('client.main')
        self.conf_client = get_default_client()
        self.dbus_manager = DbusManager(self)
        self.script_manager = ScriptManager()
        self.proxy_setter = ProxySetter()

        if pynotify and not pynotify.is_initted():
            pynotify.init('telecentros')

        # Get operating system version
        o = get_os()
        if o[0]:
            self.os_name = o[0]
        if o[1]:
            self.os_version = o[1]
        
        self.mac_id = get_route_mac_address()
        self.server = self.conf_client.get_string('server')
        self.port = self.conf_client.get_int('port')
        
        if not self.port:
            self.port = 80
    
        self.json_requester = JSONRequester(self.server, self.port)
        self.json_requester.run()
        self.json_requester.request('POST', {'cmd': 'identify', 'mac': self.mac_id, 'os_name': self.os_name,
                                             'os_version': self.os_version},
                                    self.on_identify_response, None)
        
        #icons
        self.icons = icons.Icons()
        self.logo = self.icons.get_icon(CLIENT_ICON_NAME)
        
        #MainWindow
        self.xml = get_gtk_builder('main')
        self.main_window = self.xml.get_object('window')
        self.time_str = self.xml.get_object('time_str')
        self.elapsed_pb = self.xml.get_object('elapsed_pb')
        self.remaining_pb = self.xml.get_object('remaining_pb')
        self.full_name = self.xml.get_object('full_name')
        self.tray_menu = self.xml.get_object('tray_menu')
        self.show_window_menu = self.xml.get_object('show_window_menu')
        
        self.main_window.set_icon_name('telecentros')
        self.main_window.show()
        
        self.visible = True
        self.show_window_menu.set_active(True)
        
        self.xml.connect_signals(self)
        
        #Tray
        self.tray_icon = gtk.status_icon_new_from_icon_name("telecentros")
        self.tray_icon.set_tooltip(_("TeleCentros"))
        
        self.tray_icon.connect('popup-menu', self.on_tray_popup_menu)
        self.tray_icon.connect('activate', self.on_show_hide)
        
        #Login Window
        self.login_window = login.Login(self)
        self.login_window.run()
            
    def on_window_delete_event(self, *args):
        self.on_show_hide(None)
        return True
    
    def on_show_hide(self, obj):
        
        if obj == self.show_window_menu:
            if self.visible != obj.get_active():
                if self.visible:
                    self.visible = False
                    self.main_window.hide()
                else:
                    self.visible = True
                    self.main_window.show()

        else:
            if self.visible:
                self.visible = False
                self.show_window_menu.set_active(False)
                self.main_window.hide()
            else:
                self.visible = True
                self.show_window_menu.set_active(True)
                self.main_window.show()
    
    def on_tray_popup_menu(self, obj, button, event):
        self.tray_menu.popup(None, None, None, button, event)
    
    def on_about_menuitem_activate(self, obj):
        dialogs.about(self.logo, self.main_window)
        
    def reset_widgets(self):
        self.full_name.set_text("")
        self.elapsed_pb.set_text("")
        self.elapsed_pb.set_fraction(0.0)
        self.remaining_pb.set_text("")
        self.remaining_pb.set_fraction(0.0)
    
    def do_cleanup_timeout(self):
        self.cleanup_apps_timeout -= 1

        if self.cleanup_apps_timeout == 0:
            if self.login_window.iterable_timeout_id == 0: #check
                self.login_window.set_warn_message("")

                for a in self.cleanup_apps:
                    kill_process(a) # Kill process

            self.cleanup_apps_id = 0
            return
        
        if self.login_window.iterable_timeout_id == 0: #check
            msg = (_("Closing applications in %0.2d seconds") % (self.cleanup_apps_timeout + 1))

            if msg:
                self.login_window.set_warn_message(msg)

        self.cleanup_apps_id = gobject.timeout_add_seconds(1,
                                                           self.do_cleanup_timeout)

    def block(self, after_action=0, cleanup_apps=[]):

        self.script_manager.pre_block()

        self.blocked = True
        self.elapsed_time = 0
        self.left_time = 0
        self.limited = False
        self.registred = False
        self.update_time = None
        self.time = 0
        self.reset_widgets()
        
        self.login_window.lock()
        self.stop_monitory_status()
        self.dbus_manager.block()
        
        if cleanup_apps:
            self.cleanup_apps = cleanup_apps
            self.cleanup_apps_timeout = 30
            self.do_cleanup_timeout()
        
        self.script_manager.pos_block()

        if not ActionManager:
            return

        if after_action == 1 : #shutdown
            ActionManager.shutdown()
            
        elif after_action == 2: #reboot
            ActionManager.reboot()
            
        elif after_action == 3: #logout
            ActionManager.logout()

        elif after_action == 4: #quit application
            gtk.main_quit()
    
    def unblock(self, time):
        # Execute a pre unblock script
        self.script_manager.pre_unblock()
        self.blocked = False
        self.reset_widgets()
        self.elapsed_time = 0
        self.left_time = 0
        self.update_time = None
        self.time = time
        
        self.show_window_menu.set_active(True)
        self.main_window.show()

        if self.time:
            time_str = "%0.2d:%0.2d:%0.2d" % humanize_time(self.time)
            self.time_str.set_text(time_str)
        else:
            self.time_str.set_text(_("Unlimited"))
        
        if self.cleanup_apps_id > 0:
            gobject.source_remove(self.cleanup_apps_id)
            self.cleanup_apps_id = 0

        self.start_monitory_status()
        self.login_window.unlock(None)

        # execute a pos unblock script
        self.script_manager.pos_unblock()
    
    def check_more_time(self):
        self.json_requester.request('POST', {'cmd': 'check_time', 'mac': self.mac_id},
                                    self.on_check_time_response, None)

    def on_check_time_response(self, response):

        if response.error:
            self.block()
            return

        if response.json_data:
            obj = response.json_data

            if not obj:
                self.block()
                return

        if response.json_data:
            obj = response.json_data
            if not obj:
                self.block()
                return
        
            logout = True
            if obj.has_key('logout'):
                logout = bool(obj['logout'])
            
            clean_apps = []
            if obj.has_key('clean_apps'):
                clean_apps = obj['clean_apps']

            after_action = 0
            if obj.has_key('after_action'):
                after_action = int(obj['after_action'])

            if logout:
                self.block(after_action, cleanup_apps=clean_apps)
                return

            if obj.has_key('time') and obj['time']:
                rtime = int(obj['time'])
            else:
                rtime = None

            self.start_time = time.time()
            self.unblock(rtime)

            if obj.has_key('full_name') and obj['full_name']:
                self.full_name.set_text(obj['full_name'].strip())
                self.dbus_manager.full_name_changed(obj['full_name'].strip())

            if obj.has_key('http_proxy') and obj['http_proxy']:
                self.set_proxy(obj['http_proxy'])
            else:
                self.proxy_setter.unset()

    def update_time_status(self):
        now = int(time.time())
  
        melapsed_time = now - self.start_time
        self.dbus_manager.elapsed_time_changed(melapsed_time)
        time_elapsed_str = "%0.2d:%0.2d:%0.2d" % humanize_time(melapsed_time)
        
        if self.time:
            mleft_time = self.time - melapsed_time

            if mleft_time <= 0:
                self.check_more_time()
                return

            

            self.dbus_manager.left_time_changed(mleft_time)
            time_left_str = "%0.2d:%0.2d:%0.2d" % humanize_time(mleft_time)
            time_left_per = float(mleft_time) / float(self.time)
            time_elapsed_per = float(melapsed_time) / float(self.time)
            if time_left_per <= 0.1 and pynotify: #TODO: Change
                if not self.notification:
                    self.notification = pynotify.Notification(_("Time is running out"),
                                                              _("With just %s\n"
                                                                "Save your work session that soon will be finalized") % time_left_str,
                                                              "dialog-warning")
                    self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
                    self.notification.set_timeout(1000)
                    self.notification.attach_to_status_icon(self.tray_icon)
                    self.notification.show()
                else:
                    self.notification.update(_("Time is running out"),
                                             _("With just %s\n"
                                               "Save your work session that soon will be finalized") % time_left_str,
                                             "dialog-warning")
                    self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
                    self.notification.set_timeout(1000)
                    self.notification.show()

        else:
            time_left_str = _("None")
            time_left_per = 0
            time_elapsed_per = 0
        
        self.elapsed_pb.set_text(time_elapsed_str)
        self.elapsed_pb.set_fraction(time_elapsed_per)
        self.remaining_pb.set_text(time_left_str)
        self.remaining_pb.set_fraction(time_left_per)

        
        self.update_time_handler_id = gobject.timeout_add(1000,
                                        self.update_time_status)
        
    def start_monitory_status(self):
        self.update_time_status()
    
    def stop_monitory_status(self):
        if self.update_time_handler_id:
            gobject.source_remove(self.update_time_handler_id)

    def on_identify_response_timeout(self):
        self.json_requester.request('POST', {'cmd': 'identify', 'mac': self.mac_id, 'os_name': self.os_name,
                                             'os_version': self.os_version},
                                    self.on_identify_response, None)

    def on_identify_response(self, response):
        self.login_window.set_lock_all(False)

        if response.error:
            self.login_window.err_box.set_text(str(response.error))
            gobject.timeout_add(30000, self.on_identify_response_timeout)
            return

        if response.json_data:
            obj = response.json_data

            if not obj:
                self.login_window.err_box.set_text(_("Bad Response"))
                gobject.timeout_add(30000, self.on_identify_response_timeout)
                return

            if obj.has_key('name') and obj['name']:
                self.login_window.set_title(obj['name'])

            if obj.has_key('welcome_msg') and obj['welcome_msg']:
                self.login_window.set_welcome_msg(obj['welcome_msg'])

            if obj.has_key('sign_url') and obj['sign_url']:
                self.sign_url = obj['sign_url']
                self.login_window.register_bnt.set_sensitive(True)
            else:
                self.sign_url = None #explict
                self.login_window.register_bnt.set_sensitive(False)

            if obj.has_key('background_url') and obj['background_url']:
                err = self.get_background(obj['background_url'])
                if err:
                    print err
                else:
                    self.login_window.set_background(BACKGROUND_CACHE)
            else:
                self.login_window.set_background(None)

            if obj.has_key('logo_url') and obj['logo_url']:
                err = self.get_logo(obj['logo_url'])
                if err:
                    print err
                else:
                    self.login_window.set_logo(LOGO_CACHE)
            else:
                self.login_window.set_logo(None)

    def on_logout_response(self, response):

        if response.error:
            dlg = dialogs.ok_only(text=str(response.error), ICON=gtk.MESSAGE_ERROR)
            dlg.show()
            return

        if response.json_data:
            obj = response.json_data

            if not obj:
                return

            error = None
            if obj.has_key('error'):
                error = obj['error']

            if error:
                dlg = dialogs.ok_only(text=error, ICON=gtk.MESSAGE_ERROR)
                dlg.show()
                return

            clean_apps = []
            if obj.has_key('clean_apps'):
                clean_apps = obj['clean_apps']

            after_action = 0
            if obj.has_key('after_action'):
                after_action = int(obj['after_action'])

            self.block(after_action, cleanup_apps=clean_apps)

    def on_login_response(self, response):
        self.login_window.set_lock_all(False)

        if response.error:
            self.login_window.set_current(login.LOGIN_USER)
            self.login_window.err_box.set_text(str(response.error))
            return

        if response.json_data:
            obj = response.json_data
            if not obj:
                self.login_window.set_current(login.LOGIN_USER)
                self.login_window.err_box.set_text(_("Bad Response"))
        
            if obj.has_key('authenticated'):
                auth = bool(obj['authenticated'])

            if obj.has_key('error') and obj['error']:
                self.login_attempts += 1
                self.login_window.set_current(login.LOGIN_USER)
                self.login_window.err_box.set_text(obj['error'])

            if obj.has_key('time') and obj['time']:
                rtime = int(obj['time'])
            else:
                rtime = None

            up_apps = None
            if obj.has_key('up_apps') and obj['up_apps']:
                up_apps = obj['up_apps']

            if auth:
                self.start_time = time.time()
                self.login_attempts = 0
                self.unblock(rtime)

                if up_apps:
                    self.start_apps(up_apps)

            if obj.has_key('full_name') and obj['full_name']:
                self.full_name.set_text(obj['full_name'])
                self.dbus_manager.full_name_changed(obj['full_name'])

            if obj.has_key('http_proxy') and obj['http_proxy']:
                self.set_proxy(obj['http_proxy'])
            else:
                self.proxy_setter.unset()
        
        if self.login_attempts >= 3:
            self.login_window.set_lock_all(True)
            self.login_window.on_ready_run_interable = True
            self.login_window.on_ready = 60
            
            if self.login_window.iterable_timeout_id:
                gobject.source_remove(self.login_window.iterable_timeout_id)
            
            self.login_window.on_ready_iterable()

        self.login_window.set_current(login.LOGIN_USER)

    def set_proxy(self, obj):
        if obj.has_key('username'):
            self.proxy_setter.username = obj['username'].strip()

        if obj.has_key('password'):
            self.proxy_setter.password = obj['password'].strip()

        if obj.has_key('host'):
            self.proxy_setter.host = obj['host'].strip()

        if obj.has_key('port'):
            self.proxy_setter.port = int(obj['port'])

        self.proxy_setter.set()
        
    def on_login(self, username, password):
        self.login_window.set_lock_all(True)
        self.json_requester.request('POST', {'cmd': 'login', 'mac': self.mac_id, 'username':username, 'password': password},
                                    self.on_login_response, None)
        
    
    def on_logout_menuitem_activate(self, obj):
        dlg = gtk.MessageDialog(parent=self.main_window,
                                type=gtk.MESSAGE_QUESTION,
                                buttons=gtk.BUTTONS_YES_NO)
        
        dlg.set_markup(_("<big><b>Are you sure you want to Log out "
                         "of this system now?</b></big>\n\n"
                         "If you Log out, unsaved work will be lost."))
        response = dlg.run()
        dlg.destroy()
        
        if response == gtk.RESPONSE_YES:
            self.json_requester.request('POST', {'cmd': 'logout', 'mac': self.mac_id},
                                        self.on_logout_response, None)

    def get_background(self, url):
        downloader = HttpDownload()
        e = downloader.run(url, directory=CACHE_PATH, fn="wallpaper")
        return e
    
    def get_logo(self, url):
        downloader = HttpDownload()
        e = downloader.run(url, directory=CACHE_PATH, fn="logo")
        return e

    def start_apps(self, apps):
        for app in apps:
            if not isinstance(app, list):
                app = [app]

            for i in range(len(app)): #hack set str
                app[i] = str(app[i])
                
            po = subprocess.Popen(app, stdin=None, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
            print 'start', app, po
