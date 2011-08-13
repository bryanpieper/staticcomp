"""
Decorators for the JavaScript and CSS compression views

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

from functools import wraps
from staticcomp.compressor import JsPayload, CssPayload
from staticcomp.models import StaticCompError

from django.http import HttpResponse
from django.conf import settings


def js_payload(f):
    """
    Decodes and validates the JsPayload using the group and the url encoding. The callback will
    receive the payload instance as the second argument. It will also ensure the response is always
    application/javascript while errors will be logged.
    """
    @wraps(f)
    def inner(request, group, b64_js, hash, *args, **kwargs):
        status_code = 200
        try:
            payload = JsPayload.decode(group=group, b64_code=b64_js, hash=hash)
            js_data = f(request, payload, *args, **kwargs)
        except:
            if not settings.DEBUG:
                from StringIO import StringIO
                import traceback
                buf = StringIO()
                traceback.print_exc(file=buf)
                # write out error to database for non-debug requests
                StaticCompError.log_error(request, buf.getvalue())                
                js_data = "/* Invalid Request */"
                status_code = 500
            else:
                raise
        return HttpResponse(js_data, mimetype="application/javascript", status=status_code)
    return inner


def css_payload(f):
    """
    Decodes and validates the CssPayload using the group and the url encoding. The callback will
    receive the payload instance as the second argument. It will also ensure the response is always
    text/css while errors will be logged.
    """
    @wraps(f)
    def inner(request, group, b64_css, hash, *args, **kwargs):
        status_code = 200
        try:
            payload = CssPayload.decode(group=group, b64_code=b64_css, hash=hash)
            css_data = f(request, payload, *args, **kwargs)
        except:
            if not settings.DEBUG:
                from StringIO import StringIO
                import traceback
                buf = StringIO()
                traceback.print_exc(file=buf)
                # write out error to database for non-debug requests
                StaticCompError.log_error(request, buf.getvalue())                
                css_data = "/* Invalid Request */"
                status_code = 500
            else:
                raise
        return HttpResponse(css_data, mimetype="text/css", status=status_code)
    return inner
