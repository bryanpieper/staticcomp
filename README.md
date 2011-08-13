Staticcomp README - A Django JavaScript & CSS compressor/append framework
===============================================================
The staticcomp Django app is an on-demand JavaScript & CSS compression/append framework. The design goal is to allow you to build modular JavaScript/CSS
website and compress/append them on the fly. The app relies on your cache backend (ie. memcached) to store the compressed code.

If you are not running a cache backend (like memcached), this app is not for you. If you cannot connect up the cache backend to your frontend webserver
(ie. nginx, apache), this app is not for you.  Without a robust cache and the ability to offload the handling of the code cache to
your frontend, the benefits of this app are not realized. 

Staticcomp doesn't do the actually compression, it delegates to one of the configured backends. It comes with four backends, UglifyJS, 
Google Closure Java App, the Google Closure Service and pycssmin. The compression takes place in a separate Thread/Process to allow your 
pages to display without having to wait for the job to complete.  Depending on your deployment, you can configure whether you want
it to use Threads instead of Processes.

Benefits
-------
 -  Ability to compress/minify JS/CSS files on-demand
 -  Increase website performance by reducing the total number of JS/CSS file requests
 -  Build modular JS/CSS files by page / section instead of relying on large files
 -  No need to use date-based file names or query string values to force the browser to download changes to your JS/CSS files


Installation and Configuration
==============================

Copy the staticcomp directory to your PYTHONPATH.  The add staticcomp to your Django INSTALLED_APPS.

    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        #  ...
        'staticcomp',
    )


urls.py
-------
To enable the staticcomp framework, you need to specify the include in your urls.py:

    from django.conf.urls.defaults import *
    urlpatterns = patterns('',
        #  ...
        (r'', include('staticcomp.urls', namespace='staticcomp')),
    )

In the staticcomp/urls.py file, you'll find two urls; one for compression, one for appending. 

The append url will take the requested files and append them together. This function exists to combine already 
minified files. It is very unwise to re-minify files.

The compression url handles the compression requests. 


settings.py
-----------
Out of the box, staticcomp only requires two settings:
    
    MEDIA_ROOT
    SECRET_KEY
    
    # MEDIA_ROOT = '/home/django/webapp/static/'

staticcomp uses your MEDIA_ROOT to read the files. The SECRET_KEY is used to verify and sign the compression and append requests.

By default, staticcomp uses UglifyJS as the JavaScript compression backend.  To change the backend, specify the module using: 

    # to roll your own, look at the source of the existing backends
    JSCOMP_BACKEND = 'uglifyjs'  # available backends 'uglifyjs', 'closure_web', 'closure_java' 
    
By default, staticcomp uses cssmin as the CSS compression backend.

    CSSCOMP_BACKEND = 'pycssmin'  

Optional settings:
------------------
    STATICCOMP_CACHE_KEY = 'staticcomp_{group}_{hash}'                                # a python2.6+ string format used as the frontend code cache key
    STATICCOMP_EXPAND = False                                                         # tells the tags to write out the css and js elements as static files in the HTML (useful for debugging the raw files as-is)
    STATICCOMP_DISABLE = False                                                        # turn off the compression, the urls still work, but compression is no longer performed and the code isn't cached
    STATICCOMP_HEADER = lambda: name, dt: "/* {name} \n   Compressed: {now} */\n"     # callable pre-pended to compressed files, has two arguments (name, datetime)
    STATICCOMP_CACHE_SECONDS = 60 * 60 * 24 * 365                                     # default of 1 year
    STATICCOMP_USE_THREADS = False                                                    # by default, uses multiprocessing.Process, depends on your deployment requirements. Set to True for the runserver command

Backend settings (optional):
---------------------------
The following settings are available depending on your selected backends.

UglifyJS:

    NODEJS_CMD = 'node'                           # the path to node.js executable
    JSCOMP_UGLIFY = 'lib/UglifyJS/bin/uglifyjs'   # the location of your uglifyjs bin script

Google Closure Compiler:

    # both closure backends
    JSCOMP_OPTIMIZATION = 'SIMPLE_OPTIMIZATIONS'
    
    # closure_web: closure web service (http://closure-compiler.appspot.com/)
    USER_AGENT = 'Mozilla ...'                    # uses the URL_VALIDATOR_USER_AGENT if USER_AGENT is not specified
    
    # closure_java: closure command line app
    JAVA_CMD = 'java'                             # path to the java executable
    JSCOMP_CLOSURE_JAR_FILE = 'lib/compiler.jar'  # the location of the closure jar file


Cache backend considerations
----------------------------
The default key size for memcached is 250 characters. The app will generate a url with both the base64 value
and the md5 value. The md5 value is used for the cache key to ensure the key length is under 250 while still providing
the necessary data in the URL.


Nginx configuration
-------------------
The critical component is the webserver integration. Without this, all of the compressed files will be served from the Python
interpreter (not ideal). As stated above, if you do not have a webserver (ie. apache or nginx) that can connect to your cache
backend, then this app is not for you.

