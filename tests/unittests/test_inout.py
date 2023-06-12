"""Unit tests for IOs
"""
##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import os
import tempfile
import pytest

from io import StringIO
from pyqgiswps.inout.formats import Format
from pyqgiswps.validator import get_validator
from pyqgiswps.ogc.ows import NAMESPACES
from pyqgiswps.inout.basic import IOHandler, SOURCE_TYPE, SimpleHandler, BBoxInput, BBoxOutput, \
    ComplexInput, ComplexOutput, LiteralInput, LiteralOutput
from pyqgiswps.inout import BoundingBoxInput as BoundingBoxInputXML
from pyqgiswps.inout.literaltypes import convert, AllowedValues
from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.exceptions import InvalidParameterValue
from pyqgiswps.validator.mode import MODE

from lxml import etree


def get_data_format(mime_type):
    return Format(mime_type=mime_type,
    validate=get_validator(mime_type))


class TestIOHandler:
    """IOHandler test cases"""

    def setup_method(self, me):
        self.iohandler = IOHandler()
        self._value = 'lalala'

    def test_validator(self):
        """Test available validation function
        """
        assert self.iohandler.validator == emptyvalidator

    def _test_outout(self, source_type):
        """Test all outputs"""

        assert source_type == self.iohandler.source_type
        assert self._value == self.iohandler.data

        if self.iohandler.source_type == SOURCE_TYPE.STREAM:
            source = StringIO(str(self._value))
            self.iohandler.stream = source

        if self.iohandler.source_type == SOURCE_TYPE.FILE:
            assert self.iohandler.file is not None
            file_handler = open(self.iohandler.file)
            assert self._value == file_handler.read()
            file_handler.close()

        if self.iohandler.source_type == SOURCE_TYPE.STREAM:
            source = StringIO(str(self._value))
            self.iohandler.stream = source

        stream_val = self.iohandler.stream.read()
        self.iohandler.stream.close()

        if type(stream_val) == bytes:
            assert str.encode(self._value) == stream_val
        else:
            assert self._value == stream_val

        if self.iohandler.source_type == SOURCE_TYPE.STREAM:
            source = StringIO(str(self._value))
            self.iohandler.stream = source

    def test_data(self):
        """Test data input IOHandler"""
        self.iohandler.data = self._value
        self._test_outout(SOURCE_TYPE.DATA)

    def test_stream(self):
        """Test stream input IOHandler"""
        source = StringIO(str(self._value))
        self.iohandler.stream = source
        self._test_outout(SOURCE_TYPE.STREAM)

    def test_file(self):
        """Test file input IOHandler"""
        (fd, tmp_file) = tempfile.mkstemp()
        source = tmp_file
        file_handler = open(tmp_file, 'w')
        file_handler.write(self._value)
        file_handler.close()
        self.iohandler.file = source
        self._test_outout(SOURCE_TYPE.FILE)


class TestComplexInput:
    """ComplexInput test cases"""

    def setup_method(self, me):
        self.tmp_dir = tempfile.mkdtemp()
        data_format = get_data_format('application/json')
        self.complex_in = ComplexInput(identifier="complexinput",
                                       title='MyComplex',
                                       abstract='My complex input',
                                       supported_formats=[data_format])

        self.complex_in.data = "Hallo world!"

    def test_validator(self):
        assert self.complex_in.data_format.validate == get_validator('application/json')
        assert self.complex_in.validator == get_validator('application/json')
        frmt = get_data_format('application/json')
        def my_validate():
            return True
        frmt.validate = my_validate
        assert not self.complex_in.validator == frmt.validate

    def test_contruct(self):
        assert isinstance(self.complex_in, ComplexInput)

    def test_data_format(self):
        assert isinstance(self.complex_in.supported_formats[0], Format)

    def test_json_out(self):
        out = self.complex_in.json

        assert out['file'] is None
        assert out['supported_formats'], 'There are some formats'
        assert len(out['supported_formats']) == 1, 'There is one formats'
        assert out['title'] == 'MyComplex', 'Title not set but existing'
        assert out['abstract'] == 'My complex input', 'Abstract not set but existing'
        assert out['identifier'] == 'complexinput', 'identifier set'
        assert out['type'] == 'complex', 'it is complex input'
        assert out['data_format'], 'data_format set'
        assert out['data_format']['mime_type'] == 'application/json', 'data_format set'


