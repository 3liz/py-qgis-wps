#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original parts are Copyright 2016 OSGeo Foundation,            
# represented by PyWPS Project Steering Committee,               
# and released under MIT license.                                
# 

import asyncio
import tornado.platform.asyncio
from tornado.testing import AsyncHTTPTestCase
from contextlib import contextmanager
import shutil
import tempfile

import lxml.etree
from qywps import __version__, NAMESPACES

import logging

#logging.disable(logging.CRITICAL)

from qywps.runtime import Application
from qywps.logger import setup_log_handler


@contextmanager
def temp_dir():
    """Creates temporary directory"""
    tmp = tempfile.mkdtemp()
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp)


def _pop_kwarg(name, kwargs):
    val = kwargs.get(name)
    if val:
        del kwargs[name]
    return val

class HTTPTestCase(AsyncHTTPTestCase):
  
    def get_app(self):
        setup_log_handler('info')
        self.logger = logging.getLogger('SRVLOG')
        return Application()

    def client_for(self, service):
        self._app.wpsservice = service
        return WpsClient(self)

    def get_new_ioloop(self):
        """
        Needed to make sure that I can also run asyncio based callbacks in our tests
        """
        io_loop = tornado.platform.asyncio.AsyncIOLoop()
        asyncio.set_event_loop(io_loop.asyncio_loop)

        return io_loop


class WpsClient:

    def __init__(self, testcase):
        self._testcase = testcase

    def post(self, data):
        return WpsTestResponse(self._testcase.fetch('/ows/', method='POST', body=data, raise_error=False))

    def get(self, query):
        return WpsTestResponse(self._testcase.fetch('/ows/' + query, raise_error=False))

    def put(self, data):
        return WpsTestResponse(self._testcase.fetch('/ows/', method='PUT', body=data, raise_error=False))

    def post_xml(self, doc):
        return self.post(data=lxml.etree.tostring(doc, pretty_print=True))


class WpsTestResponse:

    def __init__(self, http_response):
        self.http_response = http_response
        if self.headers.get('Content-Type','').find('text/xml')==0:
            self.xml = lxml.etree.fromstring(self.get_data())

    def get_data(self):
        return self.http_response.body

    @property
    def status_code(self):
        return self.http_response.code

    @property
    def headers(self):
        return self.http_response.headers

    def xpath(self, path):
        return self.xml.xpath(path, namespaces=NAMESPACES)

    def xpath_text(self, path):
        return ' '.join(e.text for e in self.xpath(path))


def assert_response_accepted(resp):
    assert resp.status_code == 200, "resp.status_code = %s" % resp.status_code
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    success = resp.xpath_text('/wps:ExecuteResponse'
                              '/wps:Status'
                              '/wps:ProcessAccepted')
    assert success is not None
    # TODO: assert status URL is present


def assert_process_started(resp):
    assert resp.status_code == 200, "resp.status_code = %s" % resp.status_code
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    success = resp.xpath_text('/wps:ExecuteResponse'
                              '/wps:Status'
                              'ProcessStarted')
    # Is it still like this in PyWPS-4 ?
    assert success.split[0] == "processstarted"


def assert_response_success(resp):
    assert resp.status_code == 200, "resp.status_code = %s" % resp.status_code
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    success = resp.xpath('/wps:ExecuteResponse/wps:Status/wps:ProcessSucceeded')
    assert len(success) == 1


def assert_qywps_version(resp):
    # get first child of root element
    root_firstchild = resp.xpath('/*')[0].getprevious()
    assert isinstance(root_firstchild, lxml.etree._Comment)
    tokens = root_firstchild.text.split()
    assert len(tokens) == 2
    assert tokens[0] == 'QyWPS'
    assert tokens[1] == __version__

