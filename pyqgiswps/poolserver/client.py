#
# Copyright 2020 3liz
# Author David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" Pool client

    Implement a ROUTER 
"""

import asyncio
import zmq
import zmq.asyncio
import logging
import uuid
import pickle


from time import time
from collections import deque

from typing import Callable, Any

from .utils import _get_ipc, WORKER_READY

LOGGER=logging.getLogger('SRVLOG')

class RequestTimeoutError(Exception):
    pass

class RequestGatewayError(Exception):
    pass

class RequestBackendError(Exception):
    def __init__(self, response):
        super().__init__(response)
    
    @property
    def response(self):
        return self.args[0]

class MaxRequestsExceeded():
    pass


class _Client:

    def __init__( self, bindaddr: str, maxqueue: int = 100 ) -> None:

        context = zmq.asyncio.Context.instance()

        socket = context.socket(zmq.ROUTER)
        socket.setsockopt(zmq.LINGER, 500)
        socket.setsockopt(zmq.ROUTER_MANDATORY,1)
        socket.bind(bindaddr)                

        self._running  = False
        self._handlers = {}
        self._socket   = socket
        self._loop     = asyncio.get_event_loop()
        self._maxqueue = maxqueue

        # Get track of available workers
        self._worker_q  = asyncio.Queue()
        self._worker_s  = []
        
        # Start polling
        self._polling = asyncio.ensure_future(self._poll())

    def _put_worker(self, worker_id) -> None:
        if not worker_id in self._worker_s:
            LOGGER.debug("WORKER READY %s", worker_id)
            self._worker_s.append(worker_id)
            self._worker_q.put_nowait(worker_id)

    async def _get_worker(self, timeout):
        worker_id = await asyncio.wait_for(self._worker_q.get(), timeout)
        self._worker_s.remove(worker_id)
        return worker_id

    async def _poll(self) -> None:
        """ Handle incoming messages
        """
        cancelled = False
        while not cancelled:
            try:
                worker_id, *rest = await self._socket.recv_multipart()
                if rest[0] == WORKER_READY:
                    # Worker is available on new connection
                    # Mark worker as available
                    self._put_worker(worker_id)
                    continue

                msgid, (success, response) = (rest[0],pickle.loads(rest[1]))
                LOGGER.debug("Receveid %s, success %s", msgid, success)
                # Get if there is a future pending for that message
                try:
                    handler = self._handlers.pop(msgid)
                    if not success:
                        response = RequestBackendError(response)
                        handler.set_exception(response)
                    else:
                        handler.set_result(response)
                except KeyError:
                    LOGGER.warning("%s: No pending future found for message %s",self.identity, correlation_id)
            except zmq.ZMQError as err:
                LOGGER.error("%s error:  zmq error: %s (%s)", self.identity, zmq.strerror(err.errno),err.errno)
            except Exception as err:
                LOGGER.error("poll() exception %s\n%s", err, traceback.format_exc())
            except asyncio.CancelledError:
                LOGGER.debug("polling stopped")
                cancelled = True


    def close(self):
        LOGGER.debug("Closing pool client")
        self._polling.cancel()
        self._socket.close()

    async def apply_async( self, target: Callable[[None], None], args=(), kwargs={}, timeout: int = 5) -> Any:
        """ Run job asynchronously
        """
        if len(self._handlers) > self._maxqueue:
            raise MaxRequestExceeded()

        # Wait for available worker
        try:
            worker_id = await self._get_worker(timeout)
        except asyncio.TimeoutError:
            raise RequestTimeoutError()
 
        # Send request
        request = pickle.dumps((target, args, kwargs))
        correlation_id = uuid.uuid1().bytes
        try:
            # Pick available worker
            await self._socket.send_multipart([worker_id, correlation_id, request], flags=zmq.DONTWAIT)
        except zmq.ZMQError as err:
            LOGGER.error("%s (%s)", zmq.strerror(err.errno), err.errno)
            raise RequestGatewayError()

        handler = self._loop.create_future()

        self._handlers[correlation_id] = handler
        # Wait for response
        try:
            return await asyncio.wait_for(handler, timeout)
        except asyncio.TimeoutError:
            raise RequestTimeoutError()
        finally:
            # Remove the handler
            self._handlers.pop(correlation_id,None)


def create_client( maxqueue: int=100 ) -> _Client:

    # Create ROUTER socket
    bindaddr = _get_ipc('pooladdr')

    return _Client( bindaddr, maxqueue )          

