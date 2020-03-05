#
# Copyright 2020 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import logging
import traceback
import zmq
import uuid
import pickle

from typing import Callable

from .utils import WORKER_READY
from .supervisor import Client as SupervisorClient

LOGGER=logging.getLogger('SRVLOG')


def dealer_socket( ctx: zmq.Context, address: str ) -> zmq.Socket:
    """ Socket for receiving incoming messages
    """
    LOGGER.debug("Connecting to %s", address)
    sock = ctx.socket(zmq.DEALER)
    sock.setsockopt(zmq.LINGER, 500)    # Needed for socket no to wait on close
    sock.setsockopt(zmq.SNDHWM, 1)      # Max 1 item on send queue
    sock.setsockopt(zmq.IMMEDIATE, 1)   # Do not queue if no peer, will block on send
    sock.setsockopt(zmq.RCVTIMEO, 1000) # Heartbeat
    sock.identity = uuid.uuid1().bytes
    LOGGER.debug("Identity set to %s", sock.identity)
    sock.connect(address)
    return sock
   

def broadcast_socket( ctx: zmq.Context, broadcastaddr: str ) -> zmq.Socket:
    """ Socket for receiving broadcast message notifications
    """
    LOGGER.debug("Enabling broadcast notification")
    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt(zmq.LINGER, 500)    # Needed for socket no to wait on close
    sub.setsockopt(zmq.SUBSCRIBE, b'RESTART')
    sub.connect(broadcastaddr)
    return sub


def worker_handler( router: str, broadcastaddr: str, maxcycles: int = None, 
                    initializer: Callable[[None],None] = None, initargs = ()) -> None:
    """ Run jobs
    """
    ctx = zmq.Context.instance()

    sock = dealer_socket( ctx, router )
    sub  = broadcast_socket( ctx, broadcastaddr )
        
    # Initialize supervisor client
    supervisor = SupervisorClient()

    if initializer is not None:
        initializer(*initargs)

    def get():
        corr_id, rest = sock.recv_multipart()
        LOGGER.debug("RCV %s", corr_id)
        return corr_id, pickle.loads(rest)

    def set( corr_id, res ):
        LOGGER.debug("SND %s", corr_id)
        sock.send_multipart([corr_id, pickle.dumps(res)]) 

    try:
        LOGGER.debug("Starting ZMQ worker loop")
        completed = 0
        while maxcycles is None or (maxcycles and completed < maxcycles):
            sock.send(WORKER_READY)
            try:
                jobid, (func, args, kwargs) = get()
                supervisor.notify_busy()
                try:
                    result = (True, func( *args, **kwargs ))
                except Exception as exc:
                    LOGGER.error("Worker Error: %s\n%s", exc, traceback.format_exc())
                    result = (False, exc)

                supervisor.notify_done()
                set( jobid, result )
                completed += 1
            except zmq.error.Again:
                pass

            jobid = func = args = kwargs = None
            # Handle broadcast restart
            try:
                if broadcastaddr and sub.recv(flags=zmq.NOBLOCK)==b'RESTART':
                   # There is no really way to restart
                   # so exit and let the framework restart a wew worker
                   LOGGER.info("RESTART notification received")
                   break
            except zmq.error.Again:
                pass
    except (KeyboardInterrupt, SystemExit):
            pass

    sub.close()
    sock.close()
    LOGGER.info("Terminating Worker")

