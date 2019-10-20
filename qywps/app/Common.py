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

from pathlib import Path
from urllib.parse import urlparse

from qywps import configuration

LOGGER = logging.getLogger('SRVLOG')


class Metadata:
    """
    ows:Metadata content model.

    :param title: Metadata title, human readable string
    :param href: fully qualified URL
    :param type_: fully qualified URL
    """

    def __init__(self, title, href=None, type_='simple'):
        self.title = title
        self.href = href
        self.type = type_

    def __iter__(self):
        yield '{http://www.w3.org/1999/xlink}title', self.title
        if self.href is not None:
            yield '{http://www.w3.org/1999/xlink}href', self.href
        yield '{http://www.w3.org/1999/xlink}type', self.type


class MapContext:
    """ Hold context regarding the MAP parameter
    """
    
    def __init__(self, map_uri=None):
        config       = configuration.get_config('cache')
        self.rootdir = Path(config['rootdir'])
        if map_uri is None:
                map_uri = '/'
        self.map_uri    = urlparse(map_uri)
        self.projectdir = MapContext.resolve_path(self.rootdir, os.path.dirname(self.map_uri.path))

    def update_context( self, context ):
        """ Update a configuration context
        """
        context['rootdir']    = self.rootdir.as_posix()
        context['projectdir'] = self.projectdir.as_posix()
        context['project']    = self.map_uri.path
        return context

    @staticmethod
    def resolve_path( rootdir, path, check=False ):
        """ Return the full path of a file if that file
            exists in the project root director.

            The method will ensure that path is relative to 
            the the cache root directory
        """
        # XXX Resolve do not support 'strict' with python 3.5
        #path = Path('/'+path).resolve(strict=False)
        path  = Path(os.path.normpath('/'+path))
        path = (rootdir / path.relative_to('/'))
        if check and not path.exists():
            raise FileNotFoundError(path.as_posix())
        return path


        
