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
from qywps.utils.imp import load_source

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

    def initialize( self, processes ):
        """ Initialize executor
        """
        self._config = config.get_config('processing')
        self.importproviders()
        self.loadstyles()

        super(ProcessingExecutor, self).initialize(processes)

    def loadstyles(self):
        """ Load styles definitions

            The json structure should be the following:

            {
                'algid': {
                    'outputname': file.qml
                    ...
                }
                ...
            {
        """
        providers_path = self._config.get('providers_module_path')
        if providers_path:
            filepath = os.path.join(providers_path,'styles.json')
            if not os.path.exists(filepath):
                return

        LOGGER.info("Found styles file description at %s", filepath)
        from processing.core.Processing import RenderingStyles
        try:
            with open(filepath,'r') as fp:
                data = json.load(fp)
                # Replace style name with full path
                for alg in data:
                    for key in data[alg]:
                        qml = os.path.join(providers_path,'qml',data[alg][key])
                        if not os.path.exists(qml):
                            LOGGER.warning("Style '%s' not found" % qml)
                        data[alg][key] = qml
                # update processing rendering styles
                RenderingStyles.styles.update(data)
        except Exception:
            LOGGER.error("Failed to load styles:\n%s", traceback.format_exc())

    def importproviders(self):
        """ Import algorithm providers

            The method will look for a __algorithms__.py file where all providers 
            modules should be imported 

            NOTE: this should be called before initialising QGIS application
            Import will be done automatically when initializing the procesing module
        """
        providers_path = self._config.get('providers_module_path')
        if providers_path:
            filepath = os.path.join(providers_path,'__algorithms__.py')
            if not os.path.exists(filepath):
                LOGGER.warn("%s not found" % filepath)
                return

            LOGGER.info("Loading algorithms providers from %s" % filepath)

            setup_qgis_paths()            
            sys.path.append(providers_path)
            # Load providers
            self._providers = load_source('wps_imported_algorithms',filepath).providers

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

        # Load providers explicitely
        from qgis.core import QgsApplication
        reg = QgsApplication.processingRegistry()
        for p in self._providers:
            c = p()
            # XXX Hold provider instance, processingRegistry does not gain ownership and
            # we must prevent garbage collection
            self.PROVIDERS.append(c)
            reg.addProvider(c)

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

