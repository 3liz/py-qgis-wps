#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import sys
import asyncio
import logging
import tornado.web
import tornado.process
import signal
import pkg_resources

from tornado.web import StaticFileHandler

from contextlib import contextmanager
from .logger import log_request, log_rrequest

from .config import (get_config, 
                     load_configuration, 
                     read_config_file, 
                     read_config_dict)

from .handlers import (RootHandler, WPSHandler, StoreHandler, StatusHandler, 
                       DownloadHandler)

from .filters import load_filters
from .accesspolicy import init_access_policy

from .version import __version__

LOGGER = logging.getLogger('SRVLOG')


def configure_handlers( appfilters ):
    """ Set up request handlers
    """
    staticpath = docpath = pkg_resources.resource_filename("pyqgiswps", "webui")

    cfg = get_config('server')

    workdir = cfg['workdir']
    dnl_ttl = cfg.getint('download_ttl')

    init_access_policy()

    def ows_handlers():
        # Load filters overriding '/ows/'
        if cfg.getboolean('enable_filters'):
            filters = load_filters(r"/ows/", appfilters=appfilters)
            for uri,fltrs in filters.items():
                yield (uri, WPSHandler, dict(filters=fltrs) )
        else:
            yield (r"/ows/", WPSHandler)

    handlers = [ (r"/"     , RootHandler) ]
    handlers.extend( ows_handlers() )
    handlers.extend( [
        (r"/ows/store/([^/]+)/(.*)?", StoreHandler, { 'workdir': workdir }),
        (r"/ows/status/([^/]+)?", StatusHandler),
        # Add theses as shortcuts
        (r"/store/([^/]+)/(.*)?", StoreHandler, { 'workdir': workdir }),
        (r"/status/([^/]+)?", StatusHandler),
        # Temporary download url api
        (r"/dnl/(_)/([^/]+)", DownloadHandler, { 'workdir': workdir }),
        (r"/dnl/([^/]+)/(.*)", DownloadHandler, { 'workdir': workdir, 'query': True, 'ttl': dnl_ttl }),
        # Web ui anagement
        (r"/ui/(.*)", StaticFileHandler, {
            'path': staticpath, 
            'default_filename':"dashboard.html"
        }),
    ] )

    return handlers


class Application(tornado.web.Application):

    def __init__(self, processes=[], filters=None):
        from pyqgiswps.app.Service import Service
        self.wpsservice = Service(processes=processes)
        self.config     = get_config('server')
        super().__init__(configure_handlers( filters ))

    def log_request(self, handler):
        """ Write HTTP requet to the logs
        """
        log_request(handler)

    def terminate(self):
        self.wpsservice.terminate()


def setuid(username):
    """ setuid to username uid """
    from pwd import getpwnam, getpwuid
    pw = getpwnam(username)
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    LOGGER.info("Setuid to user {} ({}:{})".format(getpwuid(os.getuid()).pw_name, os.getuid(), os.getgid()))


def run_server( port, address=None, user=None ):
    """ Run the server
    """
    import traceback
    from tornado.httpserver import HTTPServer

    if user:
       setuid(user)

    # Run
    LOGGER.info("Running WPS server %s on port %s:%s", __version__, address, port)

    from pyqgiswps.executors import processfactory

    pr_factory = processfactory.get_process_factory() 
    pr_factory.initialize()

    application = Application()
    server = HTTPServer(application)
    server.listen(port, address=address)

    # Setup the supervisor timeout killer
    pr_factory.start_supervisor()

    try:
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT , loop.stop)
        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        LOGGER.info("WPS Server ready")
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        LOGGER.info("Server interrupted")
    finally:
        application.terminate()
        pr_factory.terminate()

