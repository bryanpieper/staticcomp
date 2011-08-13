"""
Staticcomp url configuration.

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

from django.conf.urls.defaults import *
from staticcomp.compressor import JsCompressor, CssCompressor


urlpatterns = patterns('staticcomp.views',
    # JavaScript compression
    url(r'^j/(?P<group>[A-Za-z0-9]+)/(?P<b64_js>[A-Za-z0-9=]+)/c/(?P<hash>[0-9a-fA-F]+).js$', 'compressed_js', {'klass': JsCompressor}, name='compressed_js'),
    url(r'^j/(?P<group>[A-Za-z0-9]+)/(?P<b64_js>[A-Za-z0-9=]+)/a/(?P<hash>[0-9a-fA-F]+).js$', 'append_js', name='append_js'),

    # CSS compression
    url(r'^c/(?P<group>[A-Za-z0-9]+)/(?P<b64_css>[A-Za-z0-9=]+)/c/(?P<hash>[0-9a-fA-F]+).css$', 'compressed_css', {'klass': CssCompressor}, name='compressed_css'),
    url(r'^c/(?P<group>[A-Za-z0-9]+)/(?P<b64_css>[A-Za-z0-9=]+)/a/(?P<hash>[0-9a-fA-F]+).css$', 'append_css', name='append_css'),
)