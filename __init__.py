"""
Django Static compressor app. Compresses JavaScript files and inline <script /> blocks on-demand. Also
includes cssmin for Cascading Stylesheet compression.

This javascript compression framework has two use cases:
 1) Compress (and append) one or more javascript files
 2) Compress inline <script> blocks
 
The css compression only supports css files, not inline styles.
 
The module needs memcached (or similar cache backend) to provide the performance needed to function properly along 
with a webserver that integrates with the cache backend.

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


compressor_defaults = {
    'css': lambda: getattr(settings, 'CSSCOMP_BACKEND', 'pycssmin'),
    'js': lambda: getattr(settings, 'JSCOMP_BACKEND', 'uglifyjs'),
}


class CodeCompressorThreadFactoryImpl(object):
    """
    Code Compressor Factory.  Handles the initialization of the compressor backend and threads used
    by compressor.py.
    """
    def __init__(self):
        self._klass = {}
        
    def _setup(self, code_type):
        """
        Load the backend and thread class
        """
        from django.utils.importlib import import_module
        if code_type not in compressor_defaults:
            raise AttributeError("The backend type {0} is not configured".format(code_type))
        code_backend = compressor_defaults[code_type]()
        try:
            mod = import_module(code_backend)
        except:
            try:
                mod = import_module('.'.join(['staticcomp.backends', code_backend]))
            except:
                raise ImportError("The staticcomp backend {0} was not found".format(code_backend))

        # backend requires a CompressorThread class
        thread_klass = getattr(mod, 'CompressorThread', None)
        if not thread_klass:
            raise AttributeError("The module {0} does not implement the CompressorThread class".format(mod.__name__))
        self._klass[code_type] = thread_klass
    
    def create(self, code_type='js', *args, **kwargs):
        if code_type not in self._klass:
            self._setup(code_type)
        return self._klass[code_type](*args, **kwargs)


CodeCompressorThreadFactory = CodeCompressorThreadFactoryImpl()
