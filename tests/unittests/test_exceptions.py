##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import unittest
from qywps import WPSProcess, Service, WPS, OWS
from qywps.app.basic import xpath_ns
from qywps.tests import HTTPTestCase, assert_qywps_version
import lxml.etree


class ExceptionsTest(HTTPTestCase):

    def setUp(self):
        super().setUp()
        self.client = self.client_for(Service(processes=[]))

    def test_invalid_parameter_value(self):
        resp = self.client.get('?service=wms')
        exception_el = resp.xpath('/ows:ExceptionReport/ows:Exception')[0]
        assert exception_el.attrib['exceptionCode'] == 'InvalidParameterValue'
        assert resp.status_code == 400
        assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
        assert_qywps_version(resp)

    def test_missing_parameter_value(self):
        resp = self.client.get('')
        exception_el = resp.xpath('/ows:ExceptionReport/ows:Exception')[0]
        assert exception_el.attrib['exceptionCode'] == 'NoApplicableCode'
        assert resp.status_code == 400
        assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'

    def test_missing_request(self):
        resp = self.client.get("?service=wps")
        exception_el = resp.xpath('/ows:ExceptionReport/ows:Exception/ows:ExceptionText')[0]
        # should mention something about a request
        assert 'Bad Request' in exception_el.text
        assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'

    def test_bad_request(self):
        resp = self.client.get("?service=wps&request=xyz")
        exception_el = resp.xpath('/ows:ExceptionReport/ows:Exception')[0]
        assert exception_el.attrib['exceptionCode'] == 'OperationNotSupported'
        assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'

