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

import lxml.etree
from pyqgiswps import __version__, NAMESPACES


from pyqgiswps.runtime import Application
from pyqgiswps.logger import configure_log_levels
from pyqgiswps.executors import processfactory
from pyqgiswps.config import load_configuration

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
        # Ensure Qgis is initialized
        self.factory.start_qgis() 
        self.started = True

    def stop(self) -> None:
        if not self.started:
            return
        self.factory.terminate()        

    @classmethod
    def instance(cls) -> 'TestRuntime':
        if not hasattr(cls,'_instance'):
            cls._instance = TestRuntime()
        return cls._instance        


class HTTPTestCase(AsyncHTTPTestCase):
 
    def get_app(self) ->  Application:
        configure_log_levels()
        self._application =  Application(processes=self.get_processes(),filters=self.get_filters())
        return self._application

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


class WpsClient:

    def __init__(self, testcase):
        self._testcase = testcase

    def post(self, data, headers=None, path='/ows/'):
        return WpsTestResponse(self._testcase.fetch(path, method='POST', 
                               body=data, raise_error=False, headers=headers))

    def get(self, query, headers=None, path='/ows/'):
        return WpsTestResponse(self._testcase.fetch(path + query, raise_error=False,
                               headers=headers))

    def put(self, data, headers=None, path='/ows/'):
        return WpsTestResponse(self._testcase.fetch(path, method='PUT', 
                               body=data, raise_error=False, headers=headers))

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


def assert_pyqgiswps_version(resp):
    # get first child of root element
    root_firstchild = resp.xpath('/*')[0].getprevious()
    assert isinstance(root_firstchild, lxml.etree._Comment)
    tokens = root_firstchild.text.split()
    assert len(tokens) == 2
    assert tokens[0] == 'py-qgis-wps'
    assert tokens[1] == __version__

