"""
Staticcomp test cases

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

from django.test import TestCase
from django.conf import settings
from django.core.cache import cache
import re

processing_re = re.compile(r' Processing JS compression ')
compressed_re = re.compile(r' Compressed: ')


class JsCompTestCase(TestCase):
    def setUp(self):
        if getattr(settings, 'JSCOMP_DISABLE', False):
            self.fail("JSCOMP_DISABLE is True, unable to complete test cases")
        cache.clear()


class TestSettings(TestCase):
    def test_settings(self):
        self.failUnless(getattr(settings, 'MEDIA_ROOT', None), "MEDIA_ROOT does not have a value")
        self.failUnless(getattr(settings, 'SECRET_KEY', None), "SECRET_KEY does not have a value")
    
    def test_header(self):
        func = getattr(settings, 'STATICCOMP_HEADER', None)        
        if func:
            self.assertTrue(callable(func), "{0} is not callable".format(func))
            from datetime import datetime
            result = func("foo", datetime.now())
            self.failUnless(result)
            self.assertIsInstance(result, basestring)
            
    def test_media_root(self): 
        import os
        self.assertTrue(os.path.exists(settings.MEDIA_ROOT))
        
    def test_concurrency(self):
        from staticcomp.compressor import Thread as JsThread
        import threading
        import multiprocessing
        if getattr(settings, 'STATICCOMP_USE_THREADS', False):
            self.assertIsInstance(JsThread(), threading.Thread)
        else:
            self.assertIsInstance(JsThread(), multiprocessing.Process)
            
    def test_cache_backend(self):
        if not getattr(settings, 'STATICCOMP_USE_THREADS', False):
            from django.core.cache.backends.locmem import CacheClass
            if isinstance(cache, CacheClass):
                self.fail("Your cache backend is set to locmem:// while the staticcomp framework is configured to use the "
                          "multiprocessing module. The cache backend will be of no use as your data will be lost when " 
                          "the child process dies.")

class TestFactory(JsCompTestCase):
    def test_factory_js(self):
        from staticcomp import CodeCompressorThreadFactory
        from staticcomp.compressor import CodeCompressorThread
        code_thread = CodeCompressorThreadFactory.create('js', 'key', '// js data', 'job')
        # ensure thread class is correct
        self.assertIsInstance(code_thread, CodeCompressorThread)

    def test_factory_css(self):
        from staticcomp import CodeCompressorThreadFactory
        from staticcomp.compressor import CodeCompressorThread 
        code_thread = CodeCompressorThreadFactory.create('css', 'key', '/* css data */', 'job')
        # ensure thread class is correct
        self.assertIsInstance(code_thread, CodeCompressorThread)

             
class TestPayload(JsCompTestCase):
    def setUp(self):
        super(TestPayload, self).setUp()
        settings.SECRET_KEY = 'abc123'
        self.fake_files = ['js/a.js', 'js/b.js']
        self.fake_group = 'agroup'
        self.mod_time = 1296949725

    def test_signature(self):
        from staticcomp.compressor import JsPayload
        sig = JsPayload.signature(self.fake_files, self.fake_group, self.mod_time)
        self.assertEqual(sig, 'fceba194a9faf706f8abe35ba5a10d746be0244e09681da0abcb5407e1ca44e9')
    
    def test_url_encoding(self):
        from staticcomp.compressor import JsPayload
        sig = JsPayload.signature(self.fake_files, self.fake_group, self.mod_time)
        b64_url = JsPayload.url_encode(self.fake_files, self.mod_time)
        self.assertEquals(b64_url, 'anMvYS5qcyxqcy9iLmpzLDEyOTY5NDk3MjU=')
    
    def test_encoding_fail(self):
        from staticcomp.compressor import JsPayload
        payload = JsPayload(['js/a123.js', 'js/bcccc.js', 'js/foo/bar.js'], 'base')
        try:
            payload.encode()
        except OSError:
            # this is expected as these files shouldn't exist
            pass
        else:
            self.fail("The JsPayload encoder should have failed.")
    
    def test_code_random_js(self):
        import os
        js_files = set()
        min_re = re.compile(r'\.min\.')
        media_root = os.path.normpath(settings.MEDIA_ROOT)
        is_js = lambda f: bool(os.path.splitext(f)[-1] == '.js' and not min_re.search(f))
        def w(fileset, dirname, names):
            if len(fileset) < 3:
                js_files = filter(is_js, names)
                if js_files:
                    map(fileset.add, [ os.path.join(dirname, f)[len(media_root)+1:] for f in js_files])
                
        os.path.walk(settings.MEDIA_ROOT, w, js_files)
        if js_files:
            # encoding random set of js two files
            from staticcomp.compressor import JsPayload
            payload = JsPayload(list(js_files), 'random')
            b64, hash = payload.encode()

class TestCompress(JsCompTestCase):
    js = """
        var _gaq = _gaq || []; _gaq.push(['_setAccount', 'UA-5-1']); _gaq.push(['_trackPageview']); 
	(function() {var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
	ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
	(document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(ga);})();    
    """
    
    def test_cache(self):
        cache.set("a", True)
        self.assertEquals(cache.get("a"), True, "The Django cache is not working")

    def test_processing(self):
        from staticcomp.compressor import JsCompressor
        # first init uncached
        j = JsCompressor(self.js)
        data = j.compress_code()
        self.assertEqual(self.js, data)
        
        # second call returns data in process
        cached_data = j.compress_code()
        self.assertTrue(bool(processing_re.search(cached_data)))
        
    def test_compress(self):
        from staticcomp.compressor import JsCompressor
        import time
        limit = 100 # 10 seconds
        count = 0
        j = JsCompressor(self.js)
        j.compress_code()
        while processing_re.search(j.compress_code()):
            time.sleep(.1)
            count += 1
            if count > limit:
                self.fail("Data not compressed within 10 seconds")
        
        self.assertTrue(bool(compressed_re.search(j.compress_code())), True)

