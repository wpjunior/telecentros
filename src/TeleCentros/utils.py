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
import time
import gobject
import tempfile
import time
import thread
import urllib2
import threading
import traceback
import subprocess
import shutil

try:
    import dl
except:
    dl = None


from hashlib import sha1 as sha
from BaseHTTPServer import BaseHTTPRequestHandler
from TeleCentros.globals import *
_ = gettext.gettext
responses = BaseHTTPRequestHandler.responses
del BaseHTTPRequestHandler

def generate_id_bytime():
    
    cur_time = time.time()
    hash = sha(str(cur_time))
    
    return hash.hexdigest()

class HttpDownload(gobject.GObject):
    
    __gsignals__ = {'done': (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT,)),
                   }
    
    CHUNKSIZE = 4096
    THROTTLE_SLEEP_TIME = 0.01

    def __init__ (self):
        
        self.__gobject_init__()
        
        self.url = None
        self.directory = None
        self.fn = None
        self.done = False
        self.err = None
        self.bytes_read = -1
        self.content_length = 0
        self.cancelled = False
        self.verbose = False

    def get_error_msg_from_error(self, err):
        msg = _("Unexpected error of type %s") % type(err)
        
        try:
            raise err
        except urllib2.HTTPError, e:
            if e.code == 403:
                msg = _("Access to this file is forbidden")
            
            elif e.code == 404:
                msg = _("File not found on server")
                
            elif e.code == 500:
                msg = _("Internal server error, try again later")
                
            elif e.code == 503:
                msg = _("The server could not process the request due to " \
                        "high server load, try again later")
                
            else:
                try:
                    m = responses[e.code]
                except KeyError:
                    m = _("Unknown Error")
                msg = _("Server error %u: %s") % (e.code, m)
            
        except urllib2.URLError, e:
            msg = _("Failed to connect to server: %s") % e.reason[1]
            
        except IOError, e:
            if e.filename and e.strerror:
                msg = _("File error for '%s': %s") % (e.filename, e.strerror)
                
            elif e.strerror:
                msg = _("File error: %s") % e.strerror
                
            elif e.filename:
                msg = _("File error for '%s'") % e.filename
                
            else:
                msg = _("Unknown file error %d") % e.errno

        return msg

    """ Iterates the default GLib main context until the download is done """
    def run(self, url, directory, fn, message=None):
        
        if self.url:
            return _("Download already in progress")
        
        self.url = url
        self.directory = directory
        self.fn = fn
        self.done = False
        self.err = None
        self.bytes_read = -1
        self.content_length = 0
        self.cancelled = False

        thread.start_new_thread(self.thread_func, ())

        timeout_id = gobject.timeout_add(500, self.update_progress)

        self.update_progress()

      # Don't try to be smart and block here using mayblock=True, it won't work
        while not self.done:
            gobject.main_context_default().iteration(False)

        gobject.source_remove(timeout_id)

      # Update to 'finished' state
        self.update_progress()
        while gobject.main_context_default().pending():
            gobject.main_context_default().iteration(False)

      # Reset state
        self.url = None
        self.directory = None
        self.fn = None
        self.done = False
        self.bytes_read = -1
        self.content_length = 0

        return self.err

    """ Called from the context of the main GUI thread """
    def update_progress(self):
        if self.verbose:
            if self.bytes_read < 0:
                print "Connecting to server"
                
            elif self.bytes_read == 0:
                print "Connected to server"
                
            elif self.content_length > 0:
                print "Bytes read: %.1f (%.1f%%)" %                    \
                      (self.bytes_read / 1024.0,                       \
                       self.bytes_read * 100.0 / self.content_length)
                       
            else:
                print "Bytes read: %.1f" % (self.bytes_read / 1024.0)

        return not self.done

    """ Thread where all the downloading and file writing happens """
    def thread_func(self):

        tmpfile_path = None

      # First, see if we can resolve the URL at all and connect to the host
        try:
            self.bytes_read = -1
            res = urllib2.urlopen(self.url)
            self.bytes_read = 0
            time.sleep(self.THROTTLE_SLEEP_TIME)

            try:
                self.content_length = int(res.info()['Content-Length'])
            except KeyError:
                self.content_length = 0

          # Make sure the directory exists (ignore exception thrown if it
          # already exists, mkstemp will throw an exception later if there
          # is really a problem)
            try:
                os.makedirs(self.directory)
            except:
                pass

            # Now create a temp file there
            tmpfile_handle, tmpfile_path = tempfile.mkstemp('.incomplete',\
                                                            'telecentros')

            while not self.cancelled:
                data = res.read(self.CHUNKSIZE)
                if data and len(data):
                    self.bytes_read += len(data)
                    os.write(tmpfile_handle, data)
                    # give GUI thread a chance to show progress
                    time.sleep(self.THROTTLE_SLEEP_TIME)
                else:
                    break

          # Now rename the temporary file to the desired file name
            if self.cancelled:
                try:
                    os.remove(tmpfile_path)
                except:
                    pass
            else:
                shutil.move(tmpfile_path, os.path.join(self.directory, self.fn))

        except (urllib2.HTTPError, urllib2.URLError, IOError), e:
            self.err = self.get_error_msg_from_error (e)
            
            if tmpfile_path:
                try:
                    os.remove(tmpfile_path)
                except:
                    pass
                    
        else:
            self.err = None

      # Finished (one way or another), stop the thread
        self.done = True
        thread.exit()

