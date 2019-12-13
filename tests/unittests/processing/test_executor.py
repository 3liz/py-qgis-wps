"""
    Test Processing executor
"""
import pytest

from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase, assert_response_accepted
from time import sleep

from test_common import async_test


class TestsExecutor(HTTPTestCase):

    def test_execute_request(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200

    def test_process_error(self):
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testraiseerror&Version=1.0.0'
                               '&DATAINPUTS=PARAM1=10')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 424

    @async_test
    def test_process_error_async(self):
        """  Test execute process error asynchronously 
        """
        uri = ("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testraiseerror&Version=1.0.0"
                "&MAP=france_parts&DATAINPUTS=PARAM1=1&TIMEOUT=3"
                "&storeExecuteResponse=true")

        rv = self.client.get(uri, path='')

        # Get the response and test that we can get the result status
        assert_response_accepted(rv)
    
        # Get the status url
        sleep(1)
        response_element = rv.xpath('/wps:ExecuteResponse')
        assert len(response_element) > 0

        status_url = response_element[0].attrib['statusLocation']
        rv = self.client.get(status_url, path='')

        assert rv.status_code == 200
        assert len(rv.xpath('/wps:ExecuteResponse')) > 0
        assert len(rv.xpath('//wps:ProcessFailed')) > 0