The following example demonstrates the serving of the compressed and appended files from memcached via Nginx (0.8.x/1.0.x).

    server {
        listen       80;
        server_name  domain.com;

        # JavaScript
        location ~ ^/j/([A-Za-z0-9]+)/([A-Za-z0-9=]+)/[ac]/([0-9a-fA-F]+).js {   
            # The regex arguments does not work on 0.7.x or earlier.
            # the expiration is here to tell the browser not to bother requesting the url again as the url will change
            # when the javascript files change.
            expires 365d;
            
            # if you need to use a different key, change the STATICCOMP_CACHE_KEY key format
            # based on the above regex, the first (group) and third (hash) regex group are used as the 
            # memcached key. the base64 value is not used because it can exceed 250 chars. The base64 value
            # is used by the python views if the value isn't in the cache.
            
            # Django 1.2:
            set $memcached_key  staticcomp_$1_$3;
            # OR
            # Django 1.3:
            set $memcached_key  :1:staticcomp_$1_$3;
            
            # memcached sock/port
            memcached_pass      127.0.0.1:11211;
            default_type        application/javascript;
            error_page          500 404 405 = @django;
        }
        
        # CSS
        location ~ ^/c/([A-Za-z0-9]+)/([A-Za-z0-9=]+)/[ac]/([0-9a-fA-F]+).css {
            # see notes above
            expires 365d;
            
            # Django 1.2:
            set $memcached_key  staticcomp_$1_$3;
            # OR
            # Django 1.3:
            set $memcached_key  :1:staticcomp_$1_$3;

            # memcached sock/port
            memcached_pass      127.0.0.1:11211;
            default_type        text/css;
            error_page          500 404 405 = @django;
        }

        location @django {
            # django conf ...
        }

        # ... the rest of your webserver conf
    }


staticomp Usage
===============
The static tags are the primary way to use the app. The tags build a queue of files to compress/append and then
output one or more urls. The tags don't actually do the compression. They create the url that the user's browser requests
that handles the compression. 

JavaScript compression
----------------------

    {% load jscomp_tags %}
    {% jscompfile group_name rel/path/to/js_file.js [compress|append] %}
    {% jscompoutput %} 
    
The order is important. The {% jscompoutput %} tag must be last to be rendered by the Django template system.

CSS compression
---------------
Just like the JavaScript compression, there are two main tags:

    {% load csscomp_tags %}
    {% csscompfile agroup css/html5.css %}
    {% csscompoutput %}
    
The order is important. The {% csscompoutput %} tag must be last to be rendered by the Django template system.

JavaScript Example
------------------
If you wanted to compress two JS files and append two JS files:

    {% load jscomp_tags %}
    {% jscompfile base js/file1.js %}
    {% jscompfile base js/file2.js %}
    
    {% jscompfile common js/jquery-1.5.1-min.js append %}
    {% jscompfile common js/swfobject-min.js append %}
    
    {% jscompoutput %}

If you wanted to compress a block of embedded JavaScript:

    {% jscompcode %}
    <script type="text/javascript">
    // ... some javascript
    </script>
    {% endjscompcode %}
    
This tag operates just like the url requests. It will call the Process/Thread to queue the compression. It will display the code as-is
until the compression completes. It can handle multiple <script /> blocks.
   
CSS Example
-----------
If you wanted to compress two CSS files (you can also append just like above):

    {% load csscomp_tags %}
    {% csscompfile blog css/blog/blog.css %}
    {% csscompfile blog pygments/friendly.css %}
    
    {% csscompoutput %}


URL Structure
-------------
The group name given as the first argument (in the above examples) determines which files will be grouped together into the url. The second argument is the relative path 
to the actual file, which must exist in your MEDIA_ROOT. The optional third argument is the action; compress or append. 
You can use the same group name for the either action because the output tags will use a different url for each group/action and content type.

The output tag the url structure as defined in staticcomp/urls.py as follows:
    <!-- JS (one for each file) -->
    <script type="text/javascript" src="/j/[group_name]/[base64_encoded_value]/[action]/[md5].js"></script>
    
    <!-- CSS (single block) -->
    <style type="text/css">
        @import url(/c/[group_name]/[base64_encoded_value]/[action]/[md5].css);
    </style>


Compression Request
-------------------
When the browser requests the file, it is either returned from the frontend webserver/cache or the action is queued for compression while returning
the uncompressed data. During the compression, the uncompressed script is cached and will be served from the frontend/cache. Once the 
compression completes, the cache is updated.

Manually execute the compression
--------------------------------
To manually run the compressor, use the following example:

    from staticcomp.compressor import JsCompressor   # for css use the CssCompressor
    
    # js_data is a string value of one or more files
    js_compressor = JsCompressor(js_data, cache_key='cache_key_value')
    js_compressor.init()
    
    # this will queue the (Thread/Process) compression or return the existing compressed js from the cache 
    js_code = js_compressor.compress_code()

