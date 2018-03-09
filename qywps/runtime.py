##################################################################
# Copyright 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################
import os
import sys
import asyncio
import logging
import tornado.web
import tornado.process
import signal

from contextlib import contextmanager
from .logger import log_request, log_rrequest

from .configuration import (get_config, 
                            load_configuration, 
                            read_config_file, 
                            read_config_dict)

from .handlers import RootHandler, WPSHandler, StoreHandler, StatusHandler

LOGGER = logging.getLogger("QYWPS")


def configure_handlers( processes ):
    """ Set up request handlers
    """

    workdir = get_config('server')['workdir']

    handlers = [
        (r"/"     , RootHandler),
        (r"/ows/" , WPSHandler ),
        (r"/ows/store/([^/]+)/(.*)?", StoreHandler, { 'workdir': workdir }),
        (r"/ows/status/([^/]+)?", StatusHandler),
    ]

    return handlers


class Application(tornado.web.Application):

    def __init__(self, processes=[], executor=None):
        from qywps.app.Service import Service
        self.wpsservice = Service(processes=processes, executor=executor)
        self.config     = get_config('server')
        super().__init__(configure_handlers( processes ))

    def log_request(self, handler):
        """ Write HTTP requet to the logs
        """
        log_request(handler)

    def terminate(self):
        """ Close resources
        """
        self.wpsservice.terminate()



def terminate_handler(signum, frame):
    """ Terminate child processes """
    if 'children' in frame.f_locals and signum == signal.SIGTERM:
        sys.stderr.write("Terminating child processes.\n")
        for p in frame.f_locals['children']:
            os.kill(p, signal.SIGTERM)


def interrupt_handler(signum, frame):
    """ Handle INT signal """
    raise SystemExit("%s: Caught signal %s" % (os.getpid(), signum))


def setuid(username):
    """ setuid to username uid """
    from pwd import getpwnam, getpwuid
    pw = getpwnam(username)
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    LOGGER.info("Setuid to user {} ({}:{})".format(getpwuid(os.getuid()).pw_name, os.getuid(), os.getgid()))


def set_signal_handlers():
    signal.signal(signal.SIGTERM, terminate_handler)
    signal.signal(signal.SIGINT,  interrupt_handler)


def clear_signal_handlers():
    signal.signal(signal.SIGTERM, signal.SIG_DFL)


def run_server( port, address="", jobs=1, user=None ):
    """ Run the server
    """
    import traceback
    from tornado.netutil import bind_sockets
    from tornado.httpserver import HTTPServer

    sockets = bind_sockets(port, address=address)

    server = None

    if user:
       setuid(user)

    set_signal_handlers()

    # Fork processes
    if jobs > 1:
        import tornado.process
        tornado.process.fork_processes(jobs, max_restarts=10)
        task_id = tornado.process.task_id()
    else:
        task_id = os.getpid()

    # Install asyncio event loop after forking
    # This is why we do not use server.bind/server.start
    import tornado.platform.asyncio
    tornado.platform.asyncio.AsyncIOMainLoop().install()

    # Run
    LOGGER.info("Running server on port %s:%s", address, port)
    try:
        if task_id is not None:
            # Clean up signals handlers
            clear_signal_handlers()                
            from qywps.executors.processingexecutor import ProcessingExecutor
            app    = Application(executor=ProcessingExecutor())
            server = HTTPServer(app)
            server.add_sockets(sockets)

            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
            LOGGER.info("WPS Server ready")
            loop.run_forever()
    except Exception:
        traceback.print_exc()
    except SystemExit as e:
        print("%s" % e, file=sys.stderr) 

    # Teardown
    pid = os.getpid()
    if server is not None:
        server.stop()
        server = None
        app.terminate()
        # Close the loop
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.close()
        print("{}: Worker stopped".format(pid), file=sys.stderr, flush=True)
    
