#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Qgis executor

    The qgis executor publish processing algorithms to
    as wps service. 

    Only processes from selected  providers can be published 
"""
import os
import sys
import logging
import json
import traceback

from pyqgiswps.executors.pool import PoolExecutor, ExecutorError, UnknownProcessError
from pyqgiswps.utils.qgis import start_qgis_application, setup_qgis_paths, init_qgis_processing
from pyqgiswps.utils.lru import lrucache
from pyqgiswps.utils.plugins import WPSServerInterfaceImpl
from pyqgiswps.app.Common import MapContext

LOGGER = logging.getLogger('SRVLOG')

from pyqgiswps import config

class ProcessingProviderNotFound(ExecutorError):
    pass


class ProcessingExecutor(PoolExecutor):

    worker_instance = None

    def __init__( self ):
        super(ProcessingExecutor, self).__init__()
        self._plugins = []
        self._context_processes = lrucache(50)

    def initialize( self, processes ):
        """ Initialize executor
        """
        self._config = config.get_config('processing')

        plugin_path = self._config.get('providers_module_path')
        expose_scripts = self._config.getboolean('expose_scripts')
        
        setup_qgis_paths()  

        self._wps_interface = WPSServerInterfaceImpl(plugin_path, with_scripts=expose_scripts)
        self._wps_interface.initialize()

        super(ProcessingExecutor, self).initialize(processes)

    def worker_initializer(self):
        """ Worker initializer
        """
        ProcessingExecutor.worker_instance = self

        super(ProcessingExecutor, self).worker_initializer()
        # Init qgis application in worker
        self.start_qgis(main_process=False)
  
    def start_qgis(self, main_process):
        """ Set up qgis
        """
        logprefix = "[qgis:%s]" % os.getpid()

        settings = {}

        # Set up processing script folder
        # XXX  If scripts folder is not set then ScriptAlgorithmProvider will crash !
        scripts_folders = self._config.get('scripts_folders')

        scripts_folders = scripts_folders.split(';')
        for folder in scripts_folders:
            if not os.path.isdir(folder):
                LOGGER.error("Script folder '%s' not found, disabling" ,folder) 

        scripts_folders = ';'.join( f for f in scripts_folders if os.path.isdir(f))
        if scripts_folders:
            LOGGER.info("Scripts folder set to %s", scripts_folders)
            settings["Processing/Configuration/SCRIPTS_FOLDERS"] = scripts_folders

        # Init qgis application
        self.qgisapp = start_qgis_application( enable_processing=True, 
                                verbose=config.get_config('logging').get('level')=='DEBUG', 
                                logger=LOGGER, logprefix=logprefix,
                                settings=settings)

        # Load plugins
        self._wps_interface.register_providers()
        LOGGER.info("%s QGis processing initialized" % logprefix)

        return self.qgisapp

    def install_processes(self, processes ):
        """ Install processing processes

            This method is called by initialize()
        """
        super().install_processes(processes)

        # XXX We do not want to start a qgis application in the main process
        # So let's initialize the processes list in a child process
        qgs_processes = self._pool.apply(self._create_qgis_processes)
        self.processes.update(qgs_processes)


    def get_processes( self, identifiers, map_uri=None, **context ):
        """ Override executors.get_process
        """
        try:
            processes = [self.processes[ident] for ident in identifiers]
        except KeyError as exc:
            raise UnknownProcessError(str(exc))

        # Create a new instance of a process for the given context
        # Contextualized processes are stored in lru cache
        _test = lambda p: (map_uri,p.identifier) not in self._context_processes

        if map_uri is not None:
            if any(_test(p) for p in processes):
                processes = self._pool.apply(self._create_contextualized_processes, 
                                             args=(identifiers,),
                                             kwds=(lambda **kw: kw)(map_uri=map_uri,**context))
                # Update cache
                for p in processes:
                    self._context_processes[(map_uri,p.identifier)] = p 
            else:
                # Get from cache
                processes = [self._context_processes[(map_uri,p.identifier)] for p in processes]
        return processes

    @staticmethod
    def _create_contextualized_processes( identifiers, map_uri, **context ):
        """ Create processes from context
        """
        try:
            from pyqgiswps.executors.processingprocess import QgsProcess
            context = MapContext(map_uri).update_context(context)
            return [QgsProcess.createInstance(ident,map_uri=map_uri, **context) for ident in identifiers]
        except:
            traceback.print_exc()
            raise

    @staticmethod
    def _create_qgis_processes():

        # Install processes from processing providers
        from pyqgiswps.executors.processingprocess import QgsProcess
        from qgis.core import QgsApplication

        processingRegistry = QgsApplication.processingRegistry()
        processes = {}

        iface = ProcessingExecutor.worker_instance._wps_interface

        for provider in iface.providers:
            LOGGER.debug("Loading processing algorithms from provider '%s'", provider.id())
            processes.update({ alg.id():QgsProcess( alg ) for alg in provider.algorithms()})

        if processes:
            LOGGER.info("Published processes:\n * %s", "\n * ".join(sorted(processes.keys())))
        else:
            LOGGER.warning("No published processes !")

        return processes

