"""
CSS compressor tags.

{% csscompfile [group] [css_file] %}

{% csscompoutput %}

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

import os

from staticcomp.compressor import CssPayload, media_root
from staticcomp.templatetags import BaseOutputNode, group_re

register = template.Library()


class CssFileNode(template.Node):
    def __init__(self, group, name, css_file, action='compress'):
        self.group = group
        self.name = name
        self.css_file = css_file
        self.action = action
    
    def render(self, context):
        key_name = 'csscomp_groups_compress'
        if self.action == 'append':
            key_name = 'csscomp_groups_append'
        
        if key_name not in context.render_context:
            context.render_context[key_name] = SortedDict()
        css_groups = context.render_context[key_name]
        if self.group not in css_groups:
            css_groups[self.group] = []
        css_groups[self.group].append(self.name)
        # this tag has no output, just appends css to internal context
        return ""


@register.tag
def csscompfile(parser, token):
    """
    Adds a CSS file to the compression/append queue. Each file is stored by group and in the order 
    they are parsed by the Django template engine.
    
    The css file is relative to the MEDIA_ROOT
      {% csscompfile agroup css/html5.css %}
    
    Note: The group name is an alphanumeric value used in the url. The group name is the key that keeps files together.
    
    You may also specify an alternate action. The example below will append instead of compress.
      {% csscompfile agroup css/html5.css append %}
    
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
        raise template.TemplateSyntaxError("The csscompfile tag requires a group name a relative path in the MEDIA_ROOT for a CSS file")
    if not group_re.match(group):
        raise template.TemplateSyntaxError("The group name can only be an alpha numeric value")
    
    css_file = media_root(name)
    if not os.path.exists(css_file):
        raise template.TemplateSyntaxError("The file {0} does not exist".format(css_file))
    if not os.path.splitext(name)[-1].lower() in ('.css',):
        raise template.TemplateSyntaxError("The file {0} is not a CSS file".format(css_file))
    return CssFileNode(group, name, css_file, action)




css_block = '<style type="text/css">\n{0}</style>'
css_import_stmt = "  @import url({0});\n"


class CssOutputNode(BaseOutputNode):
    keys = (
        ('csscomp_groups_compress', 'staticcomp:compressed_css'),
        ('csscomp_groups_append', 'staticcomp:append_css')
    )

    def output_keys(self):
        for k in self.keys:
            yield k 
    
    def payload_klass(self):
        return CssPayload
    
    def output_format(self, path):
        return css_import_stmt.format(path)   

    def render(self, context):
        # wraps the css imports with a style tag
        buf = super(CssOutputNode, self).render(context)
        return css_block.format(buf)


@register.tag
def csscompoutput(parser, token):
    """
    Output the appended CSS. This tag calculates the
    css file signatures based on the group, filename, timestamp and secret.
    
    {% csscompoutput %}
    """
    return CssOutputNode()