def mkdir(path, RemoveExisting=False):
    """ 
        Create a full path, directory by directory
        if removeExisting is set it will remove main folder and contents before creation.
    """

    #remove directiory if already exists
    if RemoveExisting:
        if os.path.exists(path):
            removePath(path)

    if not os.path.exists(path):
        os.makedirs(path)

    return path

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

def is_in_path(name_of_command, return_abs_path=True):
    # if return_abs_path is True absolute path will be returned
    # for name_of_command
    # on failures False is returned
    
    is_in_dir = False
    found_in_which_dir = None
    path = os.getenv('PATH').split(':')
    
    for path_to_directory in path:
        try:
            contents = os.listdir(path_to_directory)
        
        except OSError: # user can have something in PATH that is not a dir
            pass
        
        else:
            is_in_dir = name_of_command in contents
        
        if is_in_dir:
            if return_abs_path:
                found_in_which_dir = path_to_directory
            
            break

    if found_in_which_dir:
        abs_path = os.path.join(path_to_directory, name_of_command)
        return abs_path
    
    else:
        return is_in_dir

def execute_command(cmd):
    """
        Execute command
    """
    if not isinstance(cmd, list):
        cmd = [cmd]
        
    env = os.environ
    po = subprocess.Popen(cmd, stdin=None, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, env=env)
    
    retval = po.wait()
    (stdout, stderr) = po.communicate()
    
    return (stdout, stderr, retval)

def md5_cripto(text):
    """Criptografy Text into MD5"""
    return md5(text).hexdigest()

def kill_windows_process(process_name):
    cmd = ["taskkill",  "/f", "/fi",
           "USERNAME eq %s" % os.environ['USERNAME'],
           "/im", "%s.exe" % process_name]
    
    out, err, retval = execute_command(cmd)
    
    if retval != 0:
        print err.strip()
    else:
        print out.strip()
    
def kill_process(process_name):
    if os.name == "posix":         # posix
        cmd = ["killall", process_name, "-u", os.environ['USER']]
        execute_command(cmd)

    elif os.name == "nt":       # windows handler
        t = threading.Thread(target=kill_windows_process, args=(process_name,))
        t.setDaemon(True)
        t.start()


WIN_VERSION = {
    (1, 4, 0): '95',
    (1, 4, 10): '98',
    (1, 4, 90): 'ME',
    (2, 4, 0): 'NT',
    (2, 5, 0): '2000',
    (2, 5, 1): 'XP',
    (2, 5, 2): '2003',
    (2, 6, 0): 'Vista', #ADD WIN 7
}

DISTRO_INFO = {
    'Arch Linux': '/etc/arch-release',
    'Aurox Linux': '/etc/aurox-release',
    'Big Linux': '/etc/atualizacao/bigversao',
    'Conectiva Linux': '/etc/conectiva-release',
    'CRUX': '/usr/bin/crux',
    'Debian GNU/Linux': '/etc/debian_release',
    'Debian GNU/Linux': '/etc/debian_version',
    'Fedora Linux': '/etc/fedora-release',
    'Gentoo Linux': '/etc/gentoo-release',
    'Linux from Scratch': '/etc/lfs-release',
    'Mandrake Linux': '/etc/mandrake-release',
    'Slackware Linux': '/etc/slackware-release',
    'Slackware Linux': '/etc/slackware-version',
    'Solaris/Sparc': '/etc/release',
    'Source Mage': '/etc/sourcemage_version',
    'SUSE Linux': '/etc/SuSE-release',
    'Sun JDS': '/etc/sun-release',
    'PLD Linux': '/etc/pld-release',
    'Yellow Dog Linux': '/etc/yellowdog-release',
    # many distros use the /etc/redhat-release for compatibility
    # so Redhat is the last
    'Redhat Linux': '/etc/redhat-release'
}

