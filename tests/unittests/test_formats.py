"""Unit tests for Formats
"""
##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

from pyqgiswps.inout.formats import Format, get_format, FORMATS
from lxml import etree
from pyqgiswps.app.basic import xpath_ns
from pyqgiswps.validator.base import emptyvalidator


def validate(inpt, level=None):
    """fake validate method
    """
    return True


def test_format_class():
    """Test pyqgiswps.formats.Format class
    """
    frmt = Format('mimetype', schema='halloworld', encoding='asdf', 
                  validate=validate)

    assert frmt.mime_type == 'mimetype'
    assert frmt.schema == 'halloworld'
    assert frmt.encoding == 'asdf'
    assert frmt.validate('the input', 1)

    describeel = frmt.describe_xml()
    assert 'Format' == describeel.tag
    mimetype = xpath_ns(describeel, '/Format/MimeType')
    encoding = xpath_ns(describeel, '/Format/Encoding')
    schema = xpath_ns(describeel, '/Format/Schema')

    assert mimetype
    assert encoding
    assert schema

    assert mimetype[0].text == 'mimetype'
    assert encoding[0].text == 'asdf'
    assert schema[0].text == 'halloworld'

    frmt2 = get_format('GML')

    assert not frmt.same_as(frmt2)


def test_getformat():
    """test for pypws.inout.formats.get_format function
    """
    frmt = get_format('GML', validate)
    assert frmt.mime_type, FORMATS.GML.mime_type
    assert frmt.validate('ahoj', 1)

    frmt2 = get_format('GML')
    assert frmt.same_as(frmt2)


def test_json_out():
    """Test json export
    """
    frmt = get_format('GML')
    outjson = frmt.json
    assert outjson['schema'] == ''
    assert outjson['extension'] == '.gml'
    assert outjson['mime_type'] == 'application/gml+xml'
    assert outjson['encoding'] == ''



