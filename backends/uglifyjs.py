"""
Uglify compiler. Specify the NODEJS_CMD to change out node.js bin command.

Source files are located in lib. You can override the UglifyJS bin with JSCOMP_UGLIFY

https://github.com/mishoo/UglifyJS
http://nodejs.org/

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
import os

from staticcomp.compressor import CompressorService, CodeCompressorThread



class UglifyJSCommand(CompressorService):
    """
    UglifyJS JavaScript compiler. Required node.js to run. 
    https://github.com/mishoo/UglifyJS
    """
    def __init__(self, *args, **kwargs):
        super(UglifyJSCommand, self).__init__(*args, **kwargs)
        self.nodejs_cmd = getattr(settings, 'NODEJS_CMD', 'node')
        self.uglifyjs = getattr(settings, 
                                'JSCOMP_UGLIFY', 
                                os.path.normpath(os.path.join(os.path.dirname(__file__), 'lib/UglifyJS/bin/uglifyjs')))    

    def compress_string(self, data):
        uglifyjs_cmd = "{node} {bin} {debug} --unsafe --max-line-len 4096".format(node=self.nodejs_cmd,
                                                                                  bin=self.uglifyjs,
                                                                                  debug="--beautify" if settings.DEBUG else "")
        return self.apply_header(self.cmd(uglifyjs_cmd, data))



class UglifyJSThread(CodeCompressorThread):
    CompressorClass = UglifyJSCommand

# hook for jscomp
CompressorThread = UglifyJSThread
