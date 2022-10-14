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

from tornado.testing import AsyncHTTPTestCase
from contextlib import contextmanager
import shutil
import tempfile
import json

import lxml.etree
from pyqgiswps import __version__
from pyqgiswps.ogc.ows.schema import NAMESPACES

from pyqgiswps.runtime import Application, initialize_middleware
from pyqgiswps.logger import configure_log_levels
from pyqgiswps.executors import processfactory
from pyqgiswps.config import load_configuration, confservice

from typing import Any, Optional, Dict

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


class TestRuntime:

    def __init__(self) -> None:
        self.started = False

    def start(self) -> None:
        if self.started:
            return

        configure_log_levels()
        load_configuration()
        self.factory = processfactory.get_process_factory()
        self.factory.initialize()

        # Get cachemanager ATFER loading configuration
        from pyqgiswps.qgscache.cachemanager import cacheservice
        self.cachemanager = cacheservice

        # Ensure Qgis is initialized
        self.factory.start_qgis() 
        self.started = True

    def stop(self) -> None:
        if not self.started:
            return
        # Clear cache earlier in order to prevent memory corruption 
        # when projects are freed
        self.cachemanager.clear()
        self.started = False
        self.factory.terminate()        

    @classmethod
    def instance(cls) -> 'TestRuntime':
        if not hasattr(cls,'_instance'):
            cls._instance = TestRuntime()
        return cls._instance        

@contextmanager
def chconfig(section, key, value):
    """ Use configuration setting
    """
    prev = confservice.get(section,key)
    try:
        confservice.set(section,key,value)
        yield prev
    finally:
        confservice.set(section,key,prev)


class HTTPTestCase(AsyncHTTPTestCase):
 
    def get_app(self) ->  Application:
        configure_log_levels()
        self._application =  Application(processes=self.get_processes())
        return initialize_middleware(self._application, filters=self.get_filters())

    def tearDown(self) -> None:
        self._application.terminate()
        super().tearDown()


    @property
    def client(self):
        return WpsClient(self)

    def get_processes(self):
        """ Return custom processes
        """
        return []

    def get_filters(self):
        """ Return custom filters

            Override in tests
        """
        return None


class WpsTestResponse:

    def __init__(self, http_response):
        self.http_response = http_response
        if self.headers.get('Content-Type','').find('text/xml')==0:
            self.xml = lxml.etree.fromstring(self.get_data())

    def get_data(self) -> Any:
        return self.http_response.body

    @property
    def body(self) -> Any:
        return self.http_response.body

    @property
    def code(self) -> int:
        return self.http_response.code

    @property
    def status_code(self) -> int:
        return self.http_response.code

    @property
    def headers(self):
        return self.http_response.headers

    def xpath(self, path) -> 'xpath':
        return self.xml.xpath(path, namespaces=NAMESPACES)

    def xpath_text(self, path) -> str:
        return ' '.join(e.text for e in self.xpath(path))


#
# OWS WPS Client/Response
#

class WpsClient:

    def __init__(self, testcase):
        self._testcase = testcase

    def post(self, data, headers: Optional[Dict]=None, path: str='/ows/') -> WpsTestResponse:
        return WpsTestResponse(self._testcase.fetch(path, method='POST', 
                               body=data, raise_error=False, headers=headers))

    def get(self, query, headers: Optional[Dict]=None, path: str='/ows/') -> WpsTestResponse:
        return WpsTestResponse(self._testcase.fetch(path + query, raise_error=False,
                               headers=headers))

    def put(self, data, headers: Optional[Dict]=None, path: str='/ows/') -> WpsTestResponse:
        return WpsTestResponse(self._testcase.fetch(path, method='PUT', 
                               body=data, raise_error=False, headers=headers))

    def post_xml(self, doc, path='/ows/') -> WpsTestResponse:
        return self.post(data=lxml.etree.tostring(doc, pretty_print=True), path=path)

    def options( self, headers: Optional[Dict]=None, path: str='/ows/') -> WpsTestResponse:
        return WpsTestResponse(self._testcase.fetch(path, method='OPTIONS',
                               raise_error=False, headers=headers)) 


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


def assert_pyqgiswps_version(resp):
    # get first child of root element
    root_firstchild = resp.xpath('/*')[0].getprevious()
    assert isinstance(root_firstchild, lxml.etree._Comment)
    tokens = root_firstchild.text.split()
    assert len(tokens) == 2
    assert tokens[0] == 'py-qgis-wps'
    assert tokens[1] == __version__


#
# Generic HTTP Client/Response
#

class HttpResponse:

    def __init__(self, http_response):
        self.http_response = http_response

    @property
    def body(self) -> Any:
        return self.http_response.body

    @property
    def status_code(self) -> int:
        return self.http_response.code

    @property
    def headers(self):
        return self.http_response.headers

    @property
    def json(self):
        if self.headers.get('Content-Type','').find('application/json')==0:
            return json.loads(self.body)


class HttpClient:

    def __init__(self, testcase):
        self._testcase = testcase

    def post(self, path: str, data: Any, headers: Optional[Dict]=None) -> HttpResponse:
        return HttpResponse(self._testcase.fetch(path, method='POST', 
                            body=data, raise_error=False, headers=headers))

    def get(self, path, headers: Optional[Dict]=None) -> HttpResponse:
        return HttpResponse(self._testcase.fetch(path, raise_error=False,
                            headers=headers))

    def put(self, path, data, headers: Optional[Dict]=None) -> HttpResponse:
        return HttpResponse(self._testcase.fetch(path, method='PUT', 
                            body=data, raise_error=False, headers=headers))

    def options(self, path, headers: Optional[Dict]=None) -> HttpResponse:
        return HttpResponse(self._testcase.fetch(path, method='OPTIONS',
                            raise_error=False, headers=headers))

    def post_json(self, path, data, headers: Optional[Dict]=None) -> HttpResponse:
        return self.post(path, json.dumps(data), headers=headers)
