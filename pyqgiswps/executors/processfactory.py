#
# Copyright 2018-2021 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Qgis process factory

"""
import logging
import os
import queue
import signal
import traceback

from glob import glob
from itertools import chain
from multiprocessing import Process, Queue
from typing import (
    List,
    Optional,
    Sequence,
)

from ..app.process import WPSProcess
from ..config import confservice
from ..exceptions import ProcessException
from ..poolserver.server import create_poolserver
from ..utils.conditions import assert_precondition
from ..utils.plugins import WPSServerInterfaceImpl
from ..utils.qgis import setup_qgis_paths, start_qgis_application
from .logstore import logstore

LOGGER = logging.getLogger('SRVLOG')

# Android does not support semaphores
# and thus queue implementation will not work
#
# Borrow android detection from kivy:
# On Android sys.platform returns 'linux2', so prefer to check the
# presence of python-for-android environment variables (ANDROID_ARGUMENT
# or ANDROID_PRIVATE).
_is_android = 'ANDROID_ARGUMENT' in os.environ


# Delegate Qgis process loading in
# another processes, this will enable live update
# of Qgis providers/algorithms
#
# The delegate acts as a pool server: restarting the subprocess
#
#
class _FactoryDelegate(Process):

    def __init__(self, factory: 'QgsProcessFactory'):
        super().__init__()
        self._queue = Queue()
        self._factory = factory

    def stop(self):
        self._queue.put(None)

    def create_qgis_processes(self) -> Optional[List[WPSProcess]]:
        processes = self._queue.get()
        if processes is None:
            raise ProcessException("Failed to initialize Qgis processes")
        return processes

    def create_contextualized_processes(self, identifiers: List[str], map_uri: str) -> List[WPSProcess]:
        self._queue.put((identifiers, map_uri))
        return self._queue.get()

    @staticmethod
    def task(q: Queue, factory: 'QgsProcessFactory'):
        """ Handle Qgis processes creation
            Run in detached process
        """
        try:
            processes = factory._create_qgis_processes()
            q.put(processes)
        except Exception:
            LOGGER.error(traceback.format_exc())
            q.put(None)
            return

        # Subsqequent calls: return contextualized processe
        while True:
            try:
                args = q.get()
                if args is None:
                    break
                identifiers, map_uri = args
                processes = factory._create_contextualized_processes(identifiers, map_uri)
                q.put(processes)
            except queue.Empty:
                pass
            except Exception:
                LOGGER.error(traceback.format_exc())
                q.put([])

    def run(self):
        """ Run in a subprocess
        """
        def term(*args):
            raise SystemExit()

        signal.signal(signal.SIGTERM, term)
        try:
            while True:
                # Create sub-process for handling processes creation
                # Process will seat waiting for creating contextualized processes
                p = Process(target=self.task, args=(self._queue, self._factory))
                p.start()
                p.join()
                # Test non-zero exitcode
                # This happends on Qgs provider registration failure because PyQgis exception are not
                # propagated to python
                if p.exitcode != 0:
                    LOGGER.critical("Sub process exited with code %s", p.exitcode)
                    self._queue.put(None)
                    break
                p.close()
        except SystemExit:
            LOGGER.debug("Factory delegate: got SystemExit()")
            if p and p.is_alive():
                p.terminate()


class QgsProcessFactory:

    def __init__(self):
        self._initialized = False
        self.qgisapp = None
        self.qgis_enabled = False

        self._delegate = None

    def initialize(self, load_qgis_processing: bool = False) -> Optional[List[WPSProcess]]:
        """ Initialize the factory

            Should be called once
        """
        assert_precondition(not self._initialized)

        self._config = confservice['processing']

        plugin_path = self._config.get('providers_module_path')
        default_path = self._config.get('default_module_path')
        exposed_providers = self._config.get('exposed_providers', fallback='').split(',')

        setup_qgis_paths()

        self._wps_interface = WPSServerInterfaceImpl(with_providers=exposed_providers)
        self._wps_interface.initialize(default_path)
        self._wps_interface.initialize(plugin_path)

        if load_qgis_processing:
            processes = self.create_qgis_processes()
        else:
            processes = None

        self._create_pool()

        return processes

    def _create_pool(self):
        """ Initialize the worker pool
        """
        cfg = confservice['server']

        maxparallel = cfg.getint('parallelprocesses')
        processlifecycle = cfg.getint('processlifecycle')
        response_timeout = cfg.getint('response_timeout')

        # Initialize logstore (redis)
        logstore.init_session()

        # 0 mean eternal life
        if processlifecycle == 0:
            processlifecycle = None

        # Need to be initialized as soon as possible
        self._poolserver = create_poolserver(
            maxparallel,
            maxcycles=processlifecycle,
            initializer=self.worker_initializer,
            timeout=response_timeout,
        )
        self._initialized = True

    def restart_pool(self):
        """ Restart all workers in pool
        """
        if self._initialized:
            self._poolserver.restart()

    def _create_contextualized_processes(self, identifiers: Sequence[str], map_uri: str) -> List[WPSProcess]:
        """ Create processes from context
        """
        from pyqgiswps.executors.processingprocess import QgsProcess
        return [QgsProcess.createInstance(ident, map_uri=map_uri) for ident in identifiers]

    def create_contextualized_processes(self, identifiers: Sequence[str], map_uri: str) -> List[WPSProcess]:
        if self._delegate and self._delegate.is_alive():
            return self._delegate.create_contextualized_processes(identifiers, map_uri)
        else:
            # XXX Fallback to direct call, needed for testing
            return self._create_contextualized_processes(identifiers, map_uri)

    def _create_qgis_processes(self) -> List[WPSProcess]:
        """
          Convert processing algorithms to WPS processes
        """
        self.qgis_enabled = True
        self.start_qgis()

        # Install processes from processing providers
        from qgis.core import QgsProcessingAlgorithm

        from pyqgiswps.executors.processingprocess import QgsProcess

        processes = []

        iface = self._wps_interface

        # Do not publish hidden algorithm from toolbox
        def _is_hidden(a: QgsProcessingAlgorithm) -> bool:
            return (int(a.flags()) & QgsProcessingAlgorithm.FlagHideFromToolbox) != 0

        for provider in iface.providers:
            LOGGER.debug("Loading processing algorithms from provider '%s'", provider.id())
            processes.extend(QgsProcess(alg) for alg in provider.algorithms() if not _is_hidden(alg))

        if processes:
            LOGGER.info("Published processes:\n * %s", "\n * ".join(sorted(p.identifier for p in processes)))
        else:
            LOGGER.warning("No published processes !")

        # Return the list of processes
        return processes

    def create_qgis_processes(self) -> List[WPSProcess]:
        """ Create initial qgis processes objects in another process in order
            to prevent side effects from loading algorithms and
            allow for live reload
        """
        self.qgis_enabled = True
        # Re-create the sub-processes
        if _is_android:
            LOGGER.warn("Android platform detected: restarting processes may not behave as expected")
            processes = self._create_qgis_processes()
        else:
            if not self._delegate:
                self._delegate = _FactoryDelegate(self)
                self._delegate.start()
            else:
                self._delegate.stop()
            # Get processes list
            processes = self._delegate.create_qgis_processes()
            # Restart pool so that workers may
            # reload providers
            self.restart_pool()

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
            "Processing/Configuration/PREFER_FILENAME_AS_LAYER_NAME": "false",  # Qgis < 3.30
            "qgis/configuration/prefer-filename-as-layer-name": "false",         # Qgis >= 3.30
        }

        def _folders_setting(setting, folders):
            folders = folders.split(';')
            folders = chain(*(glob(f) for f in folders))
            folders = ';'.join(f for f in folders if os.path.isdir(f))
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
        self.qgisapp = start_qgis_application(
            enable_processing=True,
            verbose=confservice.get('logging', 'level') == 'DEBUG',
            logger=LOGGER, logprefix=logprefix,
            settings=settings,
        )

        # Load plugins
        self._wps_interface.register_providers()
        return self.qgisapp

    def terminate(self):
        """ Cleanup  resources
        """
        if self._delegate and self._delegate.is_alive():
            LOGGER.info("Terminating factory delegate")
            self._delegate.terminate()
        if self._initialized:
            LOGGER.info("Closing worker pool")
            self._poolserver.terminate()

    def start_supervisor(self):
        """ Start supervisor killer

            Convenient proxy to pool server
        """
        self._poolserver.start_supervisor()

    def kill_worker_busy(self, pid: int) -> bool:
        """ Force kill worker in BUSY state
        """
        return self._poolserver.kill_worker_busy(pid)

    @classmethod
    def instance(cls) -> 'QgsProcessFactory':
        if not hasattr(cls, '_instance'):
            cls._instance = QgsProcessFactory()
        return cls._instance


def get_process_factory():
    """ Return the current factory instance
    """
    return QgsProcessFactory.instance()
