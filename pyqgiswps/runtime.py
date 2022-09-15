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

from tornado.web import RedirectHandler, StaticFileHandler

from .logger import log_request
from .config import confservice, get_size_bytes
from .handlers import (
    ServerInfosHandler,
    LandingPageHandler,
    ConformanceHandler,
    ProcessHandler,
    ExecuteHandler,
    JobHandler,
    ResultHandler,
    OWSHandler, 
    StoreHandler, 
    StatusHandler,
    HtmlHandler,
    DownloadHandler,
    NotFoundHandler,
    ErrorHandler,
)

from .accesspolicy import init_access_policy, new_access_policy

LOGGER = logging.getLogger('SRVLOG')


def configure_handlers():
    """ Set up request handlers
    """
    staticpath = pkg_resources.resource_filename("pyqgiswps", "webui")

    cfg = confservice['server']

    workdir = cfg['workdir']
    dnl_ttl = cfg.getint('download_ttl')

    init_access_policy()

    default_access_policy = new_access_policy()

    ogcapi_init_args = {
        'access_policy': default_access_policy,
    }

    #json_end = '(?:\.json)'

    handlers = [ 
        (r"/", LandingPageHandler),
        # OWS Api
        (r"/ows/", OWSHandler, {'access_policy': default_access_policy}),
        # OGC Api
        (r"/processes/([^/]+)/execution", ExecuteHandler, ogcapi_init_args),
        (r"/processes/([^/]+)", ProcessHandler, ogcapi_init_args),
        (r"/processes/?", ProcessHandler, ogcapi_init_args),
        
        (r"/jobs/?", JobHandler, ogcapi_init_args),
        (r"/jobs/([^/\.]+)", JobHandler, ogcapi_init_args),
        (r"/jobs/([^/\.]+)/results", ResultHandler, ogcapi_init_args),

        # HTML jobs handler

        (r"/jobs\.html/?", HtmlHandler,  {
            'path': staticpath, 
            'filename':"dashboard.html",
        }),
        (r"/jobs\.html/(.+)", StaticFileHandler, { 'path': staticpath }),

        (r"/jobs/[^/\.]+\.html/?", HtmlHandler, {
            'path': staticpath, 
            'filename':"details.html",
        }),
        (r"/jobs/[^/\.]+\.html/(.+)", StaticFileHandler, { 'path': staticpath }),

        # Job Resources
        (r"/jobs/([^/]+)/files(?:/(.*))?", StoreHandler, {'workdir': workdir, 'ttl': dnl_ttl}),

        # Conformance
        (r"/conformance/?", ConformanceHandler),

        # Temporary download url api
        (r"/dnl/([^/]+)", DownloadHandler, {'workdir': workdir}),
    ]

    # XXX Deprecated apis
    handlers.extend((
        (r"/status/([^/]+)?", StatusHandler),
        (r"/store/([^/]+)/(.*)?", StoreHandler, {'workdir': workdir, 'legacy': True}),

        (r"/ui/", RedirectHandler, {'url': "/jobs.html"}),
        (r"/ows/store/([^/]+)/(.*)?", RedirectHandler, {'url': "/store/{0}/{1}"}),
        (r"/ows/status/([^/]+)?", RedirectHandler, {'url': "/status/{0}"}),
    ))

    if cfg.getboolean('expose_server_infos'):
        handlers.append((r"/server/?", ServerInfosHandler))

    return handlers


class Application(tornado.web.Application):

    def __init__(self, processes=[]):
        from pyqgiswps.app.service import Service
        self.wpsservice = Service(processes=processes)
        self.config     = confservice['server']

        super().__init__(configure_handlers(), default_handler_class=NotFoundHandler)

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


def create_ssl_options():
    """ Create an ssl context
    """
    import ssl
    cfg = confservice['server']
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(cfg['ssl_cert'],cfg['ssl_key'])
    return ssl_ctx


def initialize_middleware( app, filters=None ): 
    """ Initialize the middleware
    """
    if confservice.getboolean('server','enable_filters'):
        from .middleware import MiddleWareRouter
        router = MiddleWareRouter(app, filters)
    else:
        router = app

    return router


def run_server( port, address=None, user=None ):
    """ Run the server
    """
    from tornado.httpserver import HTTPServer

    if user:
        setuid(user)

    kwargs = {}

    # Setup ssl config
    if confservice.getboolean('server','ssl'):
        LOGGER.info("SSL enabled")
        kwargs['ssl_options'] = create_ssl_options()

    # Allow x-forward headers
    kwargs['xheaders'] = True

    # Run
    LOGGER.info("Running WPS server on port %s:%s", address, port)

    from pyqgiswps.executors import processfactory

    pr_factory = processfactory.get_process_factory() 
    processes = pr_factory.initialize(True)

    max_buffer_size = get_size_bytes(confservice.get('server', 'maxbuffersize'))

    application = Application(processes)
    server = HTTPServer(initialize_middleware(application), max_buffer_size=max_buffer_size, **kwargs)
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

