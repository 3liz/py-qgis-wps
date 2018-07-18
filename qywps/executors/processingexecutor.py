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

from qywps.executors import PoolExecutor, ExecutorError
from qywps.utils.qgis import start_qgis_application, setup_qgis_paths
from qywps.utils.lru import lrucache
from qywps.utils.processing import (import_providers_modules, 
                                    register_providers, 
                                    load_styles)

from qywps.app.Common import MapContext

LOGGER = logging.getLogger("QYWPS")

import qywps.configuration as config

class ProcessingProviderNotFound(ExecutorError):
    pass


class ProcessingExecutor(PoolExecutor):

    def __init__( self ):
        super(ProcessingExecutor, self).__init__()
        self._providers = []
        self.PROVIDERS  = []
        self._loaded_providers = []
        self._context_processes = lrucache(50)

    def initialize( self, processes ):
        """ Initialize executor
        """
        self._config = config.get_config('processing')
        self.importproviders()
        self.loadstyles()

        super(ProcessingExecutor, self).initialize(processes)

    def loadstyles(self):
        """ Load styles definitions
        """
        providers_path = self._config.get('providers_module_path','')
        try:
            load_styles(providers_path, logger=LOGGER)
        except Exception:
            LOGGER.error("Failed to load styles:\n%s", traceback.format_exc())

    def importproviders(self):
        """ Import algorithm providers

            The method will look for a __algorithms__.py file where all providers 
            modules should be imported
        """
        providers_path = self._config.get('providers_module_path','')
        try:
            setup_qgis_paths()            
            self._providers = import_providers_modules(providers_path, logger=LOGGER)
        except FileNotFoundError as exc:
            LOGGER.warn("%s not found" % exc)

    def worker_initializer(self):
        """ Worker initializer
        """
        super(ProcessingExecutor, self).worker_initializer()
        # Init qgis application in worker
        self.start_qgis(main_process=False)
  
    def start_qgis(self, main_process):
        """ Set up qgis
        """
        # Init qgis application
        self.qgisapp = start_qgis_application( enable_processing=True, 
                                verbose=config.get_config('logging').get('level')=='DEBUG', 
                                logger=LOGGER, logprefix="[qgis:%s]" % os.getpid())

        self.PROVIDERS.extend(register_providers(provider_classes=self._providers)) 
        return self.qgisapp

    def install_processes(self, processes ):
        """ Install processinf processes

            This method is called by initialize()
        """
        super().install_processes(processes)

        # XXX We do not want to start a qgis application in the main process
        # So let's initialize the processes list in a child process
        providers = self._config.get('providers')
        if providers:
            providers = providers.split(',')
            qgs_processes = self._pool.apply(self._qgis_processes, args=(providers,))
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
            from qywps.executors.processingprocess import QgsProcess
            context = MapContext(map_uri).update_context(context)
            return [QgsProcess.createInstance(ident,map_uri=map_uri, **context) for ident in identifiers]
        except:
            traceback.print_exc()
            raise

    @staticmethod
    def _qgis_processes(providers):

        # Install processes from processing providers
        from qywps.executors.processingprocess import QgsProcess
        from qgis.core import QgsApplication

        processingRegistry = QgsApplication.processingRegistry()
        processes = {}

        LOGGER.info("Installing processes from providers %s" % providers)
        for provider_id in providers:
            LOGGER.debug("Loading processing algorithms from provider '%s'", provider_id)
            provider = processingRegistry.providerById(provider_id)
            if not provider:
                raise ProcessingProviderNotFound(provider_id)
            processes.update({ alg.id():QgsProcess( alg ) for alg in provider.algorithms()})

        LOGGER.info("Published processes:\n * %s", "\n * ".join(sorted(processes.keys())))
        return processes

