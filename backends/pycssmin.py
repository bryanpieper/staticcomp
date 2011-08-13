from staticcomp.compressor import CompressorService, CodeCompressorThread
from cssmin import cssmin


class PyCssMin(CompressorService):
    """
    Backend for cssmin 
    https://github.com/zacharyvoase/cssmin/blob/master/src/cssmin.py
    """
    def compress_string(self, data):
        return self.apply_header(cssmin.cssmin(data, 4096 * 2))


class PyCssMinThread(CodeCompressorThread):
    CompressorClass = PyCssMin


CompressorThread = PyCssMinThread