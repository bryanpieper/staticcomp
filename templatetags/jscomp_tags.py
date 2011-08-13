"""
JavaScript compression and appending tags.

{% load jscomp_tags %}

The `jscompfile` tag handles the queuing of a JavaScript file for either compression or appending. The tag takes two arguments, 
a group and the relative file name to MEDIA_ROOT. There is a 3rd optional argument which is the action, either compress or append. 

The tag doesn't actually perform the action, it create the JavaScript URL that will perform the action.

  {% jscompfile agroup js/thepiepers.js %}
  {% jscompfile agroup js/thepiepers2.js %}
  {% jscompfile agroup js/jquery-min.js append %}
  
Be sure not to compress JavaScript files that are already compressed (or minimized). For those scripts, you can use the append action
to concat the files to preserve the code.

The files are queued in order of processing and combined by the name of the group. After the files are queued, output 
the compression <script /> elements using the `jscompoutput` (must be called after the jscompfile tags).

{% jscompoutput %}

The jscompoutput will output a script tag for each group like the following:

  <script type="text/javascript" src="/j/agroup/anMvdGhlcGllcGVycy5qcyw0YjI3YTBmZGZlYTBmMzNkZGE3NzAwNmY3ODVkNzk0MTZlOWNlYjVhNDExNTc5MzEwMmQzMGVlYTU5ZWNkNmUwLDEyOTU4MzE5Mjg=/c/fbc386e44e64dd219f760b75227aba43eca638c9/"></script>

The end of the URL will be either /c/ or /a/. /c/ is the compression url and /a/ is the append url.

There is an additional tag that will compress and cache an inline script block.

  {% jscompcode %}
  <script type="text/javascript">
  // ... some javascript
  </script>
  {% endjscompcode %}
  
The block will be compressed using the same parameters as files and will be updated when it changes.

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
from django.utils.datastructures import SortedDict
from django.conf import settings

from HTMLParser import HTMLParser
from StringIO import StringIO
import os

from staticcomp.compressor import JsCompressor, JsPayload, media_root
from staticcomp.templatetags import BaseOutputNode, group_re


register = template.Library()


compressed_script = """
<script type="text/javascript">
{script}
</script>
"""


class ScriptBlockHtmlParser(HTMLParser):
    """
    Parses out any <script> tags. Will allow for any number of <script> blocks to ensure
    for a clean compile.
    """
    def handle_data(self, data):
        if not hasattr(self, '_js_data'):
            self._js_data = StringIO()
        if data:
            self._js_data.write(data)
    
    @property
    def js_data(self):
        buf = getattr(self, '_js_data', None)
        if buf:
            return buf.getvalue()


class JsCompNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    
    def render(self, context):
        orig_script = self.nodelist.render(context)
        if not orig_script:
            return ""
        
        # staticcomp kill switch
        if getattr(settings, 'STATICCOMP_DISABLE', False):
            return orig_script
        
        script_parser = ScriptBlockHtmlParser()
        script_parser.feed(orig_script)
        data = script_parser.js_data
        if data:
            js_compressor = JsCompressor(data=data)
            js_compressor.init()
            compressed_code = js_compressor.compress_code()
            return compressed_script.format(script=compressed_code)
        return orig_script       

@register.tag
def jscompcode(parser, token):
    """
    Compress and cache an inline javascript block. Will update when the 
    JS code changes.
    
    {% jscompcode %}
      <script type="text/javascript">
      // ...
      </script>
    {% endjscompcode %}
    """
    nodelist = parser.parse(('endjscompcode',))
    parser.delete_first_token()
    return JsCompNode(nodelist)


class JsFileNode(template.Node):
    def __init__(self, group, name, js_file, action='compress'):
        self.group = group
        self.name = name
        self.js_file = js_file
        self.action = action
    
    def render(self, context):
        key_name = 'jscomp_groups_compress'
        if self.action == 'append':
            key_name = 'jscomp_groups_append'
        
        if key_name not in context.render_context:
            context.render_context[key_name] = SortedDict()
        js_groups = context.render_context[key_name]
        if self.group not in js_groups:
            js_groups[self.group] = []
        js_groups[self.group].append(self.name)
        # this tag has no output, just appends script to internal context
        return ""

@register.tag
def jscompfile(parser, token):
    """
    Adds a JavaScript file to the compression/append queue. Each file is stored by group and in the order 
    they are parsed by the Django template engine.
    
    The javascript file is relative to the MEDIA_ROOT
      {% jscompfile agroup js/jquery-1.5.js %}
    
    Note: The group name is an alphanumeric value used in the url. The group name is the key that keeps files together.
    
    You may also specify an alternate action. The example below will append instead of compress.
      {% jscompfile agroup js/thepiepers.js append %}
    
    """
    action = 'compress'
    try:
        tokens = token.split_contents()
        tag_name, group, name = tokens[:3]
        if len(tokens) == 4:
            action = tokens[3].lower().strip('"\'')
            if action not in ('compress', 'append'):
                raise template.TemplateSyntaxError("The only available options are 'compress' and 'append'")
    except template.TemplateSyntaxError:
        raise
    except:
        raise template.TemplateSyntaxError("The jscompfile tag requires a group name a relative path in the MEDIA_ROOT for a JavaScript file")
    if not group_re.match(group):
        raise template.TemplateSyntaxError("The group name can only be an alpha numeric value")
    
    js_file = media_root(name)
    if not os.path.exists(js_file):
        raise template.TemplateSyntaxError("The file {0} does not exist".format(js_file))
    if not os.path.splitext(name)[-1].lower() in ('.js',):
        raise template.TemplateSyntaxError("The file {0} is not a JavaScript file".format(js_file))
    return JsFileNode(group, name, js_file, action)



js_script = '<script type="text/javascript" src="{0}"></script>\n'

class JsOutputNode(BaseOutputNode):
    keys = (
        ('jscomp_groups_compress', 'staticcomp:compressed_js'),
        ('jscomp_groups_append', 'staticcomp:append_js')
    )

    def output_keys(self):
        for k in self.keys:
            yield k 
    
    def payload_klass(self):
        return JsPayload
    
    def output_format(self, path):
        return js_script.format(path)    


@register.tag
def jscompoutput(parser, token):
    """
    Output the appended JavaScript blocks. This tag calculates the
    javascript file signatures based on the group, filename, timestamp and secret.
    
    {% jscompoutput %}
    """
    return JsOutputNode()

