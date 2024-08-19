#
# Copyright 2020 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
"""
The fork serve will ensure that forking processes
occurs from [almost] the same state.
"""
import logging
import os
import signal
import sys
import time
import traceback

from multiprocessing import Process
from multiprocessing.util import Finalize
from typing import (
    Callable,
    Optional,
    Sequence,
)

import zmq
import zmq.asyncio

from .pool import Pool
from .supervisor import Supervisor
from .utils import _get_ipc

LOGGER = logging.getLogger('SRVLOG')


class _Server:

    def __init__(self, broadcastaddr: str, pool: Process, timeout: int):

        ctx = zmq.asyncio.Context.instance()
        pub = ctx.socket(zmq.PUB)
        pub.setsockopt(zmq.LINGER, 500)    # Needed for socket no to wait on close
        pub.setsockopt(zmq.SNDHWM, 1)      # Max 1 item on send queue
        pub.bind(broadcastaddr)

        self._timeout = timeout
        self._sock = pub

        LOGGER.debug("Started server")
        self._pool = pool
        self._supervisor = None

        # Ensure that pool is terminated is called
        # at process exit
        self._terminate = Finalize(
            self, self._terminate_pool,
            args=(self._pool,),
            exitpriority=16,
        )

    def start_supervisor(self):
        """ Start supervisor independently

            Note: It is no recommended to run supervisor before asyncio loop
            has been properly set - for exemple when using a custom loop.
        """
        if self._supervisor is None:
            LOGGER.info("Starting supervisor")
            self._supervisor = Supervisor(self._timeout, lambda pid: os.kill(pid, signal.SIGKILL))
            self._supervisor.run()

    @classmethod
    def _terminate_pool(cls, p: Process):
        if p and hasattr(p, 'terminate'):
            if p.exitcode is None:
                p.terminate()
            if p.is_alive():
                p.join()

    def terminate(self):
        """ Terminate handler
        """
        self._sock.close()
        if self._supervisor:
            LOGGER.info("Stopping supervisor")
            self._supervisor.stop()
        LOGGER.info("Stopping worker pool")
        self._terminate()

    def broadcast(self, command: bytes):
        """ Broadcast notification to workers
        """
        try:
            self._sock.send(command, zmq.NOBLOCK)
        except zmq.ZMQError as err:
            if err.errno != zmq.EAGAIN:
                LOGGER.error("Broadcast Error %s\n%s", err, traceback.format_exc())

    def restart(self):
        """ Send restart command
        """
        self.broadcast(b'RESTART')

    def kill_worker_busy(self, pid: int) -> bool:
        """ Force kill worker
        """
        if self._supervisor:
            return self._supervisor.kill_worker_busy(pid)
        else:
            return False


def create_poolserver(
    numworkers: int,
    maxcycles: Optional[int] = None,
    initializer: Optional[Callable[[None], None]] = None,
    initargs: Sequence = (),
    timeout: int = 20,
) -> _Server:
    """ Run workers pool in its own process

        This ensure that sub-processes all always forked from
        the same parent context
    """
    broadcast = _get_ipc('broadcast')
    router = _get_ipc('pooladdr')

    p = Process(target=run_worker_pool, args=(router, broadcast, numworkers),
                kwargs=dict(initializer=initializer, initargs=initargs,
                            maxcycles=maxcycles))
    p.start()

    return _Server(broadcast, p, timeout)


def run_worker_pool(
    router: str,
    broadcastaddr: str,
    numworkers: int,
    initializer: Optional[Callable[[None], None]] = None,
    initargs: Sequence = (),
    maxcycles: Optional[int] = None,
):
    """ Run a qgis worker pool

        Ensure that child processes run in the main thread
    """
    # Try to exit gracefully
    def term_signal(signum, frames):
        # print("Caught signal: %s" % signum, file=sys.stderr)
        raise SystemExit()

    LOGGER.info("Starting worker pool")

    pool = Pool(router, broadcastaddr, numworkers,
                initializer=initializer, initargs=initargs,
                maxcycles=maxcycles)

    # Handle critical failure by sending ABORT to
    # parent process
    def abrt_signal(signum, frames):
        if pool.critical_failure:
            print("Server aborting prematurely !", file=sys.stderr)  # noqa: T201
            os.kill(os.getppid(), signal.SIGABRT)

    signal.signal(signal.SIGTERM, term_signal)
    signal.signal(signal.SIGABRT, abrt_signal)

    try:
        while True:
            pool.maintain_pool()
            time.sleep(0.1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        LOGGER.info("Terminating worker pool")
        pool.terminate()
