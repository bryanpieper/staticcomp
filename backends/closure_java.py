"""
Google Closure Commandline Compiler backend for the javascript compression. 

The command line app uses the "lib/compiler.jar" by default. You can specify your
own version via the Django settings.

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
import os

from staticcomp.compressor import CompressorService, CodeCompressorThread


# Either WHITESPACE_ONLY, SIMPLE_OPTIMIZATIONS 
#  or ADVANCED_OPTIMIZATIONS (the advanced option is not recommended for this usage)
COMPILATION_LEVEL = getattr(settings, 'JSCOMP_OPTIMIZATION', 'SIMPLE_OPTIMIZATIONS')



class GoogleClosureCommand(CompressorService):
    """
    Java command line app for the Google Closure Compiler. 
    More info at http://code.google.com/closure/compiler/docs/gettingstarted_app.html
    """
    def __init__(self, *args, **kwargs):
        super(GoogleClosureCommand, self).__init__(*args, **kwargs)
        self.java_cmd = getattr(settings, 'JAVA_CMD', 'java')
        self.closure_jar = getattr(settings, 
                                   'JSCOMP_CLOSURE_JAR_FILE', 
                                   os.path.normpath(os.path.join(os.path.dirname(__file__), 'lib/compiler.jar')))        

    def compress_string(self, data):
        closure_cmd = "{java} -jar {jar} --compilation_level {level} {debug}".format(java=self.java_cmd,
                                                                                     jar=self.closure_jar,
                                                                                     level=COMPILATION_LEVEL,
                                                                                     debug="--formatting PRETTY_PRINT" if settings.DEBUG else "")
        return self.apply_header(self.cmd(closure_cmd, data))



class GoogleClosureJavaThread(CodeCompressorThread):
    CompressorClass = GoogleClosureCommand


CompressorThread = GoogleClosureJavaThread
