##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

"""Unit tests for complex validator
"""

import sys
from pyqgiswps.validator.complexvalidator import *
from pyqgiswps.inout.formats import FORMATS
import tempfile
import os
import pytest

try:
    import osgeo
except ImportError:
    WITH_GDAL = False
else:
    WITH_GDAL = True

def get_input(name, schema, mime_type):

    class FakeFormat(object):
        mimetype = 'text/plain'
        schema = None
        units = None
        def validate(self, data):
            return True

    class FakeInput(object):
        tempdir = tempfile.mkdtemp()
        file = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..', 'data', name)
        format = FakeFormat()

    class data_format(object):
        file = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..', 'data', str(schema))

    fake_input = FakeInput()
    fake_input.stream = open(fake_input.file)
    fake_input.data_format = data_format()
    if schema:
        fake_input.data_format.schema = 'file://' + fake_input.data_format.file
    fake_input.data_format.mime_type = mime_type

    return fake_input

def test_gml_validator():
    """Test GML validator
    """
    gml_input = get_input('gml/point.gml', 'point.xsd', FORMATS.GML.mime_type)
    assert validategml(gml_input, MODE.NONE), 'NONE validation'
    assert validategml(gml_input, MODE.SIMPLE), 'SIMPLE validation'
    if WITH_GDAL:
        assert validategml(gml_input, MODE.STRICT), 'STRICT validation'
        # XXX Depends on external connection, may fail if not online
        # Prevent test to fail if site is down
        #assert validategml(gml_input, MODE.VERYSTRICT), 'VERYSTRICT validation'
    gml_input.stream.close()


def test_geojson_validator():
    """Test GeoJSON validator
    """
    geojson_input = get_input('json/point.geojson', 'json/schema/geojson.json',
                              FORMATS.GEOJSON.mime_type)
    assert validategeojson(geojson_input, MODE.NONE), 'NONE validation'
    assert validategeojson(geojson_input, MODE.SIMPLE), 'SIMPLE validation'
    if WITH_GDAL:
        assert validategeojson(geojson_input, MODE.STRICT), 'STRICT validation'
        assert validategeojson(geojson_input, MODE.VERYSTRICT), 'VERYSTRICT validation'
    geojson_input.stream.close()


def test_shapefile_validator():
    """Test ESRI Shapefile validator
    """
    shapefile_input = get_input('shp/point.shp.zip', None,
            FORMATS.SHP.mime_type)
    assert validateshapefile(shapefile_input, MODE.NONE), 'NONE validation'
    assert validateshapefile(shapefile_input, MODE.SIMPLE), 'SIMPLE validation'
    if WITH_GDAL:
        assert validateshapefile(shapefile_input, MODE.STRICT), 'STRICT validation'
    shapefile_input.stream.close()


def test_geotiff_validator():
    """Test GeoTIFF validator
    """
    geotiff_input = get_input('geotiff/dem.tiff', None,
                              FORMATS.GEOTIFF.mime_type)
    assert validategeotiff(geotiff_input, MODE.NONE), 'NONE validation'
    assert validategeotiff(geotiff_input, MODE.SIMPLE), 'SIMPLE validation'
    if WITH_GDAL:
        assert validategeotiff(geotiff_input, MODE.STRICT), 'STRICT validation'
    geotiff_input.stream.close()


def test_fail_validator():
    fake_input = get_input('point.xsd', 'point.xsd', FORMATS.SHP.mime_type)
    assert not validategml(fake_input, MODE.SIMPLE), 'SIMPLE validation invalid'
    fake_input.stream.close()

