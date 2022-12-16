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
import traceback

from typing import Callable, Any

from .utils import _get_ipc, WORKER_READY, WORKER_DONE

LOGGER = logging.getLogger('SRVLOG')


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


class MaxRequestsExceeded(Exception):
    pass


class _Client:

    def __init__(self, bindaddr: str, maxqueue: int = 100) -> None:

        context = zmq.asyncio.Context.instance()

        socket = context.socket(zmq.ROUTER)
        socket.setsockopt(zmq.LINGER, 500)
        socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        socket.bind(bindaddr)

        self._running = False
        self._handlers = {}
        self._socket = socket
        self._maxqueue = maxqueue

        # Get track of available workers
        self._worker_q = asyncio.Queue()
        self._worker_s = []

        # Start polling
        self._polling = asyncio.ensure_future(self._poll())

    def _put_worker(self, worker_id) -> None:
        if worker_id not in self._worker_s:
            LOGGER.debug("WORKER READY %s", worker_id)
            self._worker_s.append(worker_id)
            self._worker_q.put_nowait(worker_id)

    def _remove_worker(self, worker_id) -> None:
        if worker_id in self._worker_s:
            LOGGER.debug("WORKER GONE %s", worker_id)
            self._worker_s.remove(worker_id)

    async def _get_worker(self, timeout):
        while True:
            worker_id = await asyncio.wait_for(self._worker_q.get(), timeout)
            try:
                self._worker_s.remove(worker_id)
                break
            except ValueError:
                # Worker was removed from list, try again
                pass
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
                if rest[0] == WORKER_DONE:
                    # Worker is gone because of a restart
                    # Remove worker from list
                    self._remove_worker(worker_id)
                    continue

                msgid = rest[0]
                # Get if there is a future pending for that message
                handler = self._handlers.pop(msgid, None)
                if handler is not None:
                    try:
                        success, response = pickle.loads(rest[1])
                    except Exception as exc:
                        LOGGER.error("Pickle exception:\n%s", traceback.format_exc())
                        handler.set_exception(exc)
                        continue
                    LOGGER.debug("Receveid %s, success %s", msgid, success)
                    if not success:
                        response = RequestBackendError(response)
                        handler.set_exception(response)
                    else:
                        handler.set_result(response)
                else:
                    LOGGER.warning("No pending future found for message %s", msgid)
            except zmq.ZMQError as err:
                LOGGER.error("zmq error: %s (%s)", zmq.strerror(err.errno), err.errno)
            except asyncio.CancelledError:
                LOGGER.debug("polling stopped")
                cancelled = True
            except Exception:
                LOGGER.error("Polling error\n%s", traceback.format_exc())

    def close(self) -> None:
        LOGGER.debug("Closing pool client")
        self._polling.cancel()
        self._socket.close()

    def apply_async(self, target: Callable[[None], None], args=(), kwargs={}, timeout: int = 5) -> Any:
        """ Run job asynchronously
        """
        # Pickle data, if it fails, then error will be raised before
        # entering async
        request = pickle.dumps((target, args, kwargs))
        return self._apply_async(request, timeout)

    async def _apply_async(self, request: bytes, timeout: int = 5) -> Any:
        """ Run job asynchronously
        """
        if len(self._handlers) > self._maxqueue:
            raise MaxRequestsExceeded()

        # Wait for available worker
        LOGGER.debug("*** Waiting worker")
        worker_id = await self._get_worker(timeout)

        # Send request
        correlation_id = uuid.uuid1().bytes
        try:
            # Send request
            LOGGER.debug("*** Sending request")
            await self._socket.send_multipart([worker_id, correlation_id, request], flags=zmq.DONTWAIT)
        except zmq.ZMQError as err:
            LOGGER.error("%s (%s)", zmq.strerror(err.errno), err.errno)
            raise RequestGatewayError()

        handler = asyncio.get_running_loop().create_future()

        try:
            self._handlers[correlation_id] = handler
            # Wait for response
            LOGGER.debug("*** Waiting for response")
            return await asyncio.wait_for(handler, timeout)
        finally:
            # Remove the handler
            self._handlers.pop(correlation_id, None)


def create_client(maxqueue: int = 100) -> _Client:

    # Create ROUTER socket
    bindaddr = _get_ipc('pooladdr')

    return _Client(bindaddr, maxqueue)
