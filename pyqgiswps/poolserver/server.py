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
import sys
import os
import asyncio
import zmq
import zmq.asyncio
import logging
import signal
import time

from multiprocessing import Process
from typing import Callable

from .supervisor import Supervisor
from .pool import Pool
from .utils import _get_ipc

LOGGER=logging.getLogger('SRVLOG')

class _Server:

    def __init__(self, broadcastaddr: str, pool: Process,  timeout: int  ) -> None:

        ctx = zmq.asyncio.Context.instance()
        pub = ctx.socket(zmq.PUB)
        pub.setsockopt(zmq.LINGER, 500)    # Needed for socket no to wait on close
        pub.setsockopt(zmq.SNDHWM, 1)      # Max 1 item on send queue
        pub.bind(broadcastaddr)

        self._sock = pub

        sprvsr = Supervisor(timeout, lambda pid: os.kill(pid, signal.SIGKILL))
        sprvsr.run()

        LOGGER.debug("Started server")
        self._supervisor = sprvsr
        self._pool = pool

    def terminate(self):
        """ Terminate handler
        """
        self._sock.close()
        self._supervisor.stop()
        LOGGER.info("Stopping worker pool")
        self._pool.terminate()
        self._pool.join()

    def broadcast(self, command: bytes ) -> None:
        """ Broadcast notification to workers 
        """
        try:
            self._sock.send(command, zmq.NOBLOCK)
        except zmq.ZMQError as err:
            if err.errno != zmq.EAGAIN:
              LOGGER.error("Broadcast Error %s\n%s", exc, traceback.format_exc())

    def restart(self) -> None:
        """ Send restart command
        """
        self.broadcast(b'RESTART')


def create_poolserver( numworkers: int,  maxcycles: int = None,
                       initializer: Callable[[None],None] = None, initargs = (),
                       timeout: int = 20) -> _Server:
    """ Run workers pool in its own process

        This ensure that sub-processes all always forked from
        the same parent context
    """
    broadcast = _get_ipc('broadcast')
    router    = _get_ipc('pooladdr')

    p = Process(target=run_worker_pool,args=(router, broadcast, numworkers), 
                kwargs=dict(initializer = initializer, initargs=initargs,
                            maxcycles = maxcycles))
    p.start()

    return _Server(broadcast, p, timeout)


def run_worker_pool(router: str, broadcastaddr: str, numworkers: int,
                    initializer: Callable[[None],None] = None, initargs=(),
                    maxcycles: int = None) -> None:
    """ Run a qgis worker pool

        Ensure that child processes run in the main thread
    """
    # Try to exit gracefully
    def term_signal(signum,frames):
        #print("Caught signal: %s" % signum, file=sys.stderr)
        raise SystemExit()

    LOGGER.info("Starting worker pool")

    pool = Pool( router, broadcastaddr, numworkers,
                 initializer = initializer, initargs=initargs,
                 maxcycles = maxcycles)

    # Handle critical failure by sending ABORT to
    # parent process
    def abrt_signal(signum,frames):
        if pool.critical_failure:
            print("Server aborting prematurely !", file=sys.stderr)
            os.kill(os.getppid(), signal.SIGABRT)

    signal.signal(signal.SIGTERM,term_signal)
    signal.signal(signal.SIGABRT,abrt_signal)

    try:
        while True:
            pool.maintain_pool()
            time.sleep(0.1)
    except (KeyboardInterrupt,SystemExit):
        pass
    finally:
        LOGGER.info("Terminating worker pool")
        pool.terminate()


