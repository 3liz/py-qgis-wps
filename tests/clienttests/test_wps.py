""" Test WPS service
"""
import sys
import os
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from time import sleep
from client_utils import * 


def test_get_capabilities( host, data ):
    """ Test Get capabilities"""
    rv = requests.get(host + "/ows/?SERVICE=WPS&Request=GetCapabilities")
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'text/xml;charset=utf-8'


def test_describeprocess( host, data ):
    """ Test describe process"""
    rv = requests.get(host + "/ows/?SERVICE=WPS&Request=DescribeProcess&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0")

    assert rv.status_code == 200


def test_executeprocess( host, data ):
    """  Test execute process """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2"))
    assert rv.status_code == 200


def test_executeprocess_async( host, data ):
    """  Test execute async process GET """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2"
                               "&storeExecuteResponse=true"))
    assert rv.status_code == 200

    # Get the response and test that we can get the result status
    assert rv.headers.get('Content-Type') == 'text/xml;charset=utf-8'
    resp = Response(rv)
    assert_response_accepted(resp)

    # Get the status url
    status_url = resp.xpath_attr('/wps:ExecuteResponse','statusLocation')
    resp = Response(requests.get(status_url))
    assert resp.status_code == 200 
    assert resp.xpath('/wps:ExecuteResponse')  is not None
    


POST_DATA="""
<wps:Execute xmlns:wps="http://www.opengis.net/wps/1.0.0" version="1.0.0" service="WPS" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">pyqgiswps_test:testcopylayer</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">INPUT</ows:Identifier>
      <ows:Title xmlns:ows="http://www.opengis.net/ows/1.1">Vector Layer</ows:Title>
      <wps:Data>
        <wps:LiteralData>france_parts</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">OUTPUT</ows:Identifier>
      <ows:Title xmlns:ows="http://www.opengis.net/ows/1.1">Output Layer</ows:Title>
      <wps:Data>
        <wps:LiteralData>copy</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
  <wps:ResponseForm>
    <wps:ResponseDocument storeExecuteResponse="{storeExecuteResponse}">
      <wps:Output asReference="true">
        <ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">OUTPUT</ows:Identifier>
        <ows:Title xmlns:ows="http://www.opengis.net/ows/1.1"/>
        <ows:Abstract xmlns:ows="http://www.opengis.net/ows/1.1"/>
      </wps:Output>
    </wps:ResponseDocument>
  </wps:ResponseForm>
</wps:Execute>
"""


def _execute_process( host, storeExecuteResponse="false" ):
    """ Execute a process and return its status json
    """
    # Execute a process
    rv = requests.post(host+"/ows/?SERVICE=WPS&MAP=france_parts",
            data=POST_DATA.format(storeExecuteResponse=storeExecuteResponse),
            headers={ "Content-Type": "text/xml" })

    resp = Response(rv)
    assert resp.status_code == 200 

    # Get the status url
    status_url = resp.xpath_attr('/wps:ExecuteResponse','statusLocation')
    # Get the uuid
    q = parse_qs(urlparse(status_url).query)
    assert 'uuid' in q 

    return q['uuid'][0]


def test_executeprocess_post( host, data):
    """ Test execute async process POST """
    rv = requests.post(host+"/ows/?SERVICE=WPS&MAP=france_parts",
            data=POST_DATA.format(storeExecuteResponse="false"),
            headers={ "Content-Type": "text/xml" })

    # dump the response
    #fp = data.open("test_executeprocess_post.xml",mode='w')
    #fp.write(rv.text)
    #fp.close()
    assert rv.status_code == 200


def test_executeprocess_post_async( host, data):
    """ Test execute async process POST """
    rv = requests.post(host+"/ows/?SERVICE=WPS&MAP=france_parts",
            data=POST_DATA.format(storeExecuteResponse="true"),
            headers={ "Content-Type": "text/xml" })

    # dump the response
    #fp = data.open("test_executeprocess_post_async.xml",mode='w')
    #fp.write(rv.text)
    #fp.close()
    assert rv.status_code == 200


def test_executetimeout( host, data ):
    """  Test execute timeout """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testlongprocess&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=PARAM1=1&TIMEOUT=3"))
    assert rv.status_code == 424
    

