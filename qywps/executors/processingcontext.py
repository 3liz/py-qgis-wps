#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Wrapper around qgis processing context
"""
import os
import logging
import traceback

from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from qgis.core import (QgsProcessingContext,)
from qywps.utils.filecache import FileCache
from qywps.utils.decorators import singleton

from qywps import configuration
from qywps.exceptions import InvalidParameterValue

from qgis.core import (QgsProject, QgsMapLayer)

LOGGER = logging.getLogger('QYWPS')

@singleton
class _Cache(FileCache):

    def __init__(self):
        config    = configuration.get_config('cache')
        cachesize = config.getint('size')
        rootdir   = Path(config['rootdir'])

        if not rootdir.exists():
            raise FileNotFoundError(str(rootdir))
        if not rootdir.is_absolute():
            raise ValueError("cache rootdir must be an absolute path: found %s" % rootdir)

        class _Store:
            def getpath(self, key, exists=False):
                # XXX Security: strip leading/trailing slash
                key = key.strip('/')
                path = rootdir / key
                path = path.with_suffix('.qgs')
                if not path.exists():
                    raise FileNotFoundError(str(path))

                # Get modification time for the file
                timestamp = datetime.fromtimestamp(path.stat().st_mtime)
                return str(path), timestamp

        self.rootdir = rootdir

        # Init FileCache
        super().__init__(size=cachesize, store=_Store())

    def on_cache_update(self, key, path ):
        """ Called when cache is updated
        """
        LOGGER.debug("Updated project cache key=%s path=%s", key, path)



def cache_lookup( uri ):
    c = _Cache()
    return c.lookup(uri.path)

    
class Context(QgsProcessingContext):

    def __init__(self, workdir, map_uri=None):
        super().__init__()
        self.workdir = workdir

        if map_uri is not None:
            self.map_uri = urlparse(map_uri)
            self.setProject(cache_lookup(self.map_uri))
        else:
            LOGGER.warning("No map url defined, inputs may be incorrect !")
            self.map_uri = None

        # Create the destination project
        self.destination_project = QgsProject()

    @property
    def rootdir(self):
        return _Cache().rootdir

    def get_as_project_file( self, name ):
        """ Return the full path of a file if that file
            exists in the project cache dir.

            The method will ensure that path is relative to 
            the the cache root directory
        """
        try:
            # XXX Resolve do not support 'strict' with python 3.5
            #path = Path('/'+name).resolve(strict=False)
            path  = Path(os.path.normpath('/'+name))
            path = (self.rootdir / path.relative_to('/'))
            if path.is_file():
                return path.as_posix()
            else:
                LOGGER.error("File not found: %s", path.as_posix())
        except:
            LOGGER.error(traceback.format_exc())

        raise InvalidParameterValue(name)

    

    def write_result(self, workdir, name):
        """ Save results to disk
        """
        LOGGER.debug("Writing Results to %s", workdir)
        # Publishing vector layers in WFS and raster layers in WCS
        dest_project = self.destination_project
        dest_project.writeEntry( "WFSLayers", "/", [lid for lid,lyr in dest_project.mapLayers().items() if lyr.type() == QgsMapLayer.VectorLayer] )
        for lid,lyr in dest_project.mapLayers().items():
            if lyr.type() == QgsMapLayer.VectorLayer:
                dest_project.writeEntry( "WFSLayersPrecision", "/"+lid, 6 )
        dest_project.writeEntry( "WCSLayers", "/", [lid for lid,lyr in dest_project.mapLayers().items() if lyr.type() == QgsMapLayer.RasterLayer] )
        return dest_project.write(os.path.join(workdir,name+'.qgs'))

