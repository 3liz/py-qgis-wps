""" Geometry io

    Test parsing processing inputs to WPS inputs
"""
import os

from pyqgiswps import WPS, OWS
from pyqgiswps.owsutils.ows import BoundingBox
from pyqgiswps.inout import (LiteralInput, 
                             ComplexInput,
                             BoundingBoxInput, 
                             LiteralOutput, 
                             ComplexOutput,
                             BoundingBoxOutput)

from pyqgiswps.inout.formats import FORMATS, Format

from pyqgiswps.executors.processingio import(
            parse_input_definition,
            parse_output_definition,
        ) 

from pyqgiswps.executors.io import geometryio

from pyqgiswps.exceptions import (NoApplicableCode,
                              InvalidParameterValue,
                              MissingParameterValue,
                              ProcessException)


from qgis.core import QgsApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterPoint,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterGeometry,
                       QgsReferencedRectangle,
                       QgsRectangle,
                       QgsReferencedPointXY,
                       QgsReferencedGeometry,
                       QgsGeometry,
                       QgsCoordinateReferenceSystem,
                       QgsWkbTypes)

from processing.core.Processing import Processing


def test_bbox_input():
    """ Test extent parameter
    """ 
    param = QgsProcessingParameterExtent("BBOX")
    
    inp = parse_input_definition(param)

    assert isinstance(inp,BoundingBoxInput)

    # see create_bbox_inputs at L532 app/Service.py
    inp.data = ['15', '50', '16', '51']
    value = geometryio.input_to_extent( inp ) 

    assert isinstance(value,QgsReferencedRectangle)


def test_point_input_gml():
    """ Test input point from gml
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.GML)
    inp.data = ('<gml:Point srsName="EPSG:4326">'
                '<gml:coordinates>4,42</gml:coordinates>'
                '</gml:Point>')

    assert inp.data_format.mime_type == FORMATS.GML.mime_type

    value = geometryio.input_to_point( inp )
    assert isinstance( value, QgsReferencedPointXY )


def test_point_input_json():
    """ Test input point from json
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp.data = '{"coordinates":[4.0,42.0],"type":"Point"}'

    assert inp.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value = geometryio.input_to_point( inp )
    assert isinstance( value, QgsGeometry )


def test_point_input_wkt():
    """ Test input point from wkt
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'CRS=EPSG:4326;POINT(6 10)'

    assert inp.data_format.mime_type == FORMATS.WKT.mime_type

    value = geometryio.input_to_point( inp )
    assert isinstance( value, QgsReferencedPointXY )


def test_linestring_input_gml():
    """ Test input point from gml
    """
    param = QgsProcessingParameterGeometry("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.GML)
    inp.data = ('<gml:LineString srsName="EPSG:4326">'
                '<gml:coordinates>45.67,88.56 55.56,89.44</gml:coordinates>'
                '</gml:LineString>')

    assert inp.data_format.mime_type == FORMATS.GML.mime_type

    value = geometryio.input_to_geometry( inp )
    assert isinstance( value, QgsReferencedGeometry )
    assert value.wkbType() == QgsWkbTypes.LineString


def test_multipoint_input_json():
    """ Test input point from json
    """
    param = QgsProcessingParameterPoint("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp.data = '{"coordinates":[[10, 40], [40, 30], [20, 20], [30, 10]],"type":"MultiPoint"}'

    assert inp.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value = geometryio.input_to_geometry( inp )
    assert isinstance( value, QgsGeometry )
    assert value.wkbType() == QgsWkbTypes.MultiPoint


def test_multipoint_input_wkt():
    """ Test input point from gml
    """
    param = QgsProcessingParameterPoint("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'CRS=EPSG:4326;MULTIPOINT((3.5 5.6), (4.8 10.5))'

    assert inp.data_format.mime_type == FORMATS.WKT.mime_type

    value = geometryio.input_to_geometry( inp )
    assert isinstance( value, QgsReferencedGeometry )
    assert value.wkbType() == QgsWkbTypes.MultiPoint


def test_geometry_crs_json():
    """ Test passing crs from json
    """
    param = QgsProcessingParameterGeometry("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp.data = ('{ "geometry": {"coordinates":[445277.96, 5160979.44],"type":"Point"},'
                '  "crs": { '
                '    "type": "name", '
                '    "properties": { "name": "EPSG:3785" }'
                '}}')

    assert inp.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value = geometryio.input_to_geometry( inp )
    assert isinstance( value, QgsReferencedGeometry )
    assert value.crs().authid() == "EPSG:3785"
    assert value.wkbType() == QgsWkbTypes.Point

def test_nocrs_input_wkt():
    """ Test input point from wkt
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'POINT(6 10)'

    assert inp.data_format.mime_type == FORMATS.WKT.mime_type

    value = geometryio.input_to_point( inp )
    assert isinstance( value, QgsGeometry )
    assert value.wkbType() == QgsWkbTypes.Point