def test_executedelete( host, data ):
    """ Test delete process
    """
    # Execute a process
    uuid = _execute_process( host )

    # Get the status and make sure is 200
    rv = requests.get(host+"/status/{}?SERVICE=WPS".format(uuid))
    assert rv.status_code == 200
    assert rv.json()['status'].get('uuid') == uuid

    # Delete the response
    rv = requests.delete(host+"/status/{}?SERVICE=WPS".format(uuid))
    assert rv.status_code == 200 

    # Get the status and make sure is 404
    rv = requests.get(host+"/status/{}?SERVICE=WPS".format(uuid))
    assert rv.status_code == 404 


def test_proxy_status_url( host ):
    """ Test that status url has correct host
    """
    # Execute a process
    uuid = _execute_process( host )

    proxy_loc = 'http://test.proxy.loc:8080/'

    # Get the status and make sure is 200
    rv = requests.get(host+"/status/{}?SERVICE=WPS".format(uuid),  
            headers={ 'X-Forwarded-Url': proxy_loc })
    assert rv.status_code == 200

    st = rv.json()['status']

    # Parse the host url 
    status_url = urlparse(st['status_url'])
    assert "{0.scheme}://{0.netloc}/".format(status_url) == proxy_loc


def test_handleprocesserror( host, data ):
    """  Test execute error """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testraiseerror&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=PARAM1=1&TIMEOUT=3"))
    assert rv.status_code == 424


def test_handleprocesserror_async( host, data ):
    """  Test execute error """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testraiseerror&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=PARAM1=1&TIMEOUT=3"
                               "&StoreExecuteResponse=true"))
    resp = Response(rv)
    assert resp.status_code == 200 

    # Get the status url
    status_url = resp.xpath_attr('/wps:ExecuteResponse','statusLocation')
    # Get the uuid
    q = parse_qs(urlparse(status_url).query)
    assert 'uuid' in q 
    uuid = q['uuid'][0]

    sleep(3)
 
    # Get the status and make sure is 200
    rv = requests.get(host+"/status/{}".format(uuid))
    assert rv.status_code == 200
  
    data = rv.json()
    assert data['status']['status'] == 'ERROR_STATUS'
    
 


def test_mapcontext_describe( host, data ):
    """ Test describe process with context"""
    rv = requests.get(host + "/ows/?SERVICE=WPS&Request=DescribeProcess&Identifier=pyqgiswps_test:testmapcontext&Version=1.0.0&MAP=france_parts")

    assert rv.status_code == 200

    # Get the response and test that we can get the result status
    assert rv.headers.get('Content-Type') == 'text/xml;charset=utf-8'
    resp = Response(rv)
   
    # Check the contextualized default value
    assert resp.xpath_text('//DataInputs/Input/LiteralData/DefaultValue') == 'france_parts'
 

def test_mapcontext_execute( host, data ):
    """ Test execute process with context"""

    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testmapcontext&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=INPUT=hello_context"))
    assert rv.status_code == 200

    # Get result 
    resp = Response(rv)    
    assert resp.xpath_text('//wps:ProcessOutputs/wps:Output/wps:Data/wps:LiteralData') == 'france_parts'


def test_unknownprocess( host ):
    """ Test unknown process error """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testidonotexists&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=INPUT=wtf"))

    assert rv.status_code == 400
    resp = Response(rv)


def test_enum_parameters( host ):
    """ Test parameter enums
    """
    rv = requests.get(host+("/ows/?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testmultioptionvalue&Version=1.0.0"
                               "&MAP=france_parts&DATAINPUTS=INPUT=value2"))
    assert rv.status_code == 200

    # Get result 
    resp = Response(rv)    
    assert resp.xpath_text('//wps:ProcessOutputs/wps:Output/wps:Data/wps:LiteralData') == 'selection is 1'



#def test_slowprogress( host, data ):
#    """  Test execute timeout """
#    rv = requests.get(host+("?SERVICE=WPS&Request=Execute&Identifier=pyqgiswps_test:testlongprocess&Version=1.0.0"
#                               "&MAP=france_parts&DATAINPUTS=PARAM1=2"))
#    assert rv.status_code == 200
 

