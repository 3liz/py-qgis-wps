#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import asyncio
import logging
import tornado.web
import tornado.process
import signal
import pkg_resources

from tornado.web import StaticFileHandler

from typing import Mapping, List

from .logger import log_request

from .config import confservice, get_size_bytes

from .handlers import (RootHandler, WPSHandler, StoreHandler, StatusHandler, 
                       DownloadHandler)

from .accesspolicy import init_access_policy

from pyqgisservercontrib.core.filters import ServerFilter

LOGGER = logging.getLogger('SRVLOG')


def load_filters( base_uri: str, appfilters: List[ServerFilter]=None ) -> Mapping[str,List[ServerFilter]]:
    """ Load filters and return a Mapping
    """
    import pyqgisservercontrib.core.componentmanager as cm

    filters = { base_uri: [] }

    def _add_filter( afilter ):
        uri = os.path.join(base_uri, afilter.uri)
        fls = filters.get(uri,[])
        fls.append(afilter)
        filters[uri] = fls

    if appfilters:
        for flt in appfilters:
            _add_filter(flt)

    collection = []
    cm.register_entrypoints('qgssrv_contrib_access_policy', collection, wpspolicy=True)

    for flt in collection:
        _add_filter(flt)

    # Sort filters
    for flist in filters.values():
        flist.sort(key=lambda f: f.pri, reverse=True)
    return filters


def configure_handlers( appfilters ):
    """ Set up request handlers
    """
    staticpath = pkg_resources.resource_filename("pyqgiswps", "webui")

    cfg = confservice['server']

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
        self.config     = confservice['server']
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
    from tornado.httpserver import HTTPServer

    if user:
        setuid(user)

    # Run
    LOGGER.info("Running WPS server on port %s:%s", address, port)

    from pyqgiswps.executors import processfactory

    pr_factory = processfactory.get_process_factory() 
    processes = pr_factory.initialize(True)

    max_buffer_size = get_size_bytes(confservice.get('server', 'maxbuffersize'))

    application = Application(processes)
    server = HTTPServer(application, max_buffer_size=max_buffer_size)
    server.listen(port, address=address)

    # Setup the supervisor timeout killer
    pr_factory.start_supervisor()

    try:
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT , loop.stop)
        loop.add_signal_handler(signal.SIGTERM, loop.stop)
        LOGGER.info("WPS Server ready")
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Server interrupted")
    finally:
        application.terminate()
        pr_factory.terminate()

