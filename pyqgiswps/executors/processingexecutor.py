#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import asyncio
import logging
import os
import shutil
import time
import traceback

from contextlib import contextmanager
from datetime import datetime
from glob import glob
from typing import (
    Any,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
)

import psutil

from pyqgisservercontrib.core.watchfiles import watchfiles
from pyqgiswps.app.process import WPSHandler, WPSProcess
from pyqgiswps.app.request import STATUS, WPSRequest, WPSResponse
from pyqgiswps.config import confservice
from pyqgiswps.exceptions import (
    NoApplicableCode,
    ProcessException,
    UnknownProcessError,
)
from pyqgiswps.logger import logfile_context
from pyqgiswps.poolserver.client import (
    MaxRequestsExceeded,
    RequestBackendError,
    create_client,
)
from pyqgiswps.utils.lru import lrucache

from .logstore import logstore

LOGGER = logging.getLogger('SRVLOG')


class ProcessingExecutor:
    """ Progessing executor
    """

    def __init__(self, processes: Iterable[WPSProcess]):

        # Prevent circular reference
        from .processfactory import get_process_factory

        maxqueuesize = confservice.getint('server', 'maxqueuesize')

        self._pool = create_client(maxqueuesize)
        self._context_processes = lrucache(50)
        self._factory = get_process_factory()
        self._reload_handler = None
        self._restart_files = []
        self._background_tasks = set()

        self.processes = {p.identifier: p for p in processes}

        # Launch the cleanup task
        self.schedule_cleanup()

        # Initialize restart handler
        self.init_restart_handler()

    def update_restart_files(self):
        """ Updates file that may trigger a restart  of
            workers
        """
        self._restart_files.clear()
        restartmon = confservice.get('server', 'restartmon')
        if restartmon:
            self._restart_files.append(restartmon)
            # Watch plugins
            pluginpath = confservice.get('processing', 'providers_module_path')
            if pluginpath:
                plugins = glob(os.path.join(pluginpath, '*/.update-manifest'))
                self._restart_files.extend(plugins)

            LOGGER.debug("Updated monitored files %s", self._restart_files)
            return True

    def init_restart_handler(self):
        if self.update_restart_files():
            def callback(*_args):
                self.reload_qgis_processes()
                self.update_restart_files()

            LOGGER.info("Initializing reload monitoring")
            check_time = confservice.getint('server', 'restartmon_check_time', 3000)
            self._reload_handler = watchfiles(self._restart_files, callback, check_time)
            self._reload_handler.start()

    def get_status(self, uuid: Optional[str] = None, **kwargs) -> Iterator:
        """ Return status of the stored processes

            :param uuid: the uuid of the required process.
             If set to None, return all the stored status.

            :return: The status or an iterator to the list of status.
        """
        return logstore.get_status(uuid, **kwargs)

    def kill_job(self, uuid: str, pid: Optional[int] = None) -> bool:
        """ Kill process job

            This will have no effects if the worker
            is not in 'BUSY' state
        """
        if pid is None:
            # Retrieve pid
            store = self.get_status(uuid)
            if not store:
                return False

            pid = store.get('pid')
            if not pid:
                return False

        return self._factory.kill_worker_busy(pid)

    def delete_results(self, uuid: str, force: bool = False) -> bool:
        """ Delete process results and status

            :param uuid: the uuid of the required process.
             If set to None, return all the stored status.

            :return: True if the status has been deleted.
        """
        if not force:
            rec = logstore.get_status(uuid)
            if rec is None:
                raise FileNotFoundError(uuid)
            try:
                if STATUS[rec['status']] < STATUS.DONE_STATUS:
                    return False
            except KeyError:
                # Handle legacy status
                pass
        else:
            LOGGER.warning("Forcing resources deletion for job '%s'", uuid)

        workdir = os.path.abspath(confservice.get('server', 'workdir'))

        # Delete the working directory
        uuid_str = str(uuid)
        workdir = os.path.join(workdir, uuid_str)
        LOGGER.info("Cleaning response status: %s", uuid_str)
        try:
            if os.path.isdir(workdir):
                shutil.rmtree(workdir)
        except Exception as err:
            LOGGER.error('Unable to remove directory: %s: %s', workdir, err)
        # Delete the record/response
        logstore.delete_response(uuid_str)
        return True

    def get_results(self, uuid):
        """ Return results status
        """
        return logstore.get_results(uuid)

    def terminate(self):
        """ Execute cleanup tasks
        """
        if self._reload_handler:
            self._reload_handler.stop()

        if self._cleanup_task:
            self._cleanup_task.cancel()

        if self._pool:
            self._pool.close()

    def list_processes(self):
        """ List all available processes

            :param ident: process identifier

            :return: A list of processes infos
        """
        return self.processes.values()

    def get_processes(
        self,
        identifiers: Sequence[str],
        map_uri: Optional[str] = None,
    ) -> List[WPSProcess]:
        """ Override executors.get_process
        """
        try:
            processes = [self.processes[ident] for ident in identifiers]
        except KeyError as exc:
            raise UnknownProcessError(str(exc)) from None

        # TODO Allow create contextualized processes from non-processing processes
        if self._factory.qgis_enabled and map_uri is not None:

            # Create a new instance of a process for the given context
            # Contextualized processes are stored in lru cache
            def _test(p):
                return (map_uri, p.identifier) not in self._context_processes

            if any(_test(p) for p in processes):
                processes = self._factory.create_contextualized_processes(
                    identifiers,
                    map_uri=map_uri,
                )

                # Update cache
                for p in processes:
                    self._context_processes[map_uri, p.identifier] = p
            else:
                # Get from cache
                processes = [self._context_processes[map_uri, p.identifier] for p in processes]
        return processes

    def reload_qgis_processes(self):
        """ Reload Qgis processes
        """
        factory = self._factory
        if factory.qgis_enabled:
            try:
                LOGGER.info("Reloading Qgis providers")
                self.processes = {p.identifier: p for p in factory.create_qgis_processes()}
                self._context_processes.clear()
            except ProcessException:
                LOGGER.error("Failed to reload Qgis processes")

    def schedule_cleanup(self):
        """ Schedule a periodic cleanup
        """
        interval = confservice.getint('server', 'cleanup_interval')

        async def _run_cleanup():
            while True:
                await asyncio.sleep(interval)
                try:
                    self._clean_processes()
                except Exception as e:
                    traceback.print_exc()
                    LOGGER.error("Cleanup task failed: %s", e)

        # Schedule the task
        self._cleanup_task = asyncio.ensure_future(_run_cleanup())

    async def execute(self, wps_request: WPSRequest, wps_response: WPSResponse) -> Any:
        """ Execute a process

            :return: wps_response or None
        """
        process = wps_response.process
        process.uuid = wps_response.uuid

        # Start request
        logstore.log_request(process.uuid, wps_request)

        # Get request defined timeout
        timeout = wps_request.timeout

        apply_future = self._pool.apply_async(
            self._run_process,
            args=(process.handler, wps_request, wps_response),
            timeout=timeout,
        )

        if wps_request.execute_async:
            # ---------------------------------
            # Run the processe asynchronously
            # ---------------------------------

            # Task accepted
            wps_response.update_status('Task accepted', None, STATUS.ACCEPTED_STATUS)

            async def do_execute_async():
                # Handle errors while we are going async
                try:
                    await apply_future
                except asyncio.TimeoutError:
                    wps_response.update_status("Timeout Error", None, STATUS.ERROR_STATUS)
                except MaxRequestsExceeded:
                    wps_response.update_status("Server busy, please retry later", None, STATUS.ERROR_STATUS)
                except Exception:
                    # There is no point to let the error go outside
                    LOGGER.error(traceback.format_exc())
                    wps_response.update_status("Internal Error", None, STATUS.ERROR_STATUS)
                    pass

            # Fire and forget
            task = asyncio.create_task(do_execute_async())
            task.add_done_callback(self._background_tasks.discard)

            return wps_response.document
        else:
            # -------------------------------
            # Run process and wait for response
            # -------------------------------

            # Task accepted
            wps_response.update_status('Task accepted', None, STATUS.ACCEPTED_STATUS)

            try:
                return await apply_future
            except asyncio.TimeoutError:
                wps_response.update_status("Timeout Error", None, STATUS.ERROR_STATUS)
                raise NoApplicableCode("Process execution Timeout", code=504)
            except MaxRequestsExceeded:
                raise NoApplicableCode("Server busy, please retry later", code=509)
            except RequestBackendError as e:
                if isinstance(e.response, ProcessException):
                    raise NoApplicableCode("Process Error", code=500)
                else:
                    raise

    @staticmethod
    def _run_process(
        handler: WPSHandler,
        wps_request: WPSRequest,
        wps_response: WPSResponse,
    ) -> bytes:
        """ Run WPS  process

            Note that there is nothing to return is async mode
        """
        try:
            workdir = wps_response.process.workdir
            # Change current dir to workdir
            os.chdir(workdir)

            wps_response.update_status('Task started', 0, STATUS.STARTED_STATUS)

            with logfile_context(workdir, 'processing'), memory_logger(wps_response):
                handler(wps_request, wps_response)

                wps_response.update_status('Task finished', 100, STATUS.DONE_STATUS)

                # Return pickable response
                if wps_response.document is not None:
                    return wps_response.get_document_bytes()

        except ProcessException as e:
            wps_response.update_status("%s" % e, None, STATUS.ERROR_STATUS)
            raise
        except Exception:
            wps_response.update_status("Internal error", None, STATUS.ERROR_STATUS)
            raise

    @staticmethod
    def _clean_processes():
        """ Clean up all processes
            Remove status and delete processes workdir

            Dangling tasks will be removed: these are tasks no marked finished but
            for which the timeout has expired. Usually this is task for wich the process
            as died (memory exhaustion, segfault....)
        """
        # Iterate over done processes
        cfg = confservice['server']
        workdir_base = os.path.abspath(cfg.get('workdir'))

        # The response expiration in seconds
        expire_default = cfg.getint('response_expiration')

        now_ts = datetime.utcnow().timestamp()

        for _, rec in list(logstore.records):
            timestamp = rec.get('timestamp')
            dangling = timestamp is None
            try:
                if not dangling and STATUS[rec['status']] < STATUS.DONE_STATUS:
                    # Check that the task is not in dangling state
                    timeout = rec.get('timeout')
                    dangling = timeout is None or (now_ts - int(timestamp)) >= timeout
                    if not dangling:
                        continue
            except KeyError:
                # Handle legacy status
                pass

            expiration = rec.get('expiration', expire_default)
            notpinned = not rec.get('pinned', False)
            if notpinned and (dangling or (now_ts - int(timestamp)) >= expiration):
                # Delete the working directory
                uuid_str = rec['uuid']
                workdir = os.path.join(workdir_base, uuid_str)
                LOGGER.info("Cleaning response status: %s", uuid_str)
                try:
                    if os.path.isdir(workdir):
                        shutil.rmtree(workdir)
                except Exception as err:
                    LOGGER.error('Unable to remove directory: %s', err)
                # Delete the record/response
                logstore.delete_response(uuid_str)


@contextmanager
def memory_logger(response):
    """ Log memory consumption
    """
    # Get the current process info
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss
    mb = 1024 * 1024.0
    ns = 1000000000.0
    start_time = time.perf_counter_ns()
    try:
        yield
    finally:
        # Log memory infos
        end_time = time.perf_counter_ns()
        end_mem = process.memory_info().rss
        LOGGER.info(
            (
                "{4}:{0} memory: start={1:.3f}Mb end={2:.3f}Mb "
                "delta={3:.3f}Mb "
                "duration: {5:.3f}s"
            ).format(
                str(response.uuid)[:8],
                start_mem / mb,
                end_mem / mb,
                (end_mem - start_mem) / mb,
                response.process.identifier,
                (end_time - start_time) / ns,
            ),
        )
