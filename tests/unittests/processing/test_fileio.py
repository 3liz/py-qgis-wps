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
        """ Test output file as refecerence
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testfiledestination&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=OUTPUT=my_file_output')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200

