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

from qgis.core import (QgsProcessingContext, 
                       QgsProject, 
                       QgsMapLayer)

from pyqgiswps.qgscache.cachemanager import cacheservice
from pyqgiswps.config import confservice

from typing import Mapping,Any,Optional 

LOGGER = logging.getLogger('SRVLOG')


class MapContext:
    """ Hold context regarding the MAP parameter
    """
    def __init__(self, map_uri: Optional[str]=None):
        self.rootdir = Path(confservice.get('projects.cache','rootdir'))
        self.map_uri = map_uri

    @property
    def create_context(self) -> Mapping[str, Any]:
        """ Update a configuration context
        """
        context = dict(rootdir = str(self.rootdir))
        if self.map_uri is not None:
            context['project_uri'] = self.map_uri
        return context

    def project(self) -> QgsProject:
        if self.map_uri is not None:
            return cacheservice.lookup(self.map_uri)[0]
        else:
            raise RuntimeError('No map defined')


class ProcessingContext(QgsProcessingContext):

    def __init__(self, workdir: str, map_uri: Optional[str]=None) -> None:
        super().__init__()
        self.workdir = workdir
        self.rootdir = Path(confservice.get('projects.cache','rootdir'))

        if map_uri is not None:
            self.map_uri = map_uri
            self.setProject(cacheservice.lookup(map_uri)[0])
        else:
            LOGGER.warning("No map url defined, inputs may be incorrect !")
            self.map_uri = None

        # Create the destination project
        self.destination_project = QgsProject()

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
        except Exception:
            LOGGER.error(traceback.format_exc())
            raise

    def write_result(self, workdir: str, name: str, wmsurl: Optional[str]=None) -> bool:
        """ Save results to disk
        """
        LOGGER.debug("Writing Results to %s", workdir)

        project = self.destination_project

        # Set project settings
        if wmsurl:
            project.writeEntry('WMSUrl','/',wmsurl)

        def _layers_for( layertype ):
            return (lid for lid,lyr in project.mapLayers().items() if lyr.type() == layertype)

        # Publishing vector layers in WFS and raster layers in WCS
        project.writeEntry( "WFSLayers", "/", list(_layers_for(QgsMapLayer.VectorLayer)) )
        project.writeEntry( "WCSLayers", "/", list(_layers_for(QgsMapLayer.RasterLayer)) )

        for lid in _layers_for(QgsMapLayer.VectorLayer):
            project.writeEntry( "WFSLayersPrecision", "/"+lid, 6 )

        return project.write(os.path.join(workdir,name+'.qgs'))

