##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################


from collections import namedtuple

from pyqgiswps.app import WPSProcess
from pyqgiswps.inout.inputs import LiteralInput, ComplexInput, BoundingBoxInput
from pyqgiswps.inout.outputs import LiteralOutput, ComplexOutput, BoundingBoxOutput
from pyqgiswps.inout.literaltypes import LITERAL_DATA_TYPES
from pyqgiswps.inout.formats import Format
from pyqgiswps.inout.literaltypes import AllowedValues

from pyqgiswps.app.common import Metadata
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE, RANGECLOSURETYPE
from pyqgiswps.validator.formats import FORMATS

from pyqgiswps.tests import HTTPTestCase, HttpClient

from pyqgiswps.ogc import OGCUNIT

def assert_success(resp):
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == "application/json;charset=utf-8"
    return resp.json


class ApiTestCase(HTTPTestCase):
    @property
    def client(self):
        """ Override """
        return HttpClient(self)


class ProcessTest(ApiTestCase):

    def get_processes(self):
        def hello(request): pass
        def ping(request): pass
        return [WPSProcess(hello, 'hello', 'Process Hello'), WPSProcess(ping, 'ping', 'Process Ping')]

    def test_get_process_list(self):
        resp = self.client.get('/processes')
        resp = assert_success(resp)
    
        processes = resp.get('processes')
        assert processes is not None
        assert len(processes) == 2

        identifiers = [p['id'] for p in processes]
        assert 'ping' in identifiers
        assert 'hello' in identifiers

    def test_get_nonexisting_process(self):
        resp = self.client.get('/processes/IdoNotExists')
        assert resp.status_code == 404

    def test_get_process(self):
        resp = self.client.get('/processes/ping')
        resp = assert_success(resp)
        assert resp['id'] == 'ping'


class ProcessInputTest(ApiTestCase):

    def get_processes(self):
        """ Define tests processes
        """
        def hello(request): pass
        hello_string = WPSProcess(
                hello,
                'hello_string',
                'Process Hello',
                inputs=[LiteralInput('the_name', 'Input name', data_type='string')],
                metadata=[Metadata('process metadata 1', 'http://example.org/1'), Metadata('process metadata 2', 'http://example.org/2')]
        )

        def hello(request): pass
        hello_integer = WPSProcess(hello, 'hello_integer',
                               'Process Hello',
                               inputs=[LiteralInput('the_number',
                                                    'Input number',
                                                    data_type='integer',
                                                    allowed_values=AllowedValues.positiveValue(),
                                                    )])
        return [hello_string, hello_integer]

    def get_process(self, identifier):
        resp = self.client.get(f"/processes/{identifier}")
        resp = assert_success(resp)
        return resp

    def test_one_literal_string_input(self):
        result = self.get_process('hello_string')
        inputs = result['inputs']
        assert isinstance(inputs, dict)
        assert 'the_name' in inputs

        inp = inputs['the_name']
        assert inp['title'] == 'Input name'
        assert inp['schema']['type'] == 'string'

    def test_one_literal_integer_input(self):
        result = self.get_process('hello_integer')
        inputs = result['inputs']
        assert isinstance(inputs, dict)
        assert 'the_number' in inputs

        inp = inputs['the_number']
        assert inp['title'] == 'Input number'
        assert inp['schema']['type'] == 'integer'


# ---------------------
# InputDescriptionTest
# ---------------------

def test_literal_integer_input_uom():
    literal = LiteralInput('foo', 'Literal foo', data_type='integer', uoms=['metre'])

    doc = literal.ogcapi_input_description()
    assert doc['schema']['type'] == 'integer'

    uom_schemas  = doc['schema']['uom']['oneOf']
    
    assert len(uom_schemas) == 1
    assert uom_schemas[0]['reference'] == OGCUNIT['metre']


def test_allowed_values_schema():
    """Test all around allowed_values
    """
    literal = LiteralInput(
        'foo',
        'Foo',
        data_type='integer',
        allowed_values=AllowedValues(
                allowed_type=ALLOWEDVALUETYPE.RANGE,
                minval=30,
                maxval=33,
                range_closure=RANGECLOSURETYPE.CLOSEDOPEN)
    )

    doc = literal.ogcapi_input_description()

    doc['schema']['minimum'] == 30
    doc['schema']['maximum'] == 33
    # XXX Draf4
    doc['schema']['exclusiveMaximum'] == True


def test_complex_input_default_format():
    complex_in = ComplexInput('foo', 'Complex foo', supported_formats=[Format('bar/baz')])
    doc = complex_in.ogcapi_input_description()
   
    schemas = doc['schema']
    assert schemas['type'] == 'string'
    assert schemas['contentMediaType'] == 'bar/baz'


def test_complex_input_multiple_supported_formats():
    complex_in = ComplexInput(
        'foo',
        'Complex foo',
        supported_formats=[
            Format('a/b'),
            Format('c/d')
        ]
    )

    doc = complex_in.ogcapi_input_description()

    schemas = doc['schema']['oneOf']
    assert len(schemas) == 2
    assert schemas[0]['type'] == 'string'
    assert schemas[0]['contentMediaType'] == 'a/b'
    assert schemas[1]['contentMediaType'] == 'c/d'
    

def test_bbox_input_crs():
    bbox = BoundingBoxInput('bbox', 'BBox foo',
                            crss=["EPSG:4326", "EPSG:3035"])
    doc = bbox.ogcapi_input_description()

    crs_schema = doc['schema']['properties']['crs']
    assert crs_schema['enum'] == ["EPSG:4326", "EPSG:3035"]


def test_literal_output():
    literal = LiteralOutput('literal', 'Literal foo', data_type="float", uoms=['metre'])
    doc = literal.ogcapi_output_description()
    assert doc['schema']['type'] == 'number'

    uom_schemas  = doc['schema']['uom']['oneOf']
    assert len(uom_schemas) == 1
    assert uom_schemas[0]['reference'] == OGCUNIT['metre']


def test_complex_output():
    cplx = ComplexOutput('complex', 'Complex foo', [Format('GML')])
    doc = cplx.ogcapi_output_description()

    schema = doc['schema']
    
    assert schema['type'] == 'string'
    assert schema['contentMediaType'] == FORMATS.GML.mime_type
    

def test_complex_output_multiple_formats():
    cplx = ComplexOutput('complex', 'Complex foo', [Format('GML'), Format('GEOJSON')])
    doc = cplx.ogcapi_output_description()

    schemas = doc['schema']['oneOf']
    assert len(schemas) == 2
    assert schemas[0]['contentMediaType'] == FORMATS.GML.mime_type
    assert schemas[1]['contentMediaType'] == FORMATS.GEOJSON.mime_type


def test_bbox_output():
    bbox = BoundingBoxOutput('bbox', 'BBox foo',
            crss=["EPSG:4326"])
    doc = bbox.ogcapi_output_description()
    crs_schema = doc['schema']['properties']['crs']
    assert crs_schema['enum'] == ["EPSG:4326"]
