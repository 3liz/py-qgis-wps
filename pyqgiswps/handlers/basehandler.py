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
import os
import tornado.web
import logging
import json
import traceback
import lxml
from tornado.web import HTTPError

from ..exceptions import NoApplicableCode

from ..version import __version__


LOGGER = logging.getLogger('SRVLOG')

class BaseHandler(tornado.web.RequestHandler):
    """ Base class for HTTP request hanlers
    """
    def initialize(self):
        super().initialize()
        self.connection_closed = False

    def prepare(self):
        self.has_body_arguments = len(self.request.body_arguments)>0
        # Replace query arguments to upper case:
        self.request.arguments = { k.upper():v for (k,v) in self.request.arguments.items() }

    def compute_etag(self):
        # Disable etag computation
        pass

    def set_default_headers(self):
        """ Override defaults HTTP headers
        """
        self.set_header("Server", "QyWPS %s" % __version__)

    def on_connection_close(self):
        """ Override, log and set 'connection_closed' to True
        """
        self.connection_closed = True
        LOGGER.warning("Connection closed by client: {}".format(self.request.uri))

    def write_xml(self, doc):
        """ XML response serializer """

        LOGGER.debug('Serializing XML response')
        wps_version_comment = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- PyQgisWPS %s -->\n') % __version__
        if isinstance(doc, str):
            xml = doc.encode('utf8')
        elif not isinstance(doc, bytes):
            xml = lxml.etree.tostring(doc, pretty_print=True)
        else:
            xml = doc

        self.set_header('Content-Type', 'text/xml;charset=utf-8')
        self.write(wps_version_comment)
        self.write(xml)

    def write_json(self, chunk):
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

    def write_error(self, status_code, **kwargs):
        """ Override, format error as json
        """
        message = self._reason

        if "exc_info" in kwargs:
            exception = kwargs['exc_info'][1]
            # Error was caused by a exception
            if  not isinstance(exception, NoApplicableCode ):
               exception = NoApplicableCode(message or str(e), code=status_code)
        else:
            exception = NoApplicableCode(message, code=status_code)

        self.write_xml(exception.get_body())
        self.finish()

    def proxy_url(self):
        """ Return the proxy_url
        """
        # Replace the status url with the proxy_url if any
        req = self.request
        proxy_url = self.application.config['host_proxy'] or \
                    req.headers.get('X-Proxy-Location') or  \
                    "{0.protocol}://{0.host}/".format(req)
        return proxy_url