def get_os():
    """
        Return os_name and os_version
    """
    
    def convert(x):
        x = x.strip().replace('n/a', '').replace('N/A', '')
        if x:
            return x
    
    name = None
    version = None
    
    if os.name == 'posix':
        executable = 'lsb_release'
        full_path_to_executable = is_in_path(executable, return_abs_path=True)
        
        if full_path_to_executable:
            (tmp1, a, b) = execute_command([executable, '-i', '--short'])
            (tmp2, a, b) = execute_command([executable, '-c', '--short'])
            (tmp3, a, b) = execute_command([executable, '-r', '--short'])
            
            if convert(tmp1):
                name = convert(tmp1)
            
            if convert(tmp2):
                version = convert(tmp2)
                
            if convert(tmp3) and version:
                version = version + ' (' + convert(tmp3) + ')'
        
        if not name:
            for distro_name in DISTRO_INFO:
                path_to_file = DISTRO_INFO[distro_name]
                
                if os.path.exists(path_to_file):
                    if os.access(path_to_file, os.X_OK):
                        # the file is executable (f.e. CRUX)
                        # yes, then run it and get the first line of output.
                        text = get_output_of_command(path_to_file).splitlines()[0]
                    else:
                        fd = open(path_to_file)
                        text = fd.readline().strip() # get only first line
                        fd.close()
                        if path_to_file.endswith('version'):
                            # sourcemage_version and slackware-version files
                            # have all the info we need (name and version of distro)
                            if not os.path.basename(path_to_file).startswith(
                            'sourcemage') or not\
                            os.path.basename(path_to_file).startswith('slackware'):
                                name = distro_name
                                version = text
                        
                        elif path_to_file.endswith('aurox-release'):
                            #    file doesn't have version
                            name = distro_name
                            
                        elif path_to_file.endswith('lfs-release'): # file just has version
                            name = distro_name
                            version = text
                    
                    break
        
        if not name:
            tmp = os.uname()
            name = tmp[0]
            version = tmp[2]
    
    elif os.name == 'nt':
        ver = os.sys.getwindowsversion()
        ver_format = ver[3], ver[0], ver[1]
        
        name = 'Windows'
        
        if WIN_VERSION.has_key(ver_format):
            version = WIN_VERSION[ver_format]
            
    elif os.name == 'ce':
        name = 'Windows'
        version = 'CE'
    
    elif os.name == 'mac':
        name = 'MacOS'
    
    return (name, version)

def humanize_time(mtime):
    secs = mtime % 60
    minutes = (mtime // 60) % 60
    hour = (mtime // (60 * 60)) % 60
    return hour, minutes, secs

def get_output_of_command(command):
    try:
        child_stdin, child_stdout = os.popen2(command)
    except ValueError:
        return None

    output = child_stdout.read()
    child_stdout.close()
    child_stdin.close()

    return output

def rename_process(name):
    """rename process by libc"""
    if os.name == 'posix':
        try:
            libc = dl.open('/lib/libc.so.6')
            libc.call('prctl', 15, '%s\0' % name, 0, 0, 0)
        except:
            pass

def pid_alive(app, path):
    try:
        pf = open(path)
    
    except:
        # probably file not found
        return False

    try:
        pid = int(pf.read().strip())
        pf.close()
    except:
        traceback.print_exc()
        # PID file exists, but something happened trying to read PID
        # Could be 0.10 style empty PID file, so assume app is running
        return True

    if os.name == 'nt':
        try:
            from ctypes import windll, c_ulong, c_int
            from ctypes import Structure, c_char, POINTER, pointer
        except:
            return True

        class PROCESSENTRY32(Structure):
            _fields_ = [
                ('dwSize', c_ulong, ),
                ('cntUsage', c_ulong, ),
                ('th32ProcessID', c_ulong, ),
                ('th32DefaultHeapID', c_ulong, ),
                ('th32ModuleID', c_ulong, ),
                ('cntThreads', c_ulong, ),
                ('th32ParentProcessID', c_ulong, ),
                ('pcPriClassBase', c_ulong, ),
                ('dwFlags', c_ulong, ),
                ('szExeFile', c_char*512, ),
                ]
            def __init__(self):
                Structure.__init__(self, 512+9*4)

        k = windll.kernel32
        k.CreateToolhelp32Snapshot.argtypes = c_ulong, c_ulong,
        k.CreateToolhelp32Snapshot.restype = c_int
        k.Process32First.argtypes = c_int, POINTER(PROCESSENTRY32),
        k.Process32First.restype = c_int
        k.Process32Next.argtypes = c_int, POINTER(PROCESSENTRY32),
        k.Process32Next.restype = c_int

        def get_p(p):
            h = k.CreateToolhelp32Snapshot(2, 0) # TH32CS_SNAPPROCESS
            assert h > 0, 'CreateToolhelp32Snapshot failed'
            b = pointer(PROCESSENTRY32())
            f = k.Process32First(h, b)
            while f:
                if b.contents.th32ProcessID == p:
                    return b.contents.szExeFile
                f = k.Process32Next(h, b)

        if get_p(pid) in ('python.exe', '%s.exe' % app):
            return True
        return False
    try:
        if not os.path.exists('/proc'):
            return True # no /proc, assume running

        if not os.path.exists('/proc/%d/cmdline'% pid):
            return False

        try:
            f = open('/proc/%d/cmdline'% pid) 
        except IOError, e:
            raise 

        n = f.read().lower()
        f.close()
        if n.find(app) < 0:
            return False
        return True # Running app found at pid
    except:
        traceback.print_exc()

    # If we are here, pidfile exists, but some unexpected error occured.
    # Assume running.
    return True