class TestComplexOutput:
    """ComplexOutput test cases"""

    def setup_method(self, me):
        tmp_dir = tempfile.mkdtemp()
        data_format = get_data_format('application/json')
        self.complex_out = ComplexOutput(identifier="complexinput",
                                         data_format=data_format,
                                         supported_formats=[data_format])

    def test_contruct(self):
        assert isinstance(self.complex_out, ComplexOutput)

    def test_data_format(self):
        assert isinstance(self.complex_out.data_format, Format)

    def test_storage(self):
        class Storage:
            pass
        storage = Storage()
        self.complex_out.store = storage
        assert self.complex_out.store == storage

    def test_validator(self):
        assert self.complex_out.validator == get_validator('application/json')



class TestSimpleHandler:
    """SimpleHandler test cases"""

    def setup_method(self, me):
        data_type = 'integer'
        self.simple_handler = SimpleHandler(data_type=data_type)

    def test_contruct(self):
        assert isinstance(self.simple_handler, SimpleHandler)

    def test_data_type(self):
        assert convert(self.simple_handler.data_type, '1') == 1


class TestLiteralInput:
    """LiteralInput test cases"""

    def setup_method(self, me):
        self.literal_input = LiteralInput(
            identifier="literalinput",
            mode=2,
            allowed_values=AllowedValues(values=(1, 2))
        )

    def test_contruct(self):
        assert isinstance(self.literal_input, LiteralInput)
        assert isinstance(self.literal_input.allowed_values, AllowedValues)
        assert self.literal_input.allowed_values.values == (1, 2)

    def test_valid(self):
        self.literal_input.data = 1
        assert self.literal_input.data == 1
        
        with pytest.raises(InvalidParameterValue):
            self.literal_input.data = 5

        with pytest.raises(InvalidParameterValue):
            self.literal_input.data = "a"

        with pytest.raises(InvalidParameterValue):
            self.literal_input.data = 15

    def test_json_out(self):
        self.literal_input.data = 2
        out = self.literal_input.json

        assert not out['uoms'], 'UOMs exist'
        assert out['data_type'] == 'integer', 'Data type is integer'
        assert not out['abstract'], 'abstract exist'
        assert not out['title'], 'title exist'
        assert out['data'] == 2, 'data set'
        assert out['mode'] == MODE.STRICT, 'Mode set'
        assert out['identifier'] == 'literalinput', 'identifier set'
        assert out['type'] == 'literal', 'it\'s literal input'
        assert not out['uom'], 'uom exists'
        assert out['allowed_values']['values'] == [1,2], 'allowed values [1, 2]'


class TestLiteralOutput:
    """LiteralOutput test cases"""

    def setup_method(self, me):
        self.literal_output = LiteralOutput("literaloutput", data_type="integer")

    def test_contruct(self):
        assert isinstance(self.literal_output, LiteralOutput)

    def test_storage(self):
        class Storage:
            pass
        storage = Storage()
        self.literal_output.store = storage
        assert self.literal_output.store == storage


class TestBoxInput:
    """BBoxInput test cases"""

    def setup_method(self, me):
        self.bbox_input = BBoxInput("bboxinput", dimensions=2)
        self.bbox_input.data = [0, 1, 2, 4]

    def test_contruct(self):
        assert isinstance(self.bbox_input, BBoxInput)

    def test_json_out(self):
        out = self.bbox_input.json

        assert out['identifier'], 'identifier exists'
        assert not out['title'], 'title exists'
        assert not out['abstract'], 'abstract set'
        assert out['type'] == 'bbox', 'type set'
        assert out['bbox'] == [0., 1., 2., 4.], 'data are there'
        assert out['dimensions'] == 2, 'Dimensions set'


class TestBoxOutput:
    """BoundingBoxOutput test cases"""

    def setup_method(self, me):
        self.bbox_out = BBoxOutput("bboxoutput")

    def test_contruct(self):
        assert isinstance(self.bbox_out, BBoxOutput)

    def test_storage(self):
        class Storage:
            pass
        storage = Storage()
        self.bbox_out.store = storage
        assert self.bbox_out.store == storage

