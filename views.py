"""
Staticcomp views for JavaScript and CSS compression.

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
from django.core.cache import cache

from staticcomp.decorators import js_payload, css_payload
from staticcomp.compressor import JsCompressor, CACHE_TIMEOUT

KEY_FORMAT = getattr(settings, 'STATICCOMP_CACHE_KEY', 'staticcomp_{group}_{hash}')


def _staticcomp_key(payload):
    """
    The key is used by the frontend (nginx, apache, etc) then passed to the cache 
    backend (ie memcached). 
    
    Default Format: staticcomp_[group]_[hash]
    """
    return KEY_FORMAT.format(group=payload.group, hash=payload.hash)



def compress_code(request, payload, klass=JsCompressor):
    data = payload.dump()
    
    # kill switch for the compression request
    if getattr(settings, 'STATICCOMP_DISABLE', False):
        return data
    
    # execute the compression 
    code_compressor = klass(data, cache_key=_staticcomp_key(payload), job_name=payload.name)
    code_compressor.init()
    return code_compressor.compress_code()


compressed_css = css_payload(compress_code)
compressed_js = js_payload(compress_code)


def append_code(request, payload):
    """
    Process the append request. The payload is not compressed, just appended in order.    
    """
    if getattr(settings, 'STATICCOMP_DISABLE', False):
        return payload.dump()
        
    cache_key = _staticcomp_key(payload)
    cached_css = cache.get(cache_key)
    if not cached_css:
        cached_css = payload.dump()
        cache.set(cache_key, cached_css, CACHE_TIMEOUT)
    return cached_css


append_css = css_payload(append_code)
append_js = js_payload(append_code)
