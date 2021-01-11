"""
    Test Processing executor
"""
import pytest
import json
from urllib.parse import urlparse, parse_qs

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
        sleep(4)
        response_element = rv.xpath('/wps:ExecuteResponse')
        assert len(response_element) > 0

        status_url = response_element[0].attrib['statusLocation']
        rv = self.client.get(status_url, path='')

        assert rv.status_code == 200
        assert len(rv.xpath('/wps:ExecuteResponse')) > 0
        assert len(rv.xpath('//wps:ProcessFailed')) > 0


    def test_mapcontext_describe(self):
        """ Test describe process with context
        """
        rv = self.client.get(("/ows/?SERVICE=WPS&Request=DescribeProcess"
                              "&Identifier=pyqgiswps_test:testmapcontext"
                              "&Version=1.0.0&MAP=france_parts"), path='')

        assert rv.status_code == 200

        # Get the response and test that we can get the result status
        assert rv.headers.get('Content-Type') == 'text/xml;charset=utf-8'

        # Check the contextualized default value
        assert rv.xpath_text('//DataInputs/Input/LiteralData/DefaultValue') == 'france_parts'


    def test_mapcontext_execute(self):
        """ Test execute process with context
        """
        rv = self.client.get(("/ows/?SERVICE=WPS&Request=Execute"
                              "&Identifier=pyqgiswps_test:testmapcontext&Version=1.0.0"
                              "&MAP=france_parts&DATAINPUTS=INPUT=hello_context"), path="")
        assert rv.status_code == 200
        assert rv.xpath_text('//wps:ProcessOutputs/wps:Output/wps:Data/wps:LiteralData') == 'france_parts'


    def test_proxy_url( self ):
        """ Test if proxy url is set 
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2')
        proxy_loc = 'http://test.proxy.loc:8080/'
       
        headers = { 'X-Forwarded-Url': proxy_loc }

        rv = self.client.get(uri, path='', headers=headers)
        assert rv.status_code == 200

        # Get the status url
        status_url = rv.xpath('/wps:ExecuteResponse')[0].attrib['statusLocation']

        q = parse_qs(urlparse(status_url).query)
        assert 'uuid' in q

        uuid = q['uuid'][0]
 
        # Get the status
        rv = self.client.get(f"/status/{uuid}?SERVICE=WPS", path='', headers=headers)
        assert rv.status_code == 200

        assert rv.headers.get('Content-Type','').find('application/json') == 0
        st = json.loads(rv.get_data())['status']
    
        # Parse the host url 
        status_url = urlparse(st['status_url'])
        assert f"{status_url.scheme}://{status_url.netloc}/" == proxy_loc

