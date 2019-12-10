#
# Copyright 2020 3liz
# Author David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" Pool server 
"""
import os
import sys
import logging
import time
import signal

from multiprocessing import Process
from multiprocessing.util import Finalize

from typing import Callable

from .worker import worker_handler

# Early failure min delay
# If any process fail before that starting delay
# we abort the whole process
EARLY_FAILURE_DELAY = 2

LOGGER = logging.getLogger('SRVLOG')


class Pool:

    def __init__(self, router: str, broadcastaddr: str, numworkers: int,
                 initializer: Callable[[None],None] = None, initargs=(),
                 maxcycles: int = None) -> None:

        self.critical_failure = False

        self._router = router
        self._broadcastaddr = broadcastaddr
        self._num_workers = numworkers
        self._pool = []
        self._maxcycles = maxcycles
        self._initializer = initializer
        self._initargs = initargs
        self._start_time = time.time()

        # Ensure that pool is terminated is called
        # at process exit
        self._terminate = Finalize(
            self, self._terminate_pool, 
            args=(self._pool,),
            exitpriority=15
        )

        self._repopulate_pool()

    def _join_exited_workers(self) -> bool:
        """Cleanup after any worker processes which have exited due to reaching
           their specified lifetime.  
           
           Returns True if any workers were cleaned up.
        """
        cleaned = False
        for i in reversed(range(len(self._pool))):
            worker = self._pool[i]
            if worker.exitcode is not None:
                if worker.exitcode != 0:
                    # Handle early failure by killing current process
                    LOGGER.warning("Qgis Worker exited with code %s", worker.exitcode) 
                    if time.time() - self._start_time < EARLY_FAILURE_DELAY:
                        # Critical exit
                        LOGGER.critical("Critical worker failure. Aborting...")
                        self.critical_failure = True
                        os.kill(os.getpid(), signal.SIGABRT)
                # worker exited
                worker.join()
                cleaned = True
                del self._pool[i]
        return cleaned

    def _repopulate_pool(self) -> None:
        """Bring the number of pool processes up to the specified number,
        for use after reaping workers which have exited.
        """
        for _ in range(self._num_workers - len(self._pool)):
            w = Process(target=worker_handler, args=(self._router, self._broadcastaddr),
                                      kwargs=dict( maxcycles   = self._maxcycles,
                                                   initializer = self._initializer,
                                                   initargs    = self._initargs))
            self._pool.append(w)
            w.name = w.name.replace('Process', 'PoolWorker')
            w.start()

    def maintain_pool(self) -> None:
        """Clean up any exited workers and start replacements for them.
        """
        if self._join_exited_workers():
            self._repopulate_pool()

    @classmethod
    def _terminate_pool(cls, pool: 'Pool') -> None: 

        # Send terminate to workers
        if pool and hasattr(pool[0], 'terminate'):
            for p in pool:
                if p.exitcode is None:
                    p.terminate()

        # Join pool workers
        if pool and hasattr(pool[0], 'terminate'):
            for p in pool:
                if p.is_alive():
                    # worker has not yet exited
                    p.join()

    def __reduce__(self) -> None:
        raise NotImplementedError(
            'Pool objects cannot be passed between processes or pickled'
        )

    def terminate(self) -> None:
        self._terminate()

      
