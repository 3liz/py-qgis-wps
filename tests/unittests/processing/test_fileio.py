"""
    Test Processing file io
"""
import pytest

from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase, assert_response_accepted
from time import sleep
from test_common import async_test


class TestsFileIO(HTTPTestCase):

    def test_output_file_reference(self):
        """ Test output file as reference
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testfiledestination&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=OUTPUT=my_file_output')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200


    def test_output_file_describeprocess(self):
        """ Test output file
        """
        uri = ('/ows/?service=WPS&request=DescribeProcess&Identifier=pyqgiswps_test:testoutputfile&Version=1.0.0')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200


    def test_output_file(self):
        """ Test output file
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testoutputfile&Version=1.0.0')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200

        output = rv.xpath('/wps:ExecuteResponse'
                          '/wps:ProcessOutputs'
                          '/wps:Output'
                          '/wps:Reference')

        assert len(output) == 1
        assert output[0].get('mimeType') == "application/json"


