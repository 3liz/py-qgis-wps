##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

from collections import namedtuple
from pyqgiswps import WPSProcess, Service, LiteralInput, ComplexInput, BoundingBoxInput
from pyqgiswps import LiteralOutput, ComplexOutput, BoundingBoxOutput
from pyqgiswps import E, WPS, OWS, OGCTYPE, Format, NAMESPACES, OGCUNIT
from pyqgiswps.inout.literaltypes import LITERAL_DATA_TYPES
from pyqgiswps.app.basic import xpath_ns
from pyqgiswps.app.Common import Metadata
from pyqgiswps.inout.formats import Format
from pyqgiswps.inout.literaltypes import AllowedValue
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE

from pyqgiswps.tests import HTTPTestCase, assert_pyqgiswps_version

ProcessDescription = namedtuple('ProcessDescription', ['identifier', 'inputs', 'metadata'])


def get_data_type(el):
    if el.text in LITERAL_DATA_TYPES:
        return el.text
    raise RuntimeError("Can't parse data type")


def get_describe_result(self,resp):
    assert resp.status_code == 200, "200 != %s" %  resp.status_code
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    result = []
    for desc_el in resp.xpath('/wps:ProcessDescriptions/ProcessDescription'):
        [identifier_el] = xpath_ns(desc_el, './ows:Identifier')
        inputs = []
        metadata = []
        for metadata_el in xpath_ns(desc_el, './ows:Metadata'):
            metadata.append(metadata_el.attrib['{http://www.w3.org/1999/xlink}title'])
        for input_el in xpath_ns(desc_el, './DataInputs/Input'):
            [input_identifier_el] = xpath_ns(input_el, './ows:Identifier')
            input_identifier = input_identifier_el.text
            literal_data_el_list = xpath_ns(input_el, './LiteralData')
            complex_data_el_list = xpath_ns(input_el, './ComplexData')
            if literal_data_el_list:
                [literal_data_el] = literal_data_el_list
                [data_type_el] = xpath_ns(literal_data_el, './ows:DataType')
                data_type = get_data_type(data_type_el)
                inputs.append((input_identifier, 'literal', data_type))
            elif complex_data_el_list:
                [complex_data_el] = complex_data_el_list
                formats = []
                for format_el in xpath_ns(complex_data_el,
                                          './Supported/Format'):
                    [mimetype_el] = xpath_ns(format_el, './ows:MimeType')
                    formats.append({'mime_type': mimetype_el.text})
                inputs.append((input_identifier, 'complex', formats))
            else:
                raise RuntimeError("Can't parse input description")
        result.append(ProcessDescription(identifier_el.text, inputs, metadata))
    return result


class DescribeProcessTest(HTTPTestCase):

    def setUp(self):
        super().setUp()
        def hello(request): pass
        def ping(request): pass
        processes = [WPSProcess(hello, 'hello', 'Process Hello'), WPSProcess(ping, 'ping', 'Process Ping')]
        self.client = self.client_for(Service(processes=processes))

    def test_get_request_all_args(self):
        resp = self.client.get('?Request=DescribeProcess&service=wps&version=1.0.0&identifier=all')
        identifiers = [desc.identifier for desc in get_describe_result(self, resp)]
        assert 'ping' in identifiers
        assert 'hello' in identifiers
        assert_pyqgiswps_version(resp)

    def test_get_request_zero_args(self):
        resp = self.client.get('?Request=DescribeProcess&version=1.0.0&service=wps')
        assert resp.status_code == 400 # bad request, identifier is missing

    def test_get_request_nonexisting_process_args(self):
        resp = self.client.get('?Request=DescribeProcess&version=1.0.0&service=wps&identifier=NONEXISTINGPROCESS')
        assert resp.status_code == 400

    def test_post_request_zero_args(self):
        request_doc = WPS.DescribeProcess()
        resp = self.client.post_xml(doc=request_doc)
        assert resp.status_code == 400

    def test_get_one_arg(self):
        resp = self.client.get('?service=wps&version=1.0.0&Request=DescribeProcess&identifier=hello')
        assert [pr.identifier for pr in get_describe_result(self, resp)] == ['hello']

    def test_post_one_arg(self):
        request_doc = WPS.DescribeProcess(
            OWS.Identifier('hello'),
            version='1.0.0'
        )
        resp = self.client.post_xml(doc=request_doc)
        assert [pr.identifier for pr in get_describe_result(self, resp)] == ['hello']

    def test_get_two_args(self):
        resp = self.client.get('?Request=DescribeProcess'
                               '&service=wps'
                               '&version=1.0.0'
                               '&identifier=hello,ping')
        result = get_describe_result(self, resp)
        assert [pr.identifier for pr in result] == ['hello', 'ping']

    def test_post_two_args(self):
        request_doc = WPS.DescribeProcess(
            OWS.Identifier('hello'),
            OWS.Identifier('ping'),
            version='1.0.0'
        )
        resp = self.client.post_xml(doc=request_doc)
        result = get_describe_result(self, resp)
        assert [pr.identifier for pr in result] == ['hello', 'ping']


class DescribeProcessInputTest(HTTPTestCase):

    def describe_process(self, process):
        client = self.client_for(Service(processes=[process]))
        resp = client.get('?service=wps&version=1.0.0&Request=DescribeProcess&identifier=%s'
                          % process.identifier)
        [result] = get_describe_result(self, resp)
        return result

    def test_one_literal_string_input(self):
        def hello(request): pass
        hello_process = WPSProcess(
                hello,
                'hello',
                'Process Hello',
                inputs=[LiteralInput('the_name', 'Input name')],
                metadata=[Metadata('process metadata 1', 'http://example.org/1'), Metadata('process metadata 2', 'http://example.org/2')]
        )
        result = self.describe_process(hello_process)
        assert result.inputs == [('the_name', 'literal', 'integer')]
        assert result.metadata == ['process metadata 1', 'process metadata 2']

    def test_one_literal_integer_input(self):
        def hello(request): pass
        hello_process = WPSProcess(hello, 'hello',
                                'Process Hello',
                                inputs=[LiteralInput('the_number',
                                                     'Input number',
                                                     data_type='positiveInteger')])
        result = self.describe_process(hello_process)
        assert result.inputs == [('the_number', 'literal', 'positiveInteger')]


