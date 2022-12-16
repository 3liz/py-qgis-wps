#
# Copyright 2020 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import sys
import os
import logging
import argparse
import traceback
import time
import threading
import asyncio
import signal

from .server import create_poolserver
from .client import create_client, RequestBackendError

LOGGER = logging.getLogger('SRVLOG')


def initializer(*args):
    is_main_thread = threading.current_thread() is threading.main_thread()
    print("[%s]" % os.getpid(), "Initializer args:", args, flush=True)
    print("[%s]" % os.getpid(), "Initializer is in main thread:", is_main_thread, flush=True)


def job_ok(*args, **kwargs):
    return "OK: %s %s" % (args, kwargs)


def job_fail(*args, **kwars):
    raise Exception("I'have failed")


def job_timeout(*args, **kwars):
    time.sleep(20)


async def run_test(job, client, timeout):
    try:
        rv = await client.apply_async(job, args=('foobar',), kwargs={'bar': 'foo'}, timeout=timeout)
        print("======>", rv, flush=True)
    except RequestBackendError as exc:
        LOGGER.error("Worker returned exception '%s'", exc.response)
    except Exception as exc:
        LOGGER.error("Catched exception %s", exc)
        traceback.print_exc()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Pool server')
    parser.add_argument('--maxqueue', metavar='NUM', type=int, default=100, help="Max waiting queue")
    parser.add_argument('--timeout', metavar='NUM', type=int, default=3, help="Set timeout in ms for waiting requests")
    parser.add_argument('--workers', metavar='NUM', type=int, default=1, help="Number of workers")
    parser.add_argument('--maxcycles', metavar='NUM', type=int, default=10, help="Max number of run cycles")
    parser.add_argument('--job-timeout', metavar='NUM', type=int, default=8, help="Job timeout")

    args = parser.parse_args()

    timeout = args.timeout

    server = create_poolserver(args.workers, maxcycles=args.maxcycles,
                               initializer=initializer,
                               initargs=('foobar',),
                               timeout=args.job_timeout)
    try:
        client = create_client(args.maxqueue)

        async def _main():
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, loop.stop)
            loop.add_signal_handler(signal.SIGINT, loop.stop)

            await asyncio.wait([
                run_test(job_ok, client, timeout),
                run_test(job_fail, client, timeout),
            ])

            server.restart()

            await asyncio.wait([
                run_test(job_ok, client, timeout),
                run_test(job_timeout, client, timeout),
            ])

        asyncio.run(_main())

        client.close()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Server interrupted")
    finally:
        server.terminate()
    print("DONE", file=sys.stderr)
