#!/usr/bin/env python3
 
"""Simple HTTP Server With Upload.
"""
 
import os
import posixpath
import http.server
import urllib.request, urllib.parse, urllib.error
import cgi
import shutil
import mimetypes
import re
from io import BytesIO
import sys
import glob
import os.path
import ctypes
import ctypes.util
import threading

from ctypes import c_char_p, c_int, c_size_t, c_void_p


"""
magic is a wrapper around the libmagic file identification library.

See README for more information.

Usage:

>>> import magic
>>> magic.from_file("testdata/test.pdf")
'PDF document, version 1.2'
>>> magic.from_file("testdata/test.pdf", mime=True)
'application/pdf'
>>> magic.from_buffer(open("testdata/test.pdf").read(1024))
'PDF document, version 1.2'
>>>
"""


class MagicException(Exception):
    def __init__(self, message):
        super(MagicException, self).__init__(message)
        self.message = message


class Magic:
    """
    Magic is a wrapper around the libmagic C library.

    """

    def __init__(self, mime=False, magic_file=None, mime_encoding=False,
                 keep_going=False, uncompress=False):
        """
        Create a new libmagic wrapper.

        mime - if True, mimetypes are returned instead of textual descriptions
        mime_encoding - if True, codec is returned
        magic_file - use a mime database other than the system default
        keep_going - don't stop at the first match, keep going
        uncompress - Try to look inside compressed files.
        """
        self.flags = MAGIC_NONE
        if mime:
            self.flags |= MAGIC_MIME
        elif mime_encoding:
            self.flags |= MAGIC_MIME_ENCODING
        if keep_going:
            self.flags |= MAGIC_CONTINUE

        if uncompress:
            self.flags |= MAGIC_COMPRESS

        self.cookie = magic_open(self.flags)
        self.lock = threading.Lock()
        
        magic_load(self.cookie, magic_file)

    def from_buffer(self, buf):
        """
        Identify the contents of `buf`
        """
        with self.lock:
            try:
                return magic_buffer(self.cookie, buf)
            except MagicException as e:
                return self._handle509Bug(e)

    def from_file(self, filename):
        """
        Identify the contents of file `filename`
        raises IOError if the file does not exist
        """
        if not os.path.exists(filename):
            raise IOError("File does not exist: " + filename)
        with self.lock:
            try:
                return magic_file(self.cookie, filename)
            except MagicException as e:
                return self._handle509Bug(e)

    def _handle509Bug(self, e):
        # libmagic 5.09 has a bug where it might fail to identify the
        # mimetype of a file and returns null from magic_file (and
        # likely _buffer), but also does not return an error message.
        if e.message is None and (self.flags & MAGIC_MIME):
            return "application/octet-stream"

    def __del__(self):
        # no _thread_check here because there can be no other
        # references to this object at this point.

        # during shutdown magic_close may have been cleared already so
        # make sure it exists before using it.

        # the self.cookie check should be unnecessary and was an
        # incorrect fix for a threading problem, however I'm leaving
        # it in because it's harmless and I'm slightly afraid to
        # remove it.
        if self.cookie and magic_close:
            magic_close(self.cookie)
            self.cookie = None

_instances = {}

def _get_magic_type(mime):
    i = _instances.get(mime)
    if i is None:
        i = _instances[mime] = Magic(mime=mime)
    return i

def from_file(filename, mime=False):
    """"
    Accepts a filename and returns the detected filetype.  Return
    value is the mimetype if mime=True, otherwise a human readable
    name.

    >>> magic.from_file("testdata/test.pdf", mime=True)
    'application/pdf'
    """
    m = _get_magic_type(mime)
    return m.from_file(filename)

def from_buffer(buffer, mime=False):
    """
    Accepts a binary string and returns the detected filetype.  Return
    value is the mimetype if mime=True, otherwise a human readable
    name.

    >>> magic.from_buffer(open("testdata/test.pdf").read(1024))
    'PDF document, version 1.2'
    """
    m = _get_magic_type(mime)
    return m.from_buffer(buffer)




libmagic = None
# Let's try to find magic or magic1
dll = ctypes.util.find_library('magic') or ctypes.util.find_library('magic1') or ctypes.util.find_library('cygmagic-1')

# This is necessary because find_library returns None if it doesn't find the library
if dll:
    libmagic = ctypes.CDLL(dll)

if not libmagic or not libmagic._name:
    windows_dlls = ['magic1.dll','cygmagic-1.dll']
    platform_to_lib = {'darwin': ['/opt/local/lib/libmagic.dylib',
                                  '/usr/local/lib/libmagic.dylib'] +
                         # Assumes there will only be one version installed
                         glob.glob('/usr/local/Cellar/libmagic/*/lib/libmagic.dylib'),
                       'win32': windows_dlls,
                       'cygwin': windows_dlls }
    for dll in platform_to_lib.get(sys.platform, []):
        try:
            libmagic = ctypes.CDLL(dll)
            break
        except OSError:
            pass

if not libmagic or not libmagic._name:
    # It is better to raise an ImportError since we are importing magic module
    raise ImportError('failed to find libmagic.  Check your installation')

magic_t = ctypes.c_void_p

def errorcheck_null(result, func, args):
    if result is None:
        err = magic_error(args[0])
        raise MagicException(err)
    else:
        return result

