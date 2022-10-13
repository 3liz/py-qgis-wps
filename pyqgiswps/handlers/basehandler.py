#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Base Request handler
"""
import tornado.web
import logging
import json
import lxml
import mimetypes
from pathlib import Path
from tornado.web import HTTPError  # noqa F401

from ..exceptions import NoApplicableCode

from ..version import __version__
from ..config import confservice

from typing import Any, Union, Optional, Awaitable

LOGGER = logging.getLogger('SRVLOG')

class BaseHandler(tornado.web.RequestHandler):
    """ Base class for HTTP request hanlers
    """
    def initialize(self) -> None:
        super().initialize()
        self.connection_closed = False
        self._cfg = confservice['server']
        self._cross_origin = self._cfg.getboolean('cross_origin')

    def prepare(self) -> None:
        self.has_body_arguments = len(self.request.body_arguments)>0
        # Replace query arguments to upper case:
        self.request.arguments = { k.upper():v for (k,v) in self.request.arguments.items() }

    def compute_etag(self) -> None:
        # Disable etag computation
        pass

    def set_default_headers(self) -> None:
        """ Override defaults HTTP headers
        """
        self.set_header("Server", "Py-Qgis-WPS %s" % __version__)

    def on_connection_close(self) -> None:
        """ Override, log and set 'connection_closed' to True
        """
        self.connection_closed = True
        LOGGER.warning("Connection closed by client: {}".format(self.request.uri))

    def set_option_headers(self, allow_header: Optional[str]=None) -> None:
        """  Set correct headers for 'OPTION' method
        """
        if not allow_header:
            allow_header = ', '.join( me for me in self.SUPPORTED_METHODS if hasattr(self, me.lower()) )

        self.set_header("Allow", allow_header)
        if self.set_access_control_headers():
            # Required in CORS context
            # see https://developer.mozilla.org/fr/docs/Web/HTTP/M%C3%A9thode/OPTIONS
            self.set_header('Access-Control-Allow-Methods', allow_header)

    def set_access_control_headers(self) -> bool:
        """  Handle Access control and cross origin headers (CORS)
        """
        origin = self.request.headers.get('Origin')
        if origin:
            if self._cross_origin:
                self.set_header('Access-Control-Allow-Origin', '*')
            else:
                self.set_header('Access-Control-Allow-Origin', origin)
                self.set_header('Vary', 'Origin')
            return True
        else:
            return False

    def write_xml(self, doc) -> None:
        """ XML response serializer """

        LOGGER.debug('Serializing XML response')
        wps_version_comment = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- py-qgis-wps %s -->\n') % __version__
        if isinstance(doc, str):
            xml = doc.encode('utf8')
        elif not isinstance(doc, bytes):
            xml = lxml.etree.tostring(doc, pretty_print=True)
        else:
            xml = doc

        self.set_header('Content-Type', 'text/xml;charset=utf-8')
        self.set_access_control_headers()
        self.write(wps_version_comment)
        self.write(xml)

    def write_json(self, chunk: Union[dict,str]) -> None:
        """ Write body as json

            The method will also set CORS implicitely for any origin
            If this a security issue, we should allow it
            explicitely.
        """
        if isinstance(chunk, dict):
            chunk = json.dumps(chunk, sort_keys=True)
        self.set_header('Content-Type', 'application/json;charset=utf-8')
        self.set_access_control_headers()
        self.write(chunk)

    def write_error(self, status_code: int, **kwargs: Any):
        """ Override, format error as json
        """
        message = self._reason

        if "exc_info" in kwargs:
            exception = kwargs['exc_info'][1]
            # Error was caused by a exception
            if  not isinstance(exception, NoApplicableCode ):
                exception = NoApplicableCode(message or str(exception), code=status_code)
        else:
            exception = NoApplicableCode(message, code=status_code)

        LOGGER.debug('Request failed with message: %s %s', message, str(exception))
 
        self.format_exception(exception)
        self.finish()

    def format_exception(self, exc: NoApplicableCode) -> None:
        """ Format exception 
            Override this in handler
        """
        self.write_json({
            'exceptionReport':
            {
                'code': exc.code,
                'locator': exc.locator,
                'name': exc.name,
                'description': exc.description,
            }
        })

    def proxy_url(self) -> str:
        """ Return the proxy_url
        """
        req = self.request
        if self.application.http_proxy:
            # Replace the status url with the proxy_url if any
            proxy_url = self.application.config.get('proxy_url') or \
                req.headers.get('X-Forwarded-Url')
            if proxy_url:
                if proxy_url[-1] != '/':
                    proxy_url = f"{proxy_url}/"
                return proxy_url
        
        return f"{req.protocol}://{req.host}/"


class NotFoundHandler(BaseHandler):
    def prepare(self):  # for all methods
        raise HTTPError(
            status_code=404,
            reason="Invalid resource path."
        )


class ErrorHandler(BaseHandler):
    def initialize(self, status_code: int, reason: Optional[str]=None) -> None:
        super().initialize()
        self.set_status(status_code)
        self.reason = reason

    def prepare(self) -> None:
        raise HTTPError(self._status_code, reason=self.reason)


class DownloadMixIn:

    async def download(self, path: Path, content_type=None, chunk_size=65536,
                       cache_control=None) -> Awaitable[None]:
        """ Download file
        """
        if not path.is_file():
            LOGGER.error("File '%s' not found", path)
            raise HTTPError(404,reason="Resource not found")

        # Check modification time
        mtime = str(path.stat().st_mtime)

        etag = f"'{mtime}'"
        if self.request.headers.get('If-None-Match') == etag:
            self.set_header('Etag', etag)
            self.set_status(304)
            return

        # Set headers
        if not content_type:
            content_type = mimetypes.types_map.get(path.suffix) or "application/octet-stream"

        self.set_header("Content-Type", content_type)       
        self.set_header("Etag", etag)

        if cache_control:
            self.set_header("Cache-Control", cache_control)

        # Push data
        with path.open('rb') as fp:
            while True:
                chunk = fp.read(chunk_size)
                if chunk:
                    self.write(chunk)
                    await self.flush()
                else:
                    break




