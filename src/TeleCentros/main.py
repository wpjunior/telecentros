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
    
    name = None
    description = None
    locked = False
    informations = {}
    other_info = {}
    logo_md5 = None
    background_md5 = None
    visible = False
    monitory_handler_id = 0
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
    
    def __init__(self):
        
        self.logger = logging.getLogger('client.main')
        self.conf_client = get_default_client()
        self.dbus_manager = DbusManager(self)
        self.script_manager = ScriptManager()
        
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
        
        self.main_window.show()
        self.visible = True
        self.show_window_menu.set_active(True)

        self.show_informations(True)
        self.show_time_elapsed(True)
        self.show_time_remaining(True)
        
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
    
    def set_myinfo(self, data):
        if data.has_key('name'):
            self.name = data['name']
            self.dbus_manager.host_name_changed(self.name)
            
            if 'welcome_msg' in self.informations:
                self.login_window.set_title(
                    self.informations['welcome_msg'].replace("%n", self.name)
                    )
            
            self.logger.debug('My host name is "%s"' % data['name'])
            
        
        if data.has_key('description'):
            self.description = data['description']
            self.dbus_manager.description_changed(self.description)
            self.logger.debug('My host description is "%s"' % data['description'])
    
    def set_information(self, data):
        assert isinstance(data, dict)
        
        for key in data:
            self.informations[key] = data[key]
        
        if 'welcome_msg' in data:
            self.login_window.set_title(
                    self.informations['welcome_msg'].replace("%n", self.name)
                    )
            self.dbus_manager.welcome_msg_changed(self.informations['welcome_msg'])
        
        if 'default_welcome_msg' in data:
            if data['default_welcome_msg']:
                self.login_window.set_title(_('Welcome'))
                self.dbus_manager.welcome_msg_changed(_('Welcome'))
            else:
                self.login_window.set_title(
                       self.informations['welcome_msg'].replace("%n", self.name)
                       )
                self.dbus_manager.welcome_msg_changed(self.informations['welcome_msg'])
        
        if 'currency' in data:
            self.currency = data['currency']
            self.dbus_manager.currency_changed(self.currency)
        
        if 'use_background' in data:
            if data['use_background']:
                self.login_window.set_background(BACKGROUND_CACHE)
            else:
                self.login_window.set_background(None)
        
        if 'use_logo' in data:
            if data['use_logo']:
                self.login_window.set_logo(LOGO_CACHE)
            else:
                self.login_window.set_logo(None)

        print self.informations
        
    def reset_widgets(self):
        self.full_name.set_text("")
        self.elapsed_pb.set_text("")
        self.elapsed_pb.set_fraction(0.0)
        self.remaining_pb.set_text("")
        self.remaining_pb.set_fraction(0.0)
        self.other_info = {}
    
    def do_cleanup_timeout(self):
        self.cleanup_apps_timeout -= 1

        if 'finish_action' in self.informations:
            action = self.informations['finish_action']
        else:
            action = 0

        if self.cleanup_apps_timeout == 0:
            if self.login_window.iterable_timeout_id == 0: #check
                self.login_window.set_warn_message("")

            if ((action == 1) and ('close_apps_list' in self.informations)):
                for a in self.informations['close_apps_list']:
                    kill_process(a) # Kill process
            
            if ((action == 2) and (ActionManager)):
                ActionManager.logout()

            self.cleanup_apps_id = 0
            return
        
        if self.login_window.iterable_timeout_id == 0: #check
            if (action == 1):
                msg = (_("Closing applications in %0.2d seconds") % (self.cleanup_apps_timeout + 1))
            elif (action == 2):
                msg = (_("Closing desktop session in %0.2d seconds") % (self.cleanup_apps_timeout + 1))
            else:
                msg = None

            if msg:
                self.login_window.set_warn_message(msg)

        self.cleanup_apps_id = gobject.timeout_add_seconds(1,
                                                           self.do_cleanup_timeout)

    def block(self, after, action, cleanup_apps=True):

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
        
        if 'finish_action' in self.informations and 'finish_action_time' in self.informations:
            if self.informations['finish_action'] and cleanup_apps:
                self.cleanup_apps_timeout = self.informations['finish_action_time']
                self.do_cleanup_timeout()
        
        self.script_manager.pos_block()

        if not ActionManager:
            return

        if not after:
            return

        if action == 0 : #shutdown
            ActionManager.shutdown()
            
        elif action == 1: #reboot
            ActionManager.reboot()
            
        elif action == 2: #logout
            ActionManager.logout()
    
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
        self.show_informations(True)
        self.show_time_elapsed(True)
        self.show_time_remaining(True)

        if self.time:
            time_str = "%0.2d:%0.2d:%0.2d" % humanize_time(self.time)
            self.time_str.set_text(time_str)
        else:
            self.time_str.set_text(_("Unlimited"))
        """
        if self.cleanup_apps_id > 0:
            gobject.source_remove(self.cleanup_apps_id)
            self.cleanup_apps_id = 0

        if 'limited' in data and 'registred' in data:
            self.limited = data['limited']
            self.registred = data['registred']
            
            self.dbus_manager.unblock((int(data['registred']), 
                                       int(data['limited'])))
        
        if 'time' in data:
            self.time = data['time']
            self.dbus_manager.time_changed(data['time'])
        
        if 'registred' in data:
            if data['registred']:
                self.xml.get_object("information_vbox").show()
                self.xml.get_object("information_menuitem").set_sensitive(True)
            else:
                self.xml.get_object("information_vbox").hide()
                self.xml.get_object("information_menuitem").set_sensitive(False)
        
        if 'limited' in data:
            self.xml.get_object("remaining_label").set_property('visible', bool(data['limited']))
            self.xml.get_object("remaining_pb").set_property('visible', bool(data['limited']))
            self.xml.get_object("time_remaining_menuitem").set_property('sensitive', bool(data['limited']))
        """
        self.start_monitory_status()
        self.login_window.unlock(None)

        # execute a pos unblock script
        self.script_manager.pos_unblock()
    
    def dispatch(self, method, params):
        
        if method == 'core.get_hash_id':
            return self.hash_id
            
        elif method == 'main.set_myinfo':
            self.set_myinfo(*params)
            return True
        
        elif method == 'core.set_information':
            self.set_information(*params)
            return True
        
        elif method == 'core.unblock':
            self.unblock(*params)
            return True
        
        elif method == 'core.block':
            self.block(*params)
            return True
        
        elif method == 'set_status':
            self.set_status(*params)
            return True
        
        elif method == 'system.shutdown':
            self.system_shutdown()
            return True
            
        elif method == 'system.reboot':
            self.system_reboot()
            return True
        
        elif method == 'system.logout':
            self.system_logout()
            return True
        
        elif method == 'app.quit':
            self.app_quit()
            return True
        
        elif method == 'main.set_background_md5':
            self.set_background_md5(*params)
        
        elif method == 'main.set_logo_md5':
            self.set_logo_md5(*params)
        
        else:
            print method, params
            return True

    def check_more_time(self):
        self.json_requester.request('POST', {'cmd': 'check_time', 'mac': self.mac_id},
                                    self.on_check_time_response, None)

    def on_check_time_response(self, response):

        if response.error:
            self.block(0, 0)
            return

        if response.json_data:
            obj = response.json_data

            if not obj:
                self.block(0, 0)
                return

        if response.json_data:
            obj = response.json_data
            if not obj:
                self.block(0, 0)
                return
        
            logout = True
            if obj.has_key('logout'):
                logout = bool(obj['logout'])
            
            clean_apps = True
            if obj.has_key('clean_apps'):
                clean_apps = bool(obj['clean_apps'])

            if logout:
                self.block(0, 0, cleanup_apps=clean_apps) #TODO: implement shutdown
                return

            if obj.has_key('time') and obj['time']:
                rtime = int(obj['time'])
            else:
                rtime = None

            self.start_time = time.time()
            self.unblock(rtime)

            if obj.has_key('full_name') and obj['full_name']:
                self.full_name.set_text(obj['full_name'])
                self.dbus_manager.full_name_changed(obj['full_name'])

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
    
    def monitory_status(self):
        print "TODO: GET STATUS ??"
        #request = self.netclient.request('get_status')
        #request.connect("done", self.on_get_status_request_done)
        self.monitory_handler_id = gobject.timeout_add(120000,
                                        self.monitory_status)
        
    def start_monitory_status(self):
        self.update_time_status()
        self.monitory_status()
    
    def stop_monitory_status(self):
        if self.monitory_handler_id:
            gobject.source_remove(self.monitory_handler_id)
        if self.update_time_handler_id:
            gobject.source_remove(self.update_time_handler_id)
    """
    def set_status(self, data):
        for key in data:
            self.other_info[key] = data[key]
        
        if 'time' in data and 'left_time' in data and 'elapsed' in data:
            self.update_time = int(time.time())
        
        if 'time' in data:
            assert len(data['time']) == 2
            assert self.limited
            self.time = data['time']
            self.mtime = ((self.time[0] * 3600) + self.time[1] * 60)
            time_str = "%0.2d:%0.2d" % tuple(self.time)
            self.time_str.set_text(time_str)
            self.dbus_manager.time_changed(self.time)
        
        if 'left_time' in data:
            assert self.limited
            self.left_time = data['left_time']
        
        if 'elapsed' in data:
            self.elapsed_time = data['elapsed']
        
    def on_get_status_request_done(self, request, value):
        self.update_time = int(time.time())
        self.limited = value['limited']
        self.elapsed_time = value['elapsed']
        
        if self.limited:
            self.left_time = value['left_time']
            self.time = value['time']
            self.mtime = ((self.time[0] * 3600) + self.time[1] * 60)
            
            assert len(value['time']) == 2
            time_str = "%0.2d:%0.2d" % tuple(self.time)
        else:
            self.left_time = None
            self.time = None
            self.mtime = None
            time_str = _("Unlimited")
        
        self.time_str.set_text(time_str)
    """
    def show_informations(self, status):
        self.interative = False
        self.xml.get_object("information_vbox").set_property('visible', status)
        self.xml.get_object("information_menuitem").set_active(status)
        self.interative = True
    
    def show_time_elapsed(self, status):
        self.interative = False
        self.xml.get_object("elapsed_label").set_property('visible', status)
        self.xml.get_object("elapsed_pb").set_property('visible', status)
        self.xml.get_object("time_elapsed_menuitem").set_active(status)
        self.interative = True
    
    def show_time_remaining(self, status):
        self.interative = False
        self.xml.get_object("remaining_label").set_property('visible', status)
        self.xml.get_object("remaining_pb").set_property('visible', status)
        self.xml.get_object("time_remaining_menuitem").set_active(status)
        self.interative = True
    
    def on_information_toggled(self, obj):
        if self.interative:
            self.show_informations(obj.get_active())
        
    def on_time_elapsed_toggled(self, obj):
        if self.interative:
            self.show_time_elapsed(obj.get_active())
    
    def on_time_remaining_toggled(self, obj):
        if self.interative:
            self.show_time_remaining(obj.get_active())

    def on_identify_response(self, response):
        self.login_window.set_lock_all(False)

        if response.error:
            self.login_window.err_box.set_text(str(response.error))
            #TODO: re-connect in 1 min
            return

        if response.json_data:
            obj = response.json_data

            if not obj:
                self.login_window.err_box.set_text(_("Bad Response"))
                return
                #TODO: re-connect in 1 min

            if obj.has_key('name') and obj['name']:
                self.login_window.set_title(obj['name'])

            if obj.has_key('welcome-msg') and obj['welcome-msg']:
                self.login_window.set_welcome_msg(obj['welcome-msg'])

            if obj.has_key('sign-url') and obj['sign-url']:
                self.sign_url = obj['sign-url']
                self.login_window.register_bnt.set_sensitive(True)
            else:
                self.sign_url = None #explict
                self.login_window.register_bnt.set_sensitive(False)

            if obj.has_key('background-url') and obj['background-url']:
                err = self.get_background(obj['background-url'])
                if err:
                    print err
                else:
                    self.login_window.set_background(BACKGROUND_CACHE)
            else:
                self.login_window.set_background(None)

            if obj.has_key('logo-url') and obj['logo-url']:
                err = self.get_logo(obj['logo-url'])
                if err:
                    print err
                else:
                    self.login_window.set_logo(LOGO_CACHE)
            else:
                self.login_window.set_logo(None)

    def on_logout_response(self, response):
        print 'on_logout', response
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

            clean_apps = True
            if obj.has_key('clean_apps'):
                clean_apps = bool(obj['clean_apps'])

            self.block(0, 0, cleanup_apps=clean_apps)

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

            if auth:
                self.start_time = time.time()
                self.login_attempts = 0
                self.unblock(rtime)

            if obj.has_key('full_name') and obj['full_name']:
                self.full_name.set_text(obj['full_name'])
                self.dbus_manager.full_name_changed(obj['full_name'])
        
        if self.login_attempts >= 3:
            self.login_window.set_lock_all(True)
            self.login_window.on_ready_run_interable = True
            self.login_window.on_ready = 60
            
            if self.login_window.iterable_timeout_id:
                gobject.source_remove(self.login_window.iterable_timeout_id)
            
            self.login_window.on_ready_iterable()

        self.login_window.set_current(login.LOGIN_USER)
        
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

    def system_shutdown(self):
        if not ActionManager:
            return
        
        ActionManager.shutdown()

    def system_reboot(self):
        if not ActionManager:
            return
        
        ActionManager.reboot()

    def system_logout(self):
        if not ActionManager:
            return
        
        ActionManager.logout()

    def app_quit(self):
        gtk.main_quit()
        
    def get_background(self, url):
        downloader = HttpDownload()
        e = downloader.run(url, directory=CACHE_PATH, fn="wallpaper")
        return e
    
    def get_logo(self, url):
        downloader = HttpDownload()
        e = downloader.run(url, directory=CACHE_PATH, fn="logo")
        return e

        

        
