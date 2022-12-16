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
    LogsHandler,
    DownloadHandler,
    NotFoundHandler,
    OpenApiHandler,
)

from .handlers import (
    StatusHandler,
)

from .accesspolicy import init_access_policy, new_access_policy

LOGGER = logging.getLogger('SRVLOG')


def configure_handlers():
    """ Set up request handlers
    """
    staticpath = pkg_resources.resource_filename("pyqgiswps", "html")
    openapipath = pkg_resources.resource_filename("pyqgiswps", "openapi")

    cfg = confservice['server']

    workdir = cfg['workdir']
    dnl_ttl = cfg.getint('download_ttl')

    init_access_policy()

    default_access_policy = new_access_policy()

    ogcapi_init_args = {
        'access_policy': default_access_policy,
    }

    # json_end = '(?:\.json)'

    # WPS service URL
    # This follow the convention used in Qgis server
    ows_service_url = \
        os.getenv('QGIS_SERVER_SERVICE_URL') or \
        os.getenv('QGIS_SERVER_WPS_SERVICE_URL')

    handlers = [
        #
        # Landing page
        #
        (r"/", LandingPageHandler),

        #
        # OWS
        #
        (r"/ows/", OWSHandler, {
            'access_policy': default_access_policy,
            'service_url': ows_service_url,
        }),

        #
        # /processes
        #
        (r"/processes/([^/]+)/execution", ExecuteHandler, ogcapi_init_args),
        (r"/processes/([^/]+)", ProcessHandler, ogcapi_init_args),
        (r"/processes/?", ProcessHandler, ogcapi_init_args),

        #
        # /jobs
        #
        (r"/jobs/?", JobHandler, ogcapi_init_args),
        (r"/jobs/([^/\.]+)", JobHandler, ogcapi_init_args),
        (r"/jobs/([^/\.]+)/results", ResultHandler, ogcapi_init_args),

        # HTML jobs handler
        (r"/jobs\.html/?(.*)", StaticFileHandler, {
            'path': staticpath,
            'default_filename': "dashboard.html",
        }),

        (r"/jobs/[^/\.]+\.html/?(.*)", StaticFileHandler, {
            'path': staticpath,
            'default_filename': "details.html",
        }),

        # XXX Thoses are sensible apis

        # Job Resources
        (r"/jobs/([^/]+)/files(?:/(.*))?", StoreHandler, {'workdir': workdir, 'ttl': dnl_ttl}),

        # Logs
        (r"/jobs/([^/]+)/logs/?", LogsHandler, {'workdir': workdir}),

        # Temporary download url api
        (r"/dnl/([^/]+)", DownloadHandler, {'workdir': workdir}),

        #
        # Conformance
        #
        (r"/conformance/?", ConformanceHandler),

        #
        # Open api
        #
        (r"/api(?:/(.*))?", OpenApiHandler, {'path': openapipath}),
    ]

    if cfg.getboolean('expose_server_infos'):
        handlers.append((r"/server/?", ServerInfosHandler))

    # XXX Deprecated apis
    handlers.extend((
        (r"/status/([^/]+)?", StatusHandler),
        (r"/store/([^/]+)/(.*)?", StoreHandler, {'workdir': workdir, 'legacy': True}),

        (r"/ui/", RedirectHandler, {'url': "/jobs.html"}),
        (r"/ows/store/([^/]+)/(.*)?", RedirectHandler, {'url': "/store/{0}/{1}"}),
        (r"/ows/status/([^/]+)?", RedirectHandler, {'url': "/status/{0}"}),
    ))

    return handlers


class Application(tornado.web.Application):

    def __init__(self, processes=[]):
        from pyqgiswps.app.service import Service
        self.wpsservice = Service(processes=processes)
        self.config = confservice['server']
        self.http_proxy = self.config.getboolean('http_proxy')

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
    ssl_ctx.load_cert_chain(cfg['ssl_cert'], cfg['ssl_key'])
    return ssl_ctx


def initialize_middleware(app, filters=None):
    """ Initialize the middleware
    """
    if confservice.getboolean('server', 'enable_filters'):
        from .middleware import MiddleWareRouter
        router = MiddleWareRouter(app, filters)
    else:
        router = app

    return router


def run_server(port, address=None, user=None):
    """ Run the server
    """
    from tornado.httpserver import HTTPServer

    if user:
        setuid(user)

    kwargs = {}

    # Setup ssl config
    if confservice.getboolean('server', 'ssl'):
        LOGGER.info("SSL enabled")
        kwargs['ssl_options'] = create_ssl_options()

    if confservice.getboolean('server', 'http_proxy'):
        # Allow x-forward headers
        LOGGER.info("Proxy configuration enabled")
        kwargs['xheaders'] = True

    application = None
    pr_factory = None

    # Since python 3.10 and deprecation of `get_event_loop()`
    # This is now the preferred way to start tornado application
    # See https://www.tornadoweb.org/en/stable/guide/running.html
    async def _main():
        # Run
        LOGGER.info("Running WPS server on port %s:%s", address, port)

        from pyqgiswps.executors import processfactory

        nonlocal pr_factory
        pr_factory = processfactory.get_process_factory()
        processes = pr_factory.initialize(True)

        max_buffer_size = get_size_bytes(confservice.get('server', 'maxbuffersize'))

        nonlocal application
        application = Application(processes)
        server = HTTPServer(initialize_middleware(application), max_buffer_size=max_buffer_size, **kwargs)
        server.listen(port, address=address)

        # Setup the supervisor timeout killer
        pr_factory.start_supervisor()

        event = asyncio.Event()

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, event.set)
        loop.add_signal_handler(signal.SIGTERM, event.set)

        LOGGER.info("WPS Server ready")

        # Wait forever until event is set
        # see https://www.tornadoweb.org/en/stable/guide/running.html
        await event.wait()

    try:
        LOGGER.info("WPS Server ready")
        asyncio.run(_main())
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Server interrupted")
    finally:
        if application:
            application.terminate()
        if pr_factory:
            pr_factory.terminate()
