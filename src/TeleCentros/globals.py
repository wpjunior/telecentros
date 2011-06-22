#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2008-2009 Wilson Pinto Júnior <wilson@openlanhouse.org>
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import locale
import gettext

from os import path as ospath
from os import name as osname

from TeleCentros.config import *

SHARE_PATH = ospath.join(PREFIX, 'share', 'TeleCentros')
LOCALE_PATH = ospath.join(PREFIX, 'share', 'locale')

if INSTALLED:
    CUR_PATH = SHARE_PATH
else:
    _rootpath = ospath.join(ospath.dirname(__file__), '../../')
    _abspath = ospath.abspath(_rootpath)
    CUR_PATH = ospath.join(_abspath, 'data')

##Folder paths
UI_PATH = ospath.join(CUR_PATH, 'ui')
ICON_PATH = ospath.join(CUR_PATH, 'icons')
STATUS_ICON_PATH = ospath.join(ICON_PATH, 'status')

USER_PATH = ospath.expanduser('~')

CONFIG_PREFIX = ospath.join(USER_PATH, '.config')
CONFIG_PATH = ospath.join(CONFIG_PREFIX, 'TeleCentros')
CONFIG_FILE = ospath.join(CONFIG_PATH, "telecentros.ini")
CERTS_PATH = ospath.join(CONFIG_PATH, 'certs')
CACHE_PATH = ospath.join(CONFIG_PATH, 'cache')

DBUS_INTERFACE = 'org.gnome.TeleCentros'
DBUS_PATH = '/org/gnome/TeleCentros'

BACKGROUND_CACHE = ospath.join(CACHE_PATH, 'wallpaper')
LOGO_CACHE = ospath.join(CACHE_PATH, 'logo')

##CLIENT FILES
##CONFIG FILES
CONFIG_CLIENT = ospath.join(CONFIG_PATH, 'telecentros.conf')
CLIENT_PID_FILE = ospath.join(CONFIG_PATH, 'telecentros.lock')

##CLIENT TLS FILES
CLIENT_TLS_KEY = ospath.join(CERTS_PATH, 'telecentros.key')
CLIENT_TLS_CERT = ospath.join(CERTS_PATH, 'telecentros.cert')
CLIENT_TLS_TEMPLATE = ospath.join(CERTS_PATH, 'telecentros.template')

##Icons
CLIENT_ICON_NAME = 'telecentros'

##APP
APP_NAME = 'Cliente Telecentros'
APP_SITE = 'http://www.lethus.com.br'
APP_COPYRIGHT = 'Telecentros - Tethus TI'

I18N_APP = 'telecentros'

##Internacionalize
locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(I18N_APP, LOCALE_PATH)
gettext.textdomain(I18N_APP)

_ = gettext.gettext

language = locale.setlocale(locale.LC_ALL, '')
end = language.find('.')
language = language[:end]
##End internacionalize

##APP Proprerties
APP_COMMENTS = None
CLIENT_APP_NAME = _('OpenLanHouse - Client')

MIN_NICK = 4
MAX_NICK = 20
MIN_PASSWORD = 5
MAX_PASSWORD = 32
PREVIEW_SIZE = 200

DEFAULT_PATH = '/telecentros/proxy/'
#PORT CONF
SERVER_PORT = 4558
MAX_CHUNK_SIZE = 10485760

#COLORS
COLOR_YELLOW = '#FCE94F'
COLOR_RED = '#EF2929'

APP_DOCS = ('Wilson Pinto Júnior <wpjunior@lethus.com.br>',)

APP_AUTHORS = ('Wilson Pinto Júnior <wpjunior@lethus.com.br>',)
APP_ARTISTS = ""


APP_CONTRIB = ()

APP_TRANSLATORS = ""

APP_LICENCE = _('TeleCentros Client is free software: you can redistribute it and/or modify\n'
                'it under the terms of the GNU General Public License as published by\n'
                'the Free Software Foundation, either version 3 of the License, or\n'
                '(at your option) any later version.\n\n'
                'This program is distributed in the hope that it will be useful,\n'
                'but WITHOUT ANY WARRANTY; without even the implied warranty of\n'
                'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n'
                'GNU General Public License for more details.\n\n'
                'You should have received a copy of the GNU General Public License\n'
                'along with this program.  If not, see <http://www.gnu.org/licenses/>.'
                )
