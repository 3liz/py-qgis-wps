#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original parts are Copyright 2016 OSGeo Foundation,            
# represented by PyWPS Project Steering Committee,               
# and released under MIT license.                                
# Please consult PYWPS_LICENCE.txt for details
#

import os
import logging
import tornado.httpclient as httpclient

from pyqgiswps.version import __version__
from pyqgiswps.exceptions import FileSizeExceeded, NoApplicableCode

LOGGER = logging.getLogger('SRVLOG')

USER_AGENT = "QYWPS Server %s" % __version__


def openurl( url: str, filename: os.PathLike, max_bytes: int=0, **kwargs ) -> None:
    """ Open url
    """
    LOGGER.info("Fetching URL %s", url)
    
    num_bytes=0
    fail = False
    try:
        with open(filename,'wb') as fh:

            def _callback( chunk: bytes ) -> None:
                nonlocal num_bytes
                num_bytes += len(chunk)
                if num_bytes > max_bytes:
                    raise FileSizeExceeded('File size for input exceeded for ref %s', url)
                fh.write(chunk)

            client = httpclient.HTTPClient()
            try:
                client.fetch(url, user_agent=USER_AGENT, streaming_callback=_callback,
                             **kwargs)
            except Exception as e:
                fail = True
                raise NoApplicableCode("File Reference error %s: %s", url, str(e))
            finally:
                client.close()
    finally:
        if fail and os.path.exists(filename):
            os.unlink(filename)

