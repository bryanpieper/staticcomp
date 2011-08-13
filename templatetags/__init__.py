"""
Base compression tags

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

from django import template
from django.conf import settings
from django.core.urlresolvers import reverse

from StringIO import StringIO
import os
import re

group_re = re.compile(r'[A-Za-z0-9]+')

if getattr(settings, 'STATICCOMP_EXPAND', False):

    class BaseOutputNode(template.Node):
        """
        Renders the static content as direct urls, no compression 
        """
        def output_keys(self):
            raise NotImplementedError()
        
        def payload_klass(self):
            raise NotImplementedError()
        
        def output_format(self, path):
            raise NotImplementedError()
        
        def render(self, context):
            buf = StringIO()
            buf.write("")
            
            # loop through the available actions and create the output statements for direct access
            for k, u in self.output_keys():
                if k in context.render_context:
                    file_groups = context.render_context[k]
                    for group, files in file_groups.items():
                        if files:
                            map(buf.write, [ self.output_format(os.path.join(settings.MEDIA_URL, f)) for f in files ])        
            return buf.getvalue()

else:
    
    class BaseOutputNode(template.Node):
        """
        Renders the compression urls
        """
        def output_keys(self):
            raise NotImplementedError()
        
        def payload_klass(self):
            raise NotImplementedError()
        
        def output_format(self, path):
            raise NotImplementedError()
        
        def render(self, context):
            buf = StringIO()
            buf.write("")
            
            # loop through the available actions and create the output statements for compression
            for k, u in self.output_keys():
                if k in context.render_context:
                    file_groups = context.render_context[k]
                    for group, files in file_groups.items():
                        if files:
                            payload = self.payload_klass()(files, group)
                            payload_url, payload_hash = payload.encode()
                            path = reverse(u, args=(group, payload_url, payload_hash))
                            buf.write(self.output_format(path))         
            return buf.getvalue()
