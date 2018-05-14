##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import unittest
import lxml
import lxml.etree
from qywps.app import Process, Service
from qywps.app.Common import Metadata
from qywps import WPS, OWS
from qywps.tests import HTTPTestCase, assert_qywps_version

class BadRequestTest(HTTPTestCase):

    def test_bad_http_verb(self):
        client = self.client_for(Service())
        resp = client.put('')
        assert resp.status_code == 405  # method not allowed

    def test_bad_request_type_with_get(self):
        client = self.client_for(Service())
        resp = client.get('?Request=foo')
        assert resp.status_code == 400

    def test_bad_service_type_with_get(self):
        client = self.client_for(Service())
        resp = client.get('?service=foo')

        exception = resp.xpath('/ows:ExceptionReport'
                                '/ows:Exception')

        assert resp.status_code == 400
        assert exception[0].attrib['exceptionCode'] == 'InvalidParameterValue'

    def test_bad_request_type_with_post(self):
        client = self.client_for(Service())
        request_doc = WPS.Foo()
        resp = client.post_xml(doc=request_doc)
        assert resp.status_code == 400


class CapabilitiesTest(HTTPTestCase):

    def setUp(self):
        super().setUp()

        def pr1(): pass
        def pr2(): pass

        self.client = self.client_for(Service(processes=[Process(pr1, 'pr1', 'Process 1', metadata=[Metadata('pr1 metadata')]), Process(pr2, 'pr2', 'Process 2', metadata=[Metadata('pr2 metadata')])]))

    def check_capabilities_response(self, resp):
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
        title = resp.xpath_text('/wps:Capabilities'
                                '/ows:ServiceIdentification'
                                '/ows:Title')
        assert title != ''
        names = resp.xpath_text('/wps:Capabilities'
                                '/wps:ProcessOfferings'
                                '/wps:Process'
                                '/ows:Identifier')
        assert sorted(names.split()) == ['pr1', 'pr2']

        metadatas = resp.xpath('/wps:Capabilities'
                               '/wps:ProcessOfferings'
                               '/wps:Process'
                               '/ows:Metadata')
        assert len(metadatas) == 2


    def test_get_request(self):
        resp = self.client.get('?Request=GetCapabilities&service=WpS')
        self.check_capabilities_response(resp)

        # case insesitive check
        resp = self.client.get('?request=getcapabilities&service=wps')
        self.check_capabilities_response(resp)

    def test_post_request(self):
        request_doc = WPS.GetCapabilities()
        resp = self.client.post_xml(doc=request_doc)
        self.check_capabilities_response(resp)

    def test_get_bad_version(self):
        resp = self.client.get('?request=getcapabilities&service=wps&acceptversions=2001-123')
        exception = resp.xpath('/ows:ExceptionReport'
                                '/ows:Exception')
        assert resp.status_code == 400
        assert exception[0].attrib['exceptionCode'] == 'VersionNegotiationFailed'

    def test_post_bad_version(self):
        acceptedVersions_doc = OWS.AcceptVersions(
                OWS.Version('2001-123'))
        request_doc = WPS.GetCapabilities(acceptedVersions_doc)
        resp = self.client.post_xml(doc=request_doc)
        exception = resp.xpath('/ows:ExceptionReport'
                                '/ows:Exception')

        assert resp.status_code == 400
        assert exception[0].attrib['exceptionCode'] == 'VersionNegotiationFailed'

    def test_qywps_version(self):
        resp = self.client.get('?service=WPS&request=GetCapabilities')
        assert_qywps_version(resp)


def load_tests(loader=None, tests=None, pattern=None):
    if not loader:
        loader = unittest.TestLoader()
    suite_list = [
        loader.loadTestsFromTestCase(BadRequestTest),
        loader.loadTestsFromTestCase(CapabilitiesTest),
    ]
    return unittest.TestSuite(suite_list)
