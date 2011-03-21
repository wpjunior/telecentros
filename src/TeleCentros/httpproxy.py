#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2008-2011 Wilson Pinto Júnior <wilsonpjunior@gmail.com>
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

import gconf
gconf_client = gconf.client_get_default()

SYSTEM_HTTP = '/system/http_proxy/'

class ProxySetter:
    username = ""
    password = ""
    host = ""
    port = 8080

    def set(self):
        gconf_client.set_string(SYSTEM_HTTP + 'authentication_user',
                                self.username)
        gconf_client.set_string(SYSTEM_HTTP + 'authentication_password',
                                self.password)
        gconf_client.set_string(SYSTEM_HTTP + 'host',
                                self.host)
        gconf_client.set_int(SYSTEM_HTTP + 'port', self.port)


        gconf_client.set_string("/system/proxy/secure_host", self.host)
        gconf_client.set_int("/system/proxy/secure_port", self.port)

        gconf_client.set_bool(SYSTEM_HTTP + 'use_authentication', True)
        gconf_client.set_bool(SYSTEM_HTTP + 'use_http_proxy', True)

        gconf_client.set_string("/system/proxy/mode", "manual")

    def unset(self):
        params = ('authentication_user', 'authentication_password', 'host',
                  'port', 'use_authentication', 'use_http_proxy')

        for p in params:
            gconf_client.unset(SYSTEM_HTTP + p)

        gconf_client.unset("/system/proxy/secure_host")
        gconf_client.unset("/system/proxy/secure_port")

        gconf_client.set_string("/system/proxy/mode", "none")

if __name__ == "__main__":
    p = ProxySetter()
    p.username = "wilson"
    p.password = "123"
    p.host = "corumbatur.com.br"
    p.port = 1565

    p.set()
    p.unset()
