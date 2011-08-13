"""
JavaScript & CSS compressor app base classes.

Usage:
  j = JsCompressor("// some javascript")
  data = j.compress_code()  # request/retrieve the compressed JavaScript

Copyright (c) 2011 Bryan Pieper, http://www.thepiepers.net/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

from django.core.cache import cache
from django.conf import settings
from django.utils._os import safe_join

# By default uses the multiprocessing.Process. In my testing with uwsgi, the
# Thread will hang before the compressor process has a chance to
# do it's job. The problem should be corrected if you compile uwsgi with threads, but 
# I haven't verified it.
#
# If you are running the development server (runserver) and using locmem:// as 
# your cache backend, enable the STATICCOMP_USE_THREADS flag so the cache value isn't
# lost when the child process exits.
if getattr(settings, 'STATICCOMP_USE_THREADS', False):
    from threading import Thread
else:
    from multiprocessing import Process as Thread

from datetime import datetime
from StringIO import StringIO

import hashlib
import hmac
import base64
import os
import re
import subprocess
import itertools

from staticcomp import CodeCompressorThreadFactory

# bad file / file hack regex
bad_file_re = re.compile(r'(\.\.|\./|\\|[\'%"$~+|<>&\s{}()@,`?])')

# cache timeout for cached javascript, default of 1 year
CACHE_TIMEOUT = getattr(settings, 'STATICCOMP_CACHE_SECONDS', 60 * 60 * 24 * 365)


class CompressorException(Exception):
    pass

class PayloadException(CompressorException):
    pass

class BadFileException(PayloadException):
    pass




def media_root(name):
    return safe_join(settings.MEDIA_ROOT, name)


class CompressorService(object):
    """
    Code compressor service interface. 
    """
    def __init__(self, cache_key, job_name, *args, **kwargs):
        self.cache_key = cache_key
        self.job_name = job_name
    
    def apply_header(self, data):
        """
        Attaches the header content to the compressed code.
        """
        def header(n, dt):
            return "/* {name} \n   Compressed: {now} */\n".format(name=n, now=dt)
        
        compressed_header = getattr(settings, 'STATICCOMP_HEADER', header)(self.job_name, datetime.now())
        return "\n".join([compressed_header, data])
    
    def compress_string(self, data):
        raise NotImplementedError()

    def cmd(self, cmdline, data):
        """
        Execute the given command and return the STDOUT as the compressed code. Uses 
        the STDIN for the source.
        """
        p = subprocess.Popen(
            cmdline.split(),
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate(data)
        if p.returncode:
            print stderr
            raise CompressorException("Command failed: {0}".format(p.returncode))
        return stdout


class CodeCompressorThread(Thread):
    """
    The compressor service executes the actual compression in a separate Thread/Process
    to ensure the web request doesn't have to wait for it to finish the job.
    """
    class CompressorClass(CompressorService):
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("Compressor Not Implemented")
        
    cache_timeout = CACHE_TIMEOUT
    
    def __init__(self, cache_key, data, job_name, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self.cache_key = cache_key      
        self.data = data
        self.job_name = job_name

    def run(self):
        try:
            self.run_svc()
        except:
            if not settings.DEBUG:
                from django.core.mail import mail_admins
                import traceback
                buf = StringIO()
                traceback.print_exc(file=buf)
                mail_admins("Code compressor thread failed", buf.getvalue(), fail_silently=False)
                
            # if fails, report in header of code
            code_header = "/* Compression failed {0} */".format(datetime.now())
            cache.set(self.cache_key, "\n".join([code_header, self.data]), 60)
            raise
        
    def run_svc(self):
        """
        Intended to be overridden by the implementing compression service if the
        behavior differs.
        """
        comp = self.CompressorClass(cache_key=self.cache_key, job_name=self.job_name)
        compressed_data = comp.compress_string(self.data)
        if compressed_data:
            cache.set(self.cache_key, compressed_data, self.cache_timeout)


class CodePayload(object):
    """
    Base class for the code payload. Handles the encoding and
    decoding of the data.
    
    - file_list is a list of relative paths to the MEDIA_ROOT
    - group is the name of the file group
    
    Payload contents (a base64-encoded comma-delimited list):
     1) a list of relative file names to MEDIA_ROOT
     2) the payload signature
     3) the payload mod timestamp (represents the most recent file mod time in epoch) 
    """
    def __init__(self, file_list, group):
        if not file_list or not group:
            raise ValueError("Requires a valid file_list and group")
        try:
            iter(file_list)
        except TypeError:
            raise TypeError("The file_list must be iterable")
        
        self.file_list = file_list
        self.group = group
        self.hash = None
        self.b64_code = None
        self.name = ", ".join(self.file_list)
        self._file_cache = {}
        
    @classmethod
    def signature(cls, files, group, mod_time, *parts):
        """
        Creates a signature request to ensure the data is intact and matches this app instance.  
        The signature is based on the current SECRET_KEY, the file names (in order), 
        the group name and the latest file modification time.
        """
        digest = hmac.new(settings.SECRET_KEY, digestmod=hashlib.sha256)
        map(digest.update, map(str, itertools.chain(files, (group, mod_time), parts)))
        return digest.hexdigest()

    @classmethod
    def url_encode(cls, files, *parts):
        """
        Creates the encoded URL value
        """
        return base64.urlsafe_b64encode(",".join(map(str, itertools.chain(files, parts))))

    @classmethod
    def url_decode(cls, b64_val):
        """
        Decode the URL value and returns the items as a list
        """
        return base64.urlsafe_b64decode(str(b64_val)).split(",") or []
    
    @classmethod
    def hash(cls, val):
        return hashlib.sha1(val).hexdigest() if val else ""

    def _calc_mod_time(self):
        """
        Calculates the latest modification time for the files. This will ensure
        the payload signature encoding changes when the one or more of the files are modified.
        """
        return int(max([os.stat(self._media_root(f)).st_mtime for f in self.file_list]))

    def _media_root(self, file):
        """
        Check and join the MEDIA_ROOT and the file name. Keeps a small cache of file paths
        to prevent unnecessary calls to safe_join()
        """
        try:
            file_path = self._file_cache[file]
        except KeyError:
            file_path = media_root(file)
            self._file_cache[file] = file_path
        return file_path
    
    def _check_file_name(self, file_name):
        """
        Checks the relative file name and ensures it is valid, part of
        the MEDIA_ROOT and exists.
        """
        if bad_file_re.search(file_name) or file_name[0] in ('.', '/'):
            raise BadFileException("Invalid File Name: {0}".format(file_name))
        
        if not self.check_file_ext(file_name):
            raise BadFileException("Invalid File Type: {0}".format(file_name))
        
        file_path = self._media_root(file_name)
        if not os.path.exists(file_path):
            raise BadFileException("File Does Not Exist: {0}".format(file_path))
        return file_path

    def check_file_ext(self, file_name):
        raise NotImplementedError()
    
    def check(self):
        """
        Checks the files in the file_list to ensure they are valid and exist
        """
        map(self._check_file_name, self.file_list)

    def encode(self):
        """
        Encodes the payload using the instance files and the group name.
        Returns (b64_code, hash) of the payload
        """
        mod_time = self._calc_mod_time()
        sig = self.__class__.signature(self.file_list, self.group, mod_time)
        self.b64_code = self.__class__.url_encode(self.file_list, mod_time)
        
        # the hash value is used as part of the cache key to ensure the key is small
        self.hash = sig
        return self.b64_code, self.hash

    def dump(self):
        """
        Returns the files as one value in the order given.
        """
        buf = StringIO()
        for f in self.file_list:
            with open(self._media_root(f), 'r') as fd:
                buf.write(fd.read())
                buf.write("\n")
        return buf.getvalue()
    
    @classmethod
    def decode(cls, group, b64_code, hash):
        """
        Decodes the given base64 value and returns a CodePayload instance. 
        """
        if not b64_code:
            raise PayloadException("Payload empty")
        
        try:
            # create the list
            payload = cls.url_decode(b64_code)
        except:
            raise PayloadException("Invalid encoding")
        else:
            if len(payload) < 2:
                raise PayloadException("Invalid Payload Length {0}".format(len(payload)))
            
            # extract the payload parts
            code_files, code_timestamp = payload[:-1], payload[-1]
            
            # verify the signature
            sig_test = cls.signature(code_files, group, code_timestamp)
            if not sig_test == hash:
                raise PayloadException("Invalid Signature")
            
            # verify the encoding
            enc_test = cls.url_encode(code_files, code_timestamp)
            if not b64_code == enc_test:
                raise PayloadException("Invalid Encoding")
            
            # must have one or more files
            if not len(code_files):
                raise PayloadException("No Files Provided")
            
            payload_instance = cls(code_files, group)
            payload_instance.check()
            payload_instance.b64_code = b64_code
            payload_instance.hash = hash 
            return payload_instance


class CssPayload(CodePayload):
    def check_file_ext(self, file_name):
        return os.path.splitext(file_name)[-1] == '.css'


class JsPayload(CodePayload):
    def check_file_ext(self, file_name):
        return os.path.splitext(file_name)[-1] == '.js'
  

class CodeCompressor(object):
    """
    Code compression base class. 
    
    The compress_string() method initially will queue the compression job if 
    the code isn't cached. The code will be initially cached while the
    job is running.  When the job completes, the thread will store the
    compressed code in the cache. 
    
    Any calls to compress_string() that have already been compressed will return
    the data from the cache backend.
    """
    def __init__(self, data, job_name=None, cache_key=None, *args, **kwargs):
        super(CodeCompressor, self).__init__(*args, **kwargs)
        self.cached_data = None
        self.data = data
        self.cache_key = cache_key
        self.job_name = job_name        
        if data and not cache_key:
            data_md5 = self._hash(data)
            self.cache_key = "_".join(["staticcomp_code", data_md5])
            if not job_name:
                self.job_name = data_md5
    
    def _hash(self, data):
        return hashlib.md5(data).hexdigest()
    
    def init(self):
        pass
    
    def compress_code(self):
        raise NotImplementedError()


class JsCompressor(CodeCompressor):
    """
    The JsCompressor is the main hook into the JavaScript compression framework.
    """
    def compress_code(self):
        if self.cache_key:
            self.cached_data = cache.get(self.cache_key)
            if not self.cached_data:
                js_header = "/* Processing JS compression {0} */".format(datetime.now())
                # set the current js data to prevent processing from overlapping
                cache.set(self.cache_key, "\n".join([js_header, self.data]), 60)
                
                # execute the compression in a separate thread
                compressor_thread = CodeCompressorThreadFactory.create('js', self.cache_key, self.data, self.job_name)
                compressor_thread.start()
            else:
                return self.cached_data
        
        # return JS as-is 
        return self.data or ""


class CssCompressor(CodeCompressor):
    """
    The CssCompressor is the main hook into the CSS compression framework.
    """
    def compress_code(self):
        if self.cache_key:
            self.cached_data = cache.get(self.cache_key)
            if not self.cached_data:
                css_header = "/* Processing CSS compression {0} */".format(datetime.now())
                # set the current css data to prevent processing from overlapping
                cache.set(self.cache_key, "\n".join([css_header, self.data]), 60)
                
                # execute the compression in a separate thread
                compressor_thread = CodeCompressorThreadFactory.create('css', self.cache_key, self.data, self.job_name)
                compressor_thread.start()
            else:
                return self.cached_data
        
        # return CSS as-is 
        return self.data or ""
