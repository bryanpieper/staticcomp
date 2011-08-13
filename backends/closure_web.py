"""
Google Closure Web Compiler backend for the javascript compression. 

Utilizes the Google Closure Web Service to compress the JavaScript.

http://code.google.com/closure/compiler/docs/overview.html

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

from django.conf import settings

from staticcomp.compressor import CompressorService, CodeCompressorThread, CompressorException

from contextlib import contextmanager
import httplib
import urllib


# Either WHITESPACE_ONLY, SIMPLE_OPTIMIZATIONS 
#  or ADVANCED_OPTIMIZATIONS (the advanced option is not recommended for this usage)
COMPILATION_LEVEL = getattr(settings, 'JSCOMP_OPTIMIZATION', 'SIMPLE_OPTIMIZATIONS')


class ClosureRequestError(CompressorException):
    pass


class GoogleClosureWebService(CompressorService):
    """
    Web-based Google Closure Compiler Service. Relies on Google's appspot
    web service.
    
    More info at http://closure-compiler.appspot.com/
    """
    closure_uri = "/compile"
    closure_host = "closure-compiler.appspot.com"
    
    def __init__(self, *args, **kwargs):
        super(GoogleClosureWebService, self).__init__(*args, **kwargs)
        self.headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "User-Agent": getattr(settings, 'USER_AGENT', settings.URL_VALIDATOR_USER_AGENT)
        }
        
    @contextmanager
    def closure_request(self, params):
        conn = None
        try:
            conn = httplib.HTTPConnection(self.closure_host)
            conn.request('POST', self.closure_uri, params, self.headers)
            res = conn.getresponse()
            res_data = None
            if res.status == 200:
                res_data = res.read()
            else:
                raise ClosureRequestError("Invalid Closure Request Status Code {0}".format(res.status))
            yield self.apply_header(res_data)
        except:
            raise
        finally:
            if conn:
                conn.close()
    
    def compress_string(self, data):
        params = [
            ('js_code', data),
            ('compilation_level', COMPILATION_LEVEL),
            ('output_format', 'text'),
            ('output_info', 'compiled_code'),
        ]
        if settings.DEBUG:
            params.append(('formatting', 'pretty_print'))
        with self.closure_request(urllib.urlencode(params)) as closure_data:
            return closure_data



class GoogleClosureWebThread(CodeCompressorThread):
    CompressorClass = GoogleClosureWebService


CompressorThread = GoogleClosureWebThread
