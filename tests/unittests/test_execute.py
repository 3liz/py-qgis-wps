##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import lxml.etree
import json
from pyqgiswps.app import WPSProcess
from pyqgiswps.inout import (Format,
                             BoundingBoxOutput, 
                             BoundingBoxInput, 
                             ComplexInput, 
                             ComplexOutput, 
                             LiteralOutput,
                             LiteralInput)
from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.validator.complexvalidator import validategml
from pyqgiswps.exceptions import InvalidParameterValue

from pyqgiswps.ogc.ows.schema import E, OWS, WPS, xpath_ns
from pyqgiswps.ogc.ows.request import get_inputs_from_xml, get_output_from_xml

from pyqgiswps.tests import HTTPTestCase, assert_response_success

from io import StringIO


def ultimate_question(request, response):
    response.outputs['outvalue'].data = '42'
    return response


def create_ultimate_question():
    return WPSProcess(handler=ultimate_question,
                   identifier='ultimate_question',
                   title='Ultimate Question',
                   outputs=[LiteralOutput('outvalue', 'Output Value', data_type='string')])


def greeter(request, response):
    name = request.inputs['name'][0].data
    assert type(name) is str
    response.outputs['message'].data = "Hello %s!" % name
    return response

def create_greeter():
    return WPSProcess(handler=greeter,
                   identifier='greeter',
                   title='Greeter',
                   inputs=[LiteralInput('name', 'Input name', data_type='string')],
                   outputs=[LiteralOutput('message', 'Output message', data_type='string')])

def bbox_process(request, response):
    coords = request.inputs['mybbox'][0].data
    assert type(coords) == type([])
    assert len(coords) == 4
    assert coords[0] == float(15)
    response.outputs['outbbox'].data = coords
    return response


def create_bbox_process():
    return WPSProcess(handler=bbox_process,
                   identifier='my_bbox_process',
                   title='Bbox process',
                   inputs=[BoundingBoxInput('mybbox', 'Input name', ["EPSG:4326"])],
                   outputs=[BoundingBoxOutput('outbbox', 'Output message', ["EPSG:4326"])])

def complex_process(request, response):
    response.outputs['complex'].data = request.inputs['complex'][0].data
    return response

def create_complex_process():
    frmt = Format(mime_type='application/gml') # this is unknown mimetype

    return WPSProcess(handler=complex_process,
            identifier='my_complex_process',
            title='Complex process',
            inputs=[
                ComplexInput(
                    'complex',
                    'Complex input',
                    supported_formats=[frmt])
            ],
            outputs=[
                ComplexOutput(
                    'complex',
                    'Complex output',
                    supported_formats=[frmt])
             ])


def get_output(doc):
    output = {}
    for output_el in xpath_ns(doc, '/wps:ExecuteResponse'
                                   '/wps:ProcessOutputs/wps:Output'):
        [identifier_el] = xpath_ns(output_el, './ows:Identifier')
        [value_el] = xpath_ns(output_el, './wps:Data/wps:LiteralData')
        output[identifier_el.text] = value_el.text
    return output


class ExecuteTest(HTTPTestCase):
    """Test for Exeucte request KVP request"""

    def get_processes(self):
        return [
            create_ultimate_question(),
            create_greeter(),
            create_bbox_process(),
        ]

    def test_missing_process_error(self):
        resp = self.client.get('?Request=Execute&identifier=foo')
        assert resp.status_code == 400

    def test_get_with_no_inputs(self):
        resp = self.client.get('?service=wps&version=1.0.0&Request=Execute&identifier=ultimate_question')
        assert_response_success(resp)
        assert get_output(resp.xml) == {'outvalue': '42'}

    def test_post_with_no_inputs(self):
        request_doc = WPS.Execute(
            OWS.Identifier('ultimate_question'),
            version='1.0.0'
        )
        resp = self.client.post_xml(doc=request_doc)
        assert_response_success(resp)
        assert get_output(resp.xml) == {'outvalue': '42'}

    def test_post_with_string_input(self):
        request_doc = WPS.Execute(
            OWS.Identifier('greeter'),
            WPS.DataInputs(
                WPS.Input(
                    OWS.Identifier('name'),
                    WPS.Data(WPS.LiteralData('foo'))
                )
            ),
            version='1.0.0'
        )
        resp = self.client.post_xml(doc=request_doc)
        assert_response_success(resp)
        assert get_output(resp.xml) == {'message': "Hello foo!"}

    def test_bbox_io(self):
        request_doc = WPS.Execute(
            OWS.Identifier('my_bbox_process'),
            WPS.DataInputs(
                WPS.Input(
                    OWS.Identifier('mybbox'),
                    WPS.Data(WPS.BoundingBoxData(
                        OWS.LowerCorner('15 50'),
                        OWS.UpperCorner('16 51'),
                        ))
                )
            ),
            version='1.0.0'
        )
        resp = self.client.post_xml(doc=request_doc)
        assert_response_success(resp)

        [output] = xpath_ns(resp.xml, '/wps:ExecuteResponse'
                                   '/wps:ProcessOutputs/Output')
        self.assertEqual('outbbox', xpath_ns(output,
            './ows:Identifier')[0].text)
        self.assertEqual('15.0 50.0', xpath_ns(output,
            './ows:BoundingBox/ows:LowerCorner')[0].text)

