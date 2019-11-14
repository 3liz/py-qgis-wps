"""
    Test Processing executor
"""
from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase
from pyqgiswps.executors.processingexecutor import ProcessingExecutor


class Tests(HTTPTestCase):

    def test_execute_request(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2')
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.get(uri, path='')
        assert rv.status_code == 200

