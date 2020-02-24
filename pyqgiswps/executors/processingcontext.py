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
from urllib.parse import urlparse, ParseResult

from qgis.core import (QgsProcessingContext, QgsProject)

from pyqgiswps.utils.filecache import FileCache
from pyqgiswps.utils.decorators import singleton

from pyqgiswps import config
from pyqgiswps.exceptions import InvalidParameterValue

from qgis.core import (QgsProject, QgsMapLayer)

LOGGER = logging.getLogger('SRVLOG')

from typing import Tuple, Union, Mapping, Any


def _get_protocol_path(scheme: str) -> Path:
    """ Resolve path with protocol 'scheme'
    """
    LOGGER.error('Unsupported protocol %s' % scheme)
    raise FileNotFoundError(scheme)


def _resolve_path( key: str, rootdir: Path ) -> Path:
    """ Resolve path from key uri
    """
    key = urlparse(key)
    if not key.scheme or key.scheme == 'file':
        rootpath = rootdir
    else:
        rootpath = _get_protocol_path(key.scheme)

    # XXX Resolve do not support 'strict' with python 3.5
    # see https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve
    #path = Path('/'+key.path).resolve(strict=False).relative_to('/')
    path = Path(os.path.normpath('/'+key.path)).relative_to('/')
    path = rootpath / path
    for sfx in ('.qgs','.qgz'):
        path = path.with_suffix(sfx)
        if path.exists():
            break
    else:
        raise FileNotFoundError(str(path))

    return path



@singleton
class _Cache(FileCache):

    def __init__(self) -> None:
        cfg       = config.get_config('cache')
        cachesize = cfg.getint('size')
        rootdir   = Path(cfg['rootdir'])

        if not rootdir.exists():
            raise FileNotFoundError(str(rootdir))
        if not rootdir.is_absolute():
            raise ValueError("cache rootdir must be an absolute path: found %s" % rootdir)

        class _Store:
            def getpath(self, key: str) -> Tuple[str, datetime]:
                path = _resolve_path(key, rootdir)
                timestamp = datetime.fromtimestamp(path.stat().st_mtime)
                return str(path), timestamp

        self.rootdir = rootdir

        # Init FileCache
        super().__init__(size=cachesize, store=_Store())

    def on_cache_update(self, key: str, path: str ):
        """ Called when cache is updated
        """
        LOGGER.debug("Updated project cache key=%s path=%s", key, path)

    def resolve_path(self, key: str ) -> Path:
        return _resolve_path(key, self.rootdir)


def cache_lookup( uri: str ) -> QgsProject:
    c = _Cache()
    return c.lookup(uri)


class MapContext:
    """ Hold context regarding the MAP parameter
    """
    def __init__(self, map_uri: str=None, **create_context):
        c = _Cache()
        self.rootdir = c.rootdir
        self.map_uri = map_uri
        self._create_context = create_context

    @property
    def create_context(self) -> Mapping[str, Any]:
        """ Update a configuration context
        """
        context = dict(self._create_context)
        context['rootdir'] = self.rootdir.as_posix()
        if self.map_uri is not None:
            context['project_uri'] = _Cache().resolve_path(self.map_uri).as_posix()
        return context

    def project(self) -> QgsProject:
        if self.map_uri is not None:
            return cache_lookup(self.map_uri)
        else:
            raise RuntimeError('No map defined')


class ProcessingContext(QgsProcessingContext):

    def __init__(self, workdir: str, map_uri: str=None) -> None:
        super().__init__()
        self.workdir = workdir

        if map_uri is not None:
            self.map_uri = map_uri
            self.setProject(cache_lookup(map_uri))
        else:
            LOGGER.warning("No map url defined, inputs may be incorrect !")
            self.map_uri = None

        # Create the destination project
        self.destination_project = QgsProject()

    @property
    def rootdir(self) -> Path:
        """ Return the rootdir for all projects
        """
        return _Cache().rootdir

    def resolve_path( self, path: str ) -> str:
        """ Return the full path of a file if that file
            exists in the project dir.

            The method will ensure that path is relative to 
            the the cache root directory
        """
        try:
            # XXX Resolve do not support 'strict' with python 3.5
            #path = Path('/'+path).resolve(strict=False)
            path = Path(os.path.normpath('/'+path)).relative_to('/')
            path = self.rootdir / path
            if not path.exists():
                raise FileNotFoundError(path.as_posix())
            return path
        except:
            LOGGER.error(traceback.format_exc())
            raise

    def write_result(self, workdir: str, name: str) -> bool:
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