#
# Tests for Execute request XML Parser
#

def test_empty():
    request_doc = WPS.Execute(OWS.Identifier('foo'))
    assert get_inputs_from_xml(request_doc) == {}


def test_one_string():
    request_doc = WPS.Execute(
        OWS.Identifier('foo'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('name'),
                WPS.Data(WPS.LiteralData('foo'))),
            WPS.Input(
                OWS.Identifier('name'),
                WPS.Data(WPS.LiteralData('bar')))
            ))
    rv = get_inputs_from_xml(request_doc)
    assert 'name' in rv
    assert len(rv['name']) == 2
    assert rv['name'][0]['data'] == 'foo'
    assert rv['name'][1]['data'] == 'bar'


def test_two_strings():
    request_doc = WPS.Execute(
        OWS.Identifier('foo'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('name1'),
                WPS.Data(WPS.LiteralData('foo'))),
            WPS.Input(
                OWS.Identifier('name2'),
                WPS.Data(WPS.LiteralData('bar')))))
    rv = get_inputs_from_xml(request_doc)
    assert rv['name1'][0]['data'] == 'foo'
    assert rv['name2'][0]['data'] == 'bar'


def test_complex_input():
    the_data = E.TheData("hello world")
    request_doc = WPS.Execute(
        OWS.Identifier('foo'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('name'),
                WPS.Data(
                    WPS.ComplexData(the_data, mimeType='text/foobar')))))
    rv = get_inputs_from_xml(request_doc)
    assert rv['name'][0]['mimeType'] == 'text/foobar'
    rv_doc = lxml.etree.parse(StringIO(rv['name'][0]['data'])).getroot()
    assert rv_doc.tag == 'TheData'
    assert rv_doc.text == 'hello world'


def test_complex_input_raw_value():
    the_data = '{ "plot":{ "Version" : "0.1" } }'

    request_doc = WPS.Execute(
        OWS.Identifier('foo'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('json'),
                WPS.Data(
                    WPS.ComplexData(the_data, mimeType='application/json')))))
    rv = get_inputs_from_xml(request_doc)
    assert rv['json'][0]['mimeType'] == 'application/json'
    json_data = json.loads(rv['json'][0]['data'])
    assert json_data['plot']['Version'] == '0.1'


def test_complex_input_base64_value():
    the_data = 'eyAicGxvdCI6eyAiVmVyc2lvbiIgOiAiMC4xIiB9IH0='

    request_doc = WPS.Execute(
        OWS.Identifier('foo'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('json'),
                WPS.Data(
                    WPS.ComplexData(the_data,
                        encoding='base64',
                        mimeType='application/json')))))
    rv = get_inputs_from_xml(request_doc)
    assert rv['json'][0]['mimeType'] == 'application/json'
    json_data = json.loads(rv['json'][0]['data'].decode())
    assert json_data['plot']['Version'] == '0.1'


def test_bbox_input():
    request_doc = WPS.Execute(
        OWS.Identifier('request'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('bbox'),
                WPS.Data(
                    WPS.BoundingBoxData(
                        OWS.LowerCorner('40 50'),
                        OWS.UpperCorner('60 70'))))))
    rv = get_inputs_from_xml(request_doc)
    bbox = rv['bbox'][0]['data']
    assert isinstance(bbox, list)
    assert bbox[0] == '40'
    assert bbox[1] == '50'
    assert bbox[2] == '60'
    assert bbox[3] == '70'


def test_reference_post_input():
    request_doc = WPS.Execute(
        OWS.Identifier('foo'),
        WPS.DataInputs(
            WPS.Input(
                OWS.Identifier('name'),
                WPS.Reference(
                    WPS.Body('request body'),
                    {'{http://www.w3.org/1999/xlink}href': 'http://foo/bar/service'},
                    method='POST'
                )
            )
        )
    )
    rv = get_inputs_from_xml(request_doc)
    assert rv['name'][0]['href'] == 'http://foo/bar/service'
    assert rv['name'][0]['method'] == 'POST'
    assert rv['name'][0]['body'] == 'request body'
