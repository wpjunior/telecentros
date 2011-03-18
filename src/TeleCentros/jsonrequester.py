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

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import gobject
import thread
import threading
import httplib
import urllib
import traceback
from time import sleep
import json
from TeleCentros.globals import DEFAULT_PATH

"""
* Request
b|Done
r|HttpRequest
"""

def threaded(f):
    """
        Threads Wrapper
    """
    def wrapper(*args):
        t = threading.Thread(target=f, args=args)
        t.setDaemon(True)
        t.start()
    wrapper.__name__ = f.__name__
    wrapper.__dict__ = f.__dict__
    wrapper.__doc__ = f.__doc__
    return wrapper

class Request:
    def __init__(self, method='GET', request_data={}, on_done=None, on_fail=None, *args, **kwargs):
        self.method = method
        self.request_data = request_data
        self.on_done = on_done
        self.on_fail = on_fail
        self.args = args
        self.kwargs = kwargs
        self.content_type = ''
        self.data = None
        self.json_data = None
        self.http = None
        self.error = None

class JSONRequester:
    def __init__ (self, host, port=None, path="/proxy/"):
        
        self.host = host
        self.port = port
        self.path = path
        self.requests = []
        self.responses = []
        self.fail_requests = []
        self.timeout_id = -1
        
    """ Iterates the default GLib main context until the download is done """

    def watch(self):
        self.timeout_id = gobject.timeout_add(500, self.wait_progress)
        self.wait_progress()

    def unwatch(self):
        gobject.source_remove(self.timeout_id)
        self.timeout_id = -1

    def run(self):
        self.thread_func()
        self.watch()

    def wait_progress(self):
        if len(self.responses) <= 0 and len(self.requests) <= 0 and len(self.fail_requests) <=0:
            self.unwatch()
            return False

        for response in self.responses:
            if response.on_done:
                try:
                    response.on_done(response, *response.args, **response.kwargs)
                except:
                    traceback.print_exc(file=sys.stdout)
            
            self.responses.remove(response)

        for response in self.fail_requests:
            try:
                if response.on_fail:
                    response.on_fail(response, *response.args, **response.kwargs)
                elif response.on_done:
                    response.on_done(response, *response.args, **response.kwargs)
            except:
                    traceback.print_exc(file=sys.stdout)
            
            self.fail_requests.remove(response)

        return True
    

    def request(self, method, data, on_done, on_fail, *args, **kwargs):
        request = Request(method, data, on_done, on_fail, *args, **kwargs)
        self.requests.append(request)

        if self.timeout_id < 0:
            self.watch()

    def process_request(self, request):
        try:
            conn = httplib.HTTPConnection(self.host, self.port, timeout=10)
            conn.request(request.method, self.path, urllib.urlencode(request.request_data))
        except Exception, e:
            request.error = e
            self.fail_requests.append(request)
            return

        request.http = conn.getresponse()
        request.content_type = request.http.getheader('content-type', '')
        request.data = request.http.read()

        if request.http.status == 200 and request.content_type == 'application/json':
            request.json_data = json.loads(request.data)

        self.responses.append(request)

    @threaded
    def thread_func(self):

        while True:
            if len(self.requests) <= 0:
                sleep(0.01)
                continue
            
            request = self.requests[0]
            self.process_request(request)
            self.requests.pop()
        
        thread.exit()

if __name__ == "__main__":
    def done(response, *args):
        print response.data

    def fail(response, *args):
        print 'fail', response.error
    import gtk
    win = gtk.Window()
    requester = JSONRequester('localhost', port=8003)
    requester.run()
    requester.request('GET', {'eu': 'wilson'}, done, fail)
    
    win.add(gtk.Label('oi'))
    win.show_all()
    gtk.threads_init()
    gtk.main()

