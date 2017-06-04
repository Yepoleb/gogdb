"""
Copyright (c) 2008, Michael Elsdörfer <http://elsdoerfer.name>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above
       copyright notice, this list of conditions and the following
       disclaimer in the documentation and/or other materials
       provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

# Taken from the latest master of webassets, because there hasn't been a
# release which includes it.

from __future__ import absolute_import
from webassets.filter import Filter


__all__ = ('RCSSMin',)

class RCSSMin(Filter):
    """Minifies CSS.

    Requires the ``rcssmin`` package (https://github.com/ndparker/rcssmin).
    Alike 'cssmin' it is a port of the YUI CSS compression algorithm but aiming
    for speed instead of maximum compression.
    """

    name = 'rcssmin'
    options = {
        'keep_bang_comments': 'RCSSMIN_KEEP_BANG_COMMENTS',
    }

    def setup(self):
        super(RCSSMin, self).setup()
        try:
            import rcssmin
        except ImportError:
            raise EnvironmentError('The "rcssmin" package is not installed.')
        else:
            self.rcssmin = rcssmin

    def output(self, _in, out, **kw):
        keep = self.keep_bang_comments or False
        out.write(self.rcssmin.cssmin(_in.read(), keep_bang_comments=keep))
