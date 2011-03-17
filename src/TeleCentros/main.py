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
        
        #BACKGROUND MD5SUM
        if ospath.exists(BACKGROUND_CACHE): #TODO GET BACKGROUND 302
            try:
                assert ospath.getsize(BACKGROUND_CACHE) < 2500000L, "Large Background"
                self.background_md5 = md5_cripto(open(BACKGROUND_CACHE).read())
            except Exception, error:
                self.logger.error(error)
                self.background_md5 = None
        
        if self.background_md5:
            self.logger.info("Background Md5sum is %s" % self.background_md5)
        
        #LOGO MD5SUM
        if ospath.exists(LOGO_CACHE):
            try:
                assert ospath.getsize(LOGO_CACHE) < 2500000L, "Large Logo"
                self.logo_md5 = md5_cripto(open(LOGO_CACHE).read())
            except Exception, error:
                self.logger.error(error)
                self.logo_md5 = None
        
        self.mac_id = get_route_mac_address()
        self.server = self.conf_client.get_string('server')
        self.port = self.conf_client.get_int('port')
        
        if not self.port:
            self.port = 80
        
    
        self.json_requester = JSONRequester(self.server, self.port)
        self.json_requester.run()
        
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
        self.credit = self.xml.get_object('credit')
        self.total_to_pay = self.xml.get_object('total_to_pay')
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
        self.tray_icon = gtk.status_icon_new_from_icon_name("openlh-client")
        self.tray_icon.set_tooltip(_("OpenLanhouse - Client"))
        
        self.tray_icon.connect('popup-menu', self.on_tray_popup_menu)
        self.tray_icon.connect('activate', self.on_show_hide)
        
        #Login Window
        self.login_window = login.Login(self)
        self.login_window.run()
        
        #if not self.netclient.start():
        #    self.login_window.set_connected(False)
    
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
    
    def send_myos(self):
        self.netclient.request("set_myos", (self.os_name, self.os_version))
        
    def connected(self, obj, server):
        self.login_window.set_connected(True)
        gobject.timeout_add(10000,
                            self.send_myos)
        
    def disconnected(self, obj):
        self.block(False, 0)
        self.login_window.set_connected(False)
        
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
        self.credit.set_text("")
        self.full_name.set_text("")
        self.total_to_pay.set_text("")
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
        self.time = (0, 0)
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
    
    def unblock(self):
        # Execute a pre unblock script
        self.script_manager.pre_unblock()
        self.blocked = False
        self.reset_widgets()
        self.elapsed_time = 0
        self.left_time = 0
        self.update_time = None
        self.time = (0, 0)
        
        self.show_window_menu.set_active(True)
        self.main_window.show()
        self.show_informations(True)
        self.show_time_elapsed(True)
        self.show_time_remaining(True)
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

        self.start_monitory_status()
        """
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
    """ 
    def reload_network(self):
        self.netclient = NetClient(self.server, self.port,
                            CLIENT_TLS_CERT, CLIENT_TLS_KEY, self.hash_id)
        
        self.netclient.connect('connected', self.connected)
        self.netclient.connect('disconnected', self.disconnected)
        self.netclient.dispatch_func = self.dispatch
    """    
    def update_time_status(self):
        if not self.update_time:
            self.update_time_handler_id = gobject.timeout_add(1000, 
                                                self.update_time_status)
            return
        
        now = int(time.time())
        diff_secs = now - self.update_time
        melapsed_time = self.elapsed_time + diff_secs
        self.dbus_manager.elapsed_time_changed(melapsed_time)
        time_elapsed_str = "%0.2d:%0.2d:%0.2d" % humanize_time(melapsed_time)
        
        if self.limited:
            mleft_time = self.left_time - diff_secs
            self.dbus_manager.left_time_changed(mleft_time)
            time_left_str = "%0.2d:%0.2d:%0.2d" % humanize_time(mleft_time)
            time_left_per = float(mleft_time) / float(self.mtime)
            time_elapsed_per = float(melapsed_time) / float(self.mtime)
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
        request = self.netclient.request('get_status')
        request.connect("done", self.on_get_status_request_done)
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
    
    def set_status(self, data):
        for key in data:
            self.other_info[key] = data[key]
        
        if 'credit' in data:
            self.credit.set_text(
                    "%s %0.2f" % (self.currency, data['credit']))
            self.dbus_manager.credit_changed(data['credit'])
            self.dbus_manager.credit_changed_as_string("%s %0.2f" % 
                                        (self.currency, data['credit']))
        
        if 'full_name' in data:
            self.full_name.set_text(data['full_name'])
            self.dbus_manager.full_name_changed(data['full_name'])
        
        if 'total_to_pay' in data:
            ats = "%s %0.2f" % (self.currency, data['total_to_pay'])
            self.total_to_pay.set_text(ats)
            self.dbus_manager.total_to_pay_changed(data['total_to_pay'])
            self.dbus_manager.total_to_pay_changed_as_string(ats)
        
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
    
    def on_login_response(self, response):
        self.login_window.set_lock_all(False)

        if response.error:
            self.login_window.set_current(login.LOGIN_USER)
            self.login_window.err_box.set_text(str(response.error))
            #TODO: SHOW ERROR
            return

        if response.json_data:
            obj = response.json_data
            if not obj:
                self.login_window.set_current(login.LOGIN_USER)
                self.login_window.err_box.set_text(_("Bad Response"))
        
            if obj.has_key('authenticated'):
                if obj['authenticated']:
                    self.login_attempts = 0
                    self.unblock()
                    
            if obj.has_key('error') and obj['error']:
                self.login_attempts += 1
                self.login_window.set_current(login.LOGIN_USER)
                self.login_window.err_box.set_text(obj['error'])
        
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
        self.json_requester.request('POST', {'cmd': 'login', 'user':username, 'password': password},
                                    self.on_login_response, None) #TODO: Implement Session
        
    
    def on_logout_menuitem_activate(self, obj):
        dlg = gtk.MessageDialog(parent=self.main_window,
                                type=gtk.MESSAGE_QUESTION,
                                buttons=gtk.BUTTONS_YES_NO)
        
        dlg.set_markup(_("<big><b>Are you sure you want to Log out "
                         "of this system now?</b></big>\n\n"
                         "If you Log out, unsaved work will be lost."))
        response = dlg.run()
        dlg.destroy()
        
        #if response == gtk.RESPONSE_YES:
        #    self.netclient.request('logout')
            

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
    
    def set_background_md5(self, hash_md5):
        
        if self.background_md5 != hash_md5:
            e = self.get_background()
            
            if e:
                print e
                return
            
            try:
                assert ospath.getsize(BACKGROUND_CACHE) < 2500000L, "Large Background"
                self.background_md5 = md5_cripto(open(BACKGROUND_CACHE).read())
            except Exception, error:
                print error
                self.background_md5 = None
                return
        
        if ('use_background' in self.informations 
                    and self.informations['use_background']):
                self.login_window.set_background(BACKGROUND_CACHE)
        else:
            self.login_window.set_background(None)
        
    def set_logo_md5(self, hash_md5):
        if self.logo_md5 != hash_md5:
            e = self.get_logo()
            
            if e:
                print e
                return
            
            try:
                assert ospath.getsize(LOGO_CACHE) < 2500000L, "Large Logo"
                self.logo_md5 = md5_cripto(open(LOGO_CACHE).read())
            except Exception, error:
                print error
                self.logo_md5 = None
                return
        
        if ('use_logo' in self.informations 
                    and self.informations['use_logo']):
                self.login_window.set_logo(LOGO_CACHE)
        else:
            self.login_window.set_logo(None)
        
    def get_background(self):
        data = {'server': self.server, 
                'port': 4559,
                'mac_id': self.mac_id}
        
        url = "http://%(server)s:%(port)d/get_background/%(hash_id)s" % data
        
        downloader = HttpDownload()
        e = downloader.run(url,
                           directory=CACHE_PATH,
                           fn="wallpaper")
        
        return e
    
    def get_logo(self):
        data = {'server': self.server, 
                'port': 4559,
                'mac_id': self.mac_id}
        
        url = "http://%(server)s:%(port)d/get_logo/%(hash_id)s" % data
        
        downloader = HttpDownload()
        e = downloader.run(url,
                           directory=CACHE_PATH,
                           fn="logo")
        
        return e
        
