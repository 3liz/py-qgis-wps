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
from tornado.web import HTTPError  # noqa F401

from ..exceptions import NoApplicableCode

from ..version import __version__

from typing import Any,Union

LOGGER = logging.getLogger('SRVLOG')

class BaseHandler(tornado.web.RequestHandler):
    """ Base class for HTTP request hanlers
    """
    def initialize(self) -> None:
        super().initialize()
        self.connection_closed = False

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
        # Allow CORS on all origin
        if self.request.headers.get('Origin'):
            self.set_header('Access-Control-Allow-Origin', '*')
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

        LOGGER.debug('Request failed wint message: %s %s', message, str(exception))
 
        self.write_xml(exception.get_body())
        self.finish()

    def proxy_url(self, **kwargs: Any) -> str:
        """ Return the proxy_url
        """
        # Replace the status url with the proxy_url if any
        req = self.request
        proxy_url = self.application.config.get('host_proxy') or \
            req.headers.get('X-Forwarded-Url') or \
            "{0.protocol}://{0.host}/".format(req)
        proxy_url = proxy_url.format(**kwargs)
        return proxy_url
 