def errorcheck_negative_one(result, func, args):
    if result is -1:
        err = magic_error(args[0])
        raise MagicException(err)
    else:
        return result


def coerce_filename(filename):
    if filename is None:
        return None

    # ctypes will implicitly convert unicode strings to bytes with
    # .encode('ascii').  If you use the filesystem encoding 
    # then you'll get inconsistent behavior (crashes) depending on the user's
    # LANG environment variable
    is_unicode = (sys.version_info[0] <= 2 and
                  isinstance(filename, unicode)) or \
                  (sys.version_info[0] >= 3 and
                   isinstance(filename, str))
    if is_unicode:
        return filename.encode('utf-8')
    else:
        return filename

magic_open = libmagic.magic_open
magic_open.restype = magic_t
magic_open.argtypes = [c_int]

magic_close = libmagic.magic_close
magic_close.restype = None
magic_close.argtypes = [magic_t]

magic_error = libmagic.magic_error
magic_error.restype = c_char_p
magic_error.argtypes = [magic_t]

magic_errno = libmagic.magic_errno
magic_errno.restype = c_int
magic_errno.argtypes = [magic_t]

_magic_file = libmagic.magic_file
_magic_file.restype = c_char_p
_magic_file.argtypes = [magic_t, c_char_p]
_magic_file.errcheck = errorcheck_null

def magic_file(cookie, filename):
    return _magic_file(cookie, coerce_filename(filename))

_magic_buffer = libmagic.magic_buffer
_magic_buffer.restype = c_char_p
_magic_buffer.argtypes = [magic_t, c_void_p, c_size_t]
_magic_buffer.errcheck = errorcheck_null

def magic_buffer(cookie, buf):
    return _magic_buffer(cookie, buf, len(buf))


_magic_load = libmagic.magic_load
_magic_load.restype = c_int
_magic_load.argtypes = [magic_t, c_char_p]
_magic_load.errcheck = errorcheck_negative_one

def magic_load(cookie, filename):
    return _magic_load(cookie, coerce_filename(filename))

magic_setflags = libmagic.magic_setflags
magic_setflags.restype = c_int
magic_setflags.argtypes = [magic_t, c_int]

magic_check = libmagic.magic_check
magic_check.restype = c_int
magic_check.argtypes = [magic_t, c_char_p]

magic_compile = libmagic.magic_compile
magic_compile.restype = c_int
magic_compile.argtypes = [magic_t, c_char_p]



MAGIC_NONE = 0x000000 # No flags
MAGIC_DEBUG = 0x000001 # Turn on debugging
MAGIC_SYMLINK = 0x000002 # Follow symlinks
MAGIC_COMPRESS = 0x000004 # Check inside compressed files
MAGIC_DEVICES = 0x000008 # Look at the contents of devices
MAGIC_MIME = 0x000010 # Return a mime string
MAGIC_MIME_ENCODING = 0x000400 # Return the MIME encoding
MAGIC_CONTINUE = 0x000020 # Return all matches
MAGIC_CHECK = 0x000040 # Print warnings to stderr
MAGIC_PRESERVE_ATIME = 0x000080 # Restore access time on exit
MAGIC_RAW = 0x000100 # Don't translate unprintable chars
MAGIC_ERROR = 0x000200 # Handle ENOENT etc as real errors

MAGIC_NO_CHECK_COMPRESS = 0x001000 # Don't check for compressed files
MAGIC_NO_CHECK_TAR = 0x002000 # Don't check for tar files
MAGIC_NO_CHECK_SOFT = 0x004000 # Don't check magic entries
MAGIC_NO_CHECK_APPTYPE = 0x008000 # Don't check application type
MAGIC_NO_CHECK_ELF = 0x010000 # Don't check for elf details
MAGIC_NO_CHECK_ASCII = 0x020000 # Don't check for ascii files
MAGIC_NO_CHECK_TROFF = 0x040000 # Don't check ascii/troff
MAGIC_NO_CHECK_FORTRAN = 0x080000 # Don't check ascii/fortran
MAGIC_NO_CHECK_TOKENS = 0x100000 # Don't check ascii/tokens

 
 
class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
 
    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()
 
    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print((r, info, "by: ", self.client_address))
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode())
        f.write(("<br><a href=\"%s\">back</a>" % self.headers['referer']).encode())
        f.write(b"<hr><small>Powerd By: bones7456, check new version at ")
        f.write(b"<a href=\"http://li2z.cn/?s=SimpleHTTPServerWithUpload\">")
        f.write(b"here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
        
    def deal_post_data(self):
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
        if not fn:
            return (False, "Can't find out file name...")
        path = self.translate_path(self.path)
        fn = os.path.join(path, fn[0])
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False, "Can't create file to write, do you have permission to write?")
                
        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, "File '%s' upload success!" % fn)
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpect Ends of data.")
 
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f
 
    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = cgi.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(("<html>\n<title>Directory listing for %s</title>\n" % displaypath).encode())
        f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode())
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\"/>")
        f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write(('<li><a href="%s">%s</a>\n'
                    % (urllib.parse.quote(linkname), cgi.escape(displayname))).encode())
        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f
 
    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
 
    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)
 
    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        return from_file(path, mime=True).decode()


if __name__ == '__main__':
    import sys
    port = 80
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    server = http.server.HTTPServer(('', port), SimpleHTTPRequestHandler)
    server.serve_forever()