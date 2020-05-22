#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Qgis process factory

"""
import os
import logging
import traceback

from glob import glob
from itertools import chain

from pyqgiswps.utils.qgis import start_qgis_application, setup_qgis_paths, init_qgis_processing
from pyqgiswps.poolserver.server import create_poolserver
from pyqgiswps.utils.plugins import WPSServerInterfaceImpl

from pyqgiswps.config import confservice

from .logstore import logstore

LOGGER = logging.getLogger('SRVLOG')


class QgsProcessFactory:

    def __init__(self):
        self._initialized = False
        self.qgisapp = None

    def initialize(self):
        """ Initialize the factory

            Should be called once
        """
        assert not self._initialized

        self._config = confservice['processing']

        plugin_path       = self._config.get('providers_module_path')
        exposed_providers = self._config.get('exposed_providers',fallback='').split(',')

        setup_qgis_paths()

        self._wps_interface = WPSServerInterfaceImpl(plugin_path, with_providers=exposed_providers)
        self._wps_interface.initialize()

        self._create_pool()

    def _create_pool(self):
        """ Initialize the worker pool
        """
        cfg = confservice['server']
        
        maxparallel      = cfg.getint('parallelprocesses')
        processlifecycle = cfg.getint('processlifecycle')
        response_timeout = cfg.getint('response_timeout')
 
        # Initialize logstore (redis)
        logstore.init_session()
 
        # 0 mean eternal life
        if processlifecycle == 0:
            processlifecycle=None
 
        # Need to be initialized as soon as possible
        self._poolserver = create_poolserver( maxparallel, maxcycles = processlifecycle,
                                              initializer = self.worker_initializer,
                                              timeout     = response_timeout)
        self._initialized = True

    def create_contextualized_processes( self, identifiers, map_uri, **context ):
        """ Create processes from context
        """
        try:
            from pyqgiswps.executors.processingprocess import QgsProcess
            return [QgsProcess.createInstance(ident,map_uri=map_uri, **context) for ident in identifiers]
        except:
            traceback.print_exc()
            raise

    def create_qgis_processes(self):
        """
          Convert processing algorithms to WPS processes
        """
        self.start_qgis()

        # Install processes from processing providers
        from pyqgiswps.executors.processingprocess import QgsProcess
        from qgis.core import QgsApplication

        processingRegistry = QgsApplication.processingRegistry()
        processes = {}

        iface = self._wps_interface

        for provider in iface.providers:
            LOGGER.debug("Loading processing algorithms from provider '%s'", provider.id())
            processes.update({ alg.id():QgsProcess( alg ) for alg in provider.algorithms()})

        if processes:
            LOGGER.info("Published processes:\n * %s", "\n * ".join(sorted(processes.keys())))
        else:
            LOGGER.warning("No published processes !")

        # Return the list of processes
        return processes

    def worker_initializer(self):
        """ Worker initializer
        """
        # Init qgis application in worker
        self.start_qgis()
   
    def start_qgis(self):
        """ Set up qgis
        """
        # Do not intialize twice
        if self.qgisapp is not None:
            return

        logprefix = "[qgis:%s]" % os.getpid()

        settings = {
            "Processing/Configuration/PREFER_FILENAME_AS_LAYER_NAME":"false"      
        }

        def _folders_setting( setting, folders ):
            folders = folders.split(';')
            folders = chain( *(glob(f) for f in folders) )
            folders = ';'.join( f for f in folders if os.path.isdir(f) )
            if folders:
                LOGGER.info("%s = %s", setting, folders)
                settings[setting] = folders

        # Set up folder settings
        # XXX  Note that if scripts folder is not set then ScriptAlgorithmProvider will crash !
        for setting, value in confservice.items('qgis.settings.folders'):
            LOGGER.debug("*** Folder settings: %s = %s", setting, value) 
            _folders_setting(setting, value)

        # Load other settings from configuration file

        # Init qgis application
        self.qgisapp = start_qgis_application( enable_processing=True,
                                verbose=confservice.get('logging','level')=='DEBUG',
                                logger=LOGGER, logprefix=logprefix,
                                settings=settings)

        # Load plugins
        self._wps_interface.register_providers()
        return self.qgisapp

    def terminate(self):
        """ Cleanup  resources
        """
        if self._initialized:
            LOGGER.info("Closing worker pool")
            self._poolserver.terminate()

    def start_supervisor(self):
        """ Start supervisor killer 

            Convenient proxy to pool server 
        """
        self._poolserver.start_supervisor()

    @classmethod
    def instance(cls) -> 'QgsProcessFactory':
        if not hasattr(cls,'_instance'):
            cls._instance = QgsProcessFactory()
        return cls._instance


def get_process_factory():
    """ Return the current factory instance
    """
    return QgsProcessFactory.instance()
    


