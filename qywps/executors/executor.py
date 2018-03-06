##
## Copyright 2017  3Liz,                                          
## licensed under MIT, Please consult LICENSE.txt for details     
##                                                                
## author: David Marteau <david.marteau@3liz.com>                 
##                                                                

import asyncio
import os
import sys
import traceback
import json
import shutil
import tempfile
import logging
import lxml
import signal

from multiprocessing import Pool
from threading import Timer
from datetime import datetime

from abc import ABCMeta, abstractmethod
from qywps import WPS, OWS

from qywps.app.WPSResponse import WPSResponse
from qywps.app.WPSResponse import STATUS
from qywps.app.WPSRequest import WPSRequest

from lxml import etree
from qywps.exceptions import (StorageNotSupported, OperationNotSupported,
                              NoApplicableCode)

import qywps.configuration as config

LOGGER = logging.getLogger("QYWPS")

class ExecutorError(Exception):
    pass

class UnknownProcessError(ExecutorError):
    pass

class StorageNotFound(ExecutorError): 
    pass


class Executor(metaclass=ABCMeta):
    """ Define base class for all executors

        An executor is responsible for managing processes creation, execution
        and returning processes status. 
    """

    @abstractmethod
    def install_processes( self, processes ):
        """ Install processes 
        """
        raise NotImplementedError

    @abstractmethod
    def list_processes( self ):
        """ List all available processes

            :param ident: process identifier

            :return: A list of processes infos
        """
        raise NotImplementedError

    @abstractmethod
    def get_process( self, ident ):
        """ Retrieve process infos

            :param ident: process identifier
            
            :return: Object holding process description data
        """
        raise NotImplementedError

    @abstractmethod
    def get_status( self, uuid=None):
        """ Return status of the stored processes

            :param uuid: the uuid of the required process. 
             If set to None, return all the stored status.

            :return: The status or the list of status.
        """
        raise NotImplementedError


    @abstractmethod
    def start_request( self, request_uuid, wps_request ):
        """ Indicate that a request processing is started 
            
            This method is intended for the executor to record incoming request and process
            status.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute( self, wps_request, wps_response ):
        """ Execute a process
        """
        raise NotImplementedError

    @abstractmethod
    def status_url( self, uuid, request ):
        """ Return the status url
        """
        raise NotImplementedError

    @abstractmethod
    def get_results(self, uuid):
        """ Return results status
        """
        raise NotImplementedError

    def initialize( self ):
        """ Initialize an executor
        """
        pass

    def terminate( self ):
        """ Terminate and free executor ressources
        """
        pass


class LOGStore(metaclass=ABCMeta):

    @staticmethod
    def create(name):
        """ Return a storage instance
        """
        from pkg_resources import iter_entry_points
        for entry in iter_entry_points(group="qywps.logstorage", name=name):
            LOGGER.info("Loading logstore %s" % name)
            return entry.load()()
        else:
           raise StorageNotFound( name )

    @abstractmethod
    def log_request( self, request_uuid, wps_request):
        """
        """
        raise NotImplementedError

    @abstractmethod
    def status_url( self, uuid, request ):
        """ Return the status url
        """
        raise NotImplementedError

    @abstractmethod
    def get_status( self, uuid=None ):
        """ Return status of the stored processes

            :param uuid: the uuid of the required process. 
             If set to None, return all the stored status.

            :return: The status or the list of status.
        """
        raise NotImplementedError

    @abstractmethod
    def get_results(self, uuid):
        """ Return results status
        """
        raise NotImplementedError

    def delete_response(self, uuid):
        """ Delete response record
        """
        pass

    def init_session(self):
        """ initialize store session
        """
        pass


class PoolExecutor(Executor):
    """ Pool executor
    """

    def __init__(self):
        self.processes = {}
        self._cleanup_task = None
    
    def initialize(self, processes ):
        super(PoolExecutor, self).initialize()
 
        cfg = config.get_config('server')

        dbstorename = cfg.get('logstorage')
        maxparallel = cfg.getint('parallelprocesses')

        self._logstore = LOGStore.create(dbstorename)
       
        maxparallel = max(1,maxparallel)
        self._pool = Pool(processes=maxparallel, initializer=self.worker_initializer)

        self.install_processes( processes )
        self._logstore.init_session()

        WPSResponse.set_logstore(self._logstore)

        # Launch the cleanup task
        self.schedule_cleanup()

    def status_url(self, uuid, request):
        """
        """
        return self._logstore.status_url(uuid, request)

    def get_status( self, uuid=None ):
        """ Implementation of Execute.get_status
        """
        return self._logstore.get_status(uuid)
 
    def get_results(self, uuid):
        """ Return results status
        """
        return self._logstore.get_results(uuid) 

    def terminate(self):
        super(PoolExecutor,self).terminate()

        if self._cleanup_task:
            self._cleanup_task.cancel()

        if self._pool:
            LOGGER.info("Closing worker pool")
            self._pool.close()
            self._pool.terminate()
            self._pool.join()

    def worker_initializer(self):
        """ Worker initializer
        """
        LOGGER.info("Starting executor worker pid %s" % os.getpid())
        self._logstore.init_session()

        # Set logstore to all Response instance
        WPSResponse.set_logstore(self._logstore)

    def install_processes( self, processes ):
        """ Install processes 
        """
        self.processes = { p.identifier: p for p in processes }

    def list_processes( self ):
        """ List all available processes

            :param ident: process identifier

            :return: A list of processes infos
        """
        return self.processes.values()

    def get_process( self, ident ):
        """ Retrieve process infos

            :param ident: process identitfier
            
            :return: Object holding process description data
        """
        try:
            return self.processes[ident]
        except KeyError:
            raise UnknownProcessError(ident)

    def start_request( self, request_uuid, wps_request ):
        """ Log input request 
        """
        self._logstore.log_request( request_uuid, wps_request)

    def schedule_cleanup( self ):
        """ Schedule a periodic cleanup
        """
        interval = config.get_config('server').getint('cleanup_interval')
        loop     = asyncio.get_event_loop()
        pool     = self._pool

        async def _run_cleanup():
            while True:
                await asyncio.sleep(interval)
                # Run the cleanup function asynchronously
                future = loop.create_future() 
                pool.apply_async(self._clean_processes,
                    callback       = lambda rv: loop.call_soon_threadsafe(future.set_result, rv)  , 
                    error_callback = lambda exc:  loop.call_soon_threadsafe(future.set_exception, exc))
                # await for the cleaup to complete
                try:
                    await future
                except Exception as e:
                    traceback.print_exc()
                    LOGGER.error("Cleanup task failed: %s", e)

        # Schedule the task
        self._cleanup_task = asyncio.ensure_future( _run_cleanup() )

    async def execute( self, wps_request, wps_response ):
        """ Execute a process

            :return: wps_response or None
        """
        process = wps_response.process
        process.uuid = wps_response.uuid

        self.start_request(process.uuid, wps_request)

        # Check if we need no store the response
        wps_response.store = (wps_response.status >= STATUS.STORE_STATUS)

        # Get request defined timeout
        timeout = wps_request.timeout

        if (wps_response.status == STATUS.STORE_AND_UPDATE_STATUS) and self._pool is not None:

            def _on_error( exc ):
                LOGGER.error('Process Exception { "exception": "%s", "uuid": "%s" }' % (exc, process.uuid))
                wps_response.update_status("%s" % exc, None, STATUS.ERROR_STATUS)

            wps_response.update_status('Task accepted')
            self._pool.apply_async(self._run_process, args=(process.handler, wps_request, wps_response), 
                    kwds={'is_async':True, 'timeout': timeout },
                    error_callback = _on_error)
        else:
            # Run the processe asynchronously

            loop = asyncio.get_event_loop()
            # Create a future for holding the result
            future = loop.create_future()

            def success_cbk( response ):
                loop.call_soon_threadsafe(future.set_result, response)
    
            def _on_error( exc ):
                LOGGER.error('Process Exception { "exception": "%s", "uuid": "%s" }' % (exc, process.uuid))
                wps_response.update_status("%s" % exc, None, STATUS.ERROR_STATUS)
                loop.call_soon_threadsafe(future.set_result, wps_response)

            self._pool.apply_async(self._run_process, args=(process.handler, wps_request, wps_response),
                    callback=success_cbk, error_callback=_on_error, kwds={'is_async':False, 'timeout': timeout})

            try:
                wps_response = await asyncio.wait_for(future, timeout)
            except asyncio.TimeoutError:
                raise NoApplicableCode("Execute Timeout", code=424)

        return wps_response

    @staticmethod
    def _run_process(handler, wps_request, wps_response, is_async, timeout):
        """ Run WPS  process
        """
        # Set up timeout handler
        timer = Timer(timeout, _timeout_kill, args=(wps_response,is_async))
        timer.start()
        try:
            # Change current dir to workdir
            os.chdir(wps_response.process.workdir)

            wps_response.update_status('Task started', 0)

            response = handler(wps_request, wps_response)
            if not response:
                raise NoApplicableCode("Handler returned invalid response object",code=500)
            response.update_status('Task finished'.format(wps_response.process.title),
                                    100, STATUS.DONE_STATUS)
        except Exception as e:
            traceback.print_exc()
            raise
        finally:
            timer.cancel()

        if not is_async:
            # XXX We want the response to be pickable, hence we need to convert
            # The document to something pickable (here, it appears to be 'bytes')
            wps_response.document = lxml.etree.tostring(wps_response.document, pretty_print=True)
            return wps_response

        # We dont need to return anything in async mode

    @staticmethod
    def _clean_processes():
        """ Clean up all processes
            Remove status and delete processes workdir
        """
        LOGGER.info("Running cleanup task")
        # Iterate over done processes
        cfg = config.get_config('server')
        rootdir = os.path.abspath(cfg['workdir'])

        # The response expiration in seconds
        expire_default = cfg.getint('response_expiration')

        logstore = WPSResponse.get_logstore()
        now_ts   = datetime.now().timestamp()

        for _, rec in list(logstore.records):
            timestamp = rec.get('timestamp')
            dangling  = timestamp is None
            try:
                if not dangling and STATUS[rec['status']] < STATUS.DONE_STATUS:
                    # Check that the task is not in dangling state
                    timeout  = rec.get('timeout')
                    dangling = timeout is None or (now_ts - int(timestamp)) >= timeout
                    if not dangling:
                        continue
            except KeyError:
                # Handle legacy status
                pass
            
            expiration = rec.get('expiration', expire_default)
            notpinned  = not rec.get('pinned',False)
            if dangling or notpinned or (now_ts - int(timestamp)) >= expiration:
                # Delete the working directory
                uuid_str = rec['uuid']
                workdir = os.path.join(rootdir, uuid_str)
                LOGGER.info("Cleaning response status: %s", uuid_str)
                try:
                    if os.path.isdir(workdir):
                        shutil.rmtree(workdir)
                except Exception as err:
                    LOGGER.error('Unable to remove directory: %s', err)
                # Delete the record/response
                logstore.delete_response(uuid_str)




def _timeout_kill( response, is_async ):
    """ This is a kind of drastic way to handle timeout
        in workers but we have not very much control
        on what append in the worker. In all case, the pool will 
        recreate a new worker. 
    """
    LOGGER.error("Timeout occured in worker process %s: %s",
            response.process.identifier ,
            response.uuid)
    response.update_status("Timeout Error", None, STATUS.ERROR_STATUS)
    os.kill(os.getpid(), signal.SIGABRT)

   
