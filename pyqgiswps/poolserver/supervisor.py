#
# Copyright 2018 3liz
# Author David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" Supervisor implementation for controlling lifetime and restart of workers
"""

#
# Client
#

import asyncio
import logging
import os
import traceback

from typing import Callable

import zmq
import zmq.asyncio

from .utils import _get_ipc

LOGGER = logging.getLogger('SRVLOG')


class Client:

    def __init__(self):
        """ Supervised client notifier
        """
        address = _get_ipc('supervisor')

        ctx = zmq.Context.instance()
        self._sock = ctx.socket(zmq.PUSH)
        self._sock.setsockopt(zmq.IMMEDIATE, 1)  # Do no queue if no connection
        self._sock.connect(address)
        self._pid = os.getpid()
        self._busy = False

    def _send(self, data: bytes):
        try:
            self._sock.send_multipart([str(self._pid).encode(), data], flags=zmq.DONTWAIT)
        except zmq.ZMQError as err:
            if err.errno != zmq.EAGAIN:
                LOGGER.error("%s (%s)", zmq.strerror(err.errno), err.errno)

    def notify_done(self):
        """ Send 'ready' notification
        """
        if self._busy:
            self._busy = False
            self._send(b'DONE')

    def notify_busy(self):
        """ send 'busy' notification
        """
        if not self._busy:
            self._busy = True
            self._send(b'BUSY')

    def close(self):
        self._sock.close()


class Supervisor:

    def __init__(self, timeout: int, killfunc: Callable[[int], None]):
        """ Run supervisor

            :param timeout: timeout delay in seconds
        """
        address = _get_ipc('supervisor')

        ctx = zmq.asyncio.Context.instance()
        self._sock = ctx.socket(zmq.PULL)
        self._sock.setsockopt(zmq.RCVTIMEO, 1000)
        self._sock.bind(address)

        self._timeout = timeout
        self._busy = {}
        self._stopped = True
        self._killfunc = killfunc
        self._task = None

    def run(self):
        self._task = asyncio.ensure_future(self._run_async())

    def kill_worker_busy(self, pid: int) -> bool:
        """ Kill job  if in BUSY state
        """
        if pid in self._busy:
            LOGGER.info("Process dismissal requested for pid = %s", pid)
            del self._busy[pid]
            self._killfunc(pid)
            return True

    async def _run_async(self):
        """ Run supervisor
        """
        loop = asyncio.get_running_loop()

        def kill(pid: int):
            LOGGER.critical("Killing stalled process %s", pid)
            del self._busy[pid]
            self._killfunc(pid)

        self._stopped = False

        while not self._stopped:
            try:
                pid, notif = await self._sock.recv_multipart()
                pid = int(pid)
                if notif == b'BUSY':
                    self._busy[pid] = loop.call_later(self._timeout, kill, pid)
                elif notif == b'DONE':
                    try:
                        self._busy.pop(pid).cancel()
                    except KeyError:
                        pass
            except zmq.ZMQError as err:
                if err.errno != zmq.EAGAIN:
                    LOGGER.error("%s\n%s", zmq.strerror(err.errno), traceback.format_exc())
            except asyncio.CancelledError:
                self._stopped = True
            except Exception:
                LOGGER.critical("%s", traceback.format_exc())

    def stop(self):
        """ Stop the supervisor
        """
        LOGGER.debug("Stopping supervisor")
        if self._task:
            self._task.cancel()
        self._stopped = True
        self._sock.close()
        for th in self._busy.values():
            th.cancel()
        self._busy.clear()