# ---------------------
# InputDescriptionTest
# ---------------------

def test_literal_integer_input():
    literal = LiteralInput('foo', 'Literal foo', data_type='positiveInteger', uoms=['metre'])
    doc = literal.describe_xml()
    assert doc.tag == E.Input().tag
    [identifier_el] = xpath_ns(doc, './ows:Identifier')
    assert identifier_el.text == 'foo'
    [type_el] = xpath_ns(doc, './LiteralData/ows:DataType')
    assert type_el.text == 'positiveInteger'
    assert type_el.attrib['{%s}reference' % NAMESPACES['ows']] == OGCTYPE['positiveInteger']
    anyvalue = xpath_ns(doc, './LiteralData/ows:AnyValue')
    assert len(anyvalue) == 1


def test_literal_allowed_values_input():
    """Test all around allowed_values
    """
    literal = LiteralInput(
        'foo',
        'Foo',
        data_type='integer',
        uoms=['metre'],
        allowed_values=(
            1, 2, (5, 10), (12, 4, 24),
            AllowedValue(
                allowed_type=ALLOWEDVALUETYPE.RANGE,
                minval=30,
                maxval=33,
                range_closure='closed-open')
        )
    )
    doc = literal.describe_xml()

    allowed_values = xpath_ns(doc, './LiteralData/ows:AllowedValues')
    assert len(allowed_values) == 1

    allowed_value = allowed_values[0]

    values = xpath_ns(allowed_value, './ows:Value')
    ranges = xpath_ns(allowed_value, './ows:Range')

    assert len(values) == 2
    assert len(ranges) == 3


def test_complex_input_identifier():
    complex_in = ComplexInput('foo', 'Complex foo', supported_formats=[Format('bar/baz')])
    doc = complex_in.describe_xml()
    assert doc.tag == E.Input().tag
    [identifier_el] = xpath_ns(doc, './ows:Identifier')
    assert identifier_el.text == 'foo'


def test_complex_input_default_and_supported():
    complex_in = ComplexInput(
        'foo',
        'Complex foo',
        supported_formats=[
            Format('a/b'),
            Format('c/d')
        ]
    )
    doc = complex_in.describe_xml()
    [default_format] = xpath_ns(doc, './ComplexData/Default/Format')
    [default_mime_el] = xpath_ns(default_format, './MimeType')
    assert default_mime_el.text == 'a/b'
    supported_mime_types = []
    for supported_el in xpath_ns(doc, './ComplexData/Supported/Format'):
        [mime_el] = xpath_ns(supported_el, './MimeType')
        supported_mime_types.append(mime_el.text)
    assert supported_mime_types == ['a/b', 'c/d']


def test_bbox_input():
    bbox = BoundingBoxInput('bbox', 'BBox foo',
                            crss=["EPSG:4326", "EPSG:3035"])
    doc = bbox.describe_xml()
    [inpt] = xpath_ns(doc, '/Input')
    [default_crs] = xpath_ns(doc, './BoundingBoxData/Default/CRS')
    supported = xpath_ns(doc, './BoundingBoxData/Supported/CRS')
    assert inpt.attrib['minOccurs'] == '1'
    assert default_crs.text == 'EPSG:4326'
    assert len(supported) == 2


def test_literal_output():
    literal = LiteralOutput('literal', 'Literal foo', uoms=['metre'])
    doc = literal.describe_xml()
    [output] = xpath_ns(doc, '/Output')
    [identifier] = xpath_ns(doc, '/Output/ows:Identifier')
    [data_type] = xpath_ns(doc, '/Output/LiteralOutput/ows:DataType')
    [uoms] = xpath_ns(doc, '/Output/LiteralOutput/UOMs')
    [default_uom] = xpath_ns(uoms, './Default/ows:UOM')
    supported_uoms = xpath_ns(uoms, './Supported/ows:UOM')
    assert output is not None
    assert identifier.text == 'literal'
    assert data_type.attrib['{%s}reference' % NAMESPACES['ows']] == OGCTYPE['string']
    assert uoms is not None
    assert default_uom.text == 'metre'
    assert default_uom.attrib['{%s}reference' % NAMESPACES['ows']] == OGCUNIT['metre']
    assert len(supported_uoms) == 1


def test_complex_output():
    complexo = ComplexOutput('complex', 'Complex foo', [Format('GML')])
    doc = complexo.describe_xml()
    [outpt] = xpath_ns(doc, '/Output')
    [default] = xpath_ns(doc, '/Output/ComplexOutput/Default/Format/MimeType')
    supported = xpath_ns(doc, '/Output/ComplexOutput/Supported/Format/MimeType')
    assert default.text == 'application/gml+xml'
    assert len(supported) == 1


def test_bbox_output():
    bbox = BoundingBoxOutput('bbox', 'BBox foo',
            crss=["EPSG:4326"])
    doc = bbox.describe_xml()
    [outpt] = xpath_ns(doc, '/Output')
    [default_crs] = xpath_ns(doc, './BoundingBoxOutput/Default/CRS')
    supported = xpath_ns(doc, './BoundingBoxOutput/Supported/CRS')
    assert default_crs.text == 'EPSG:4326'
    assert len(supported) == 1


