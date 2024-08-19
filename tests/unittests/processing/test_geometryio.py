""" Geometry io

    Test parsing processing inputs to WPS inputs
"""
import json
import os

from os import PathLike

from qgis.core import (
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterExtent,
    QgsProcessingParameterGeometry,
    QgsProcessingParameterPoint,
    QgsProject,
    QgsRectangle,
    QgsReferencedGeometry,
    QgsReferencedPointXY,
    QgsReferencedRectangle,
    QgsWkbTypes,
)

from pyqgiswps.executors.io import geometryio
from pyqgiswps.executors.processingcontext import ProcessingContext
from pyqgiswps.executors.processingio import (
    input_to_processing,
    parse_input_definition,
    parse_output_definition,
)
from pyqgiswps.executors.processingprocess import _find_algorithm, run_algorithm
from pyqgiswps.inout import (
    BoundingBoxInput,
    ComplexInput,
)
from pyqgiswps.inout.formats import FORMATS, Format
from pyqgiswps.ogc.ows import OWS, WPS
from pyqgiswps.ogc.ows.schema import BoundingBox, xpath_ns
from pyqgiswps.utils.contexts import chdir


class Context(QgsProcessingContext):

    def __init__(self, project: QgsProject, workdir: PathLike):
        super().__init__()
        self.workdir = str(workdir)
        self.setProject(project)

        # Create the destination project
        self.destination_project = QgsProject()

    def write_result(self, workdir, name):
        """ Save results to disk
        """
        return self.destination_project.write(os.path.join(workdir, name + '.qgs'))


def get_metadata(inp, name, minOccurence=1, maxOccurence=None):
    if maxOccurence is None:
        maxOccurence = minOccurence
    assert minOccurence <= maxOccurence
    m = list(filter(lambda m: m.title == name, inp.metadata))
    assert len(m) >= minOccurence
    assert len(m) <= maxOccurence
    return m


def test_bbox_4326():
    """ Test bounding box xml
    """
    # XXX With EPSG:4326 axes *MUST* be inverted
    bbox_el = WPS.BoundingBoxData(OWS.LowerCorner('20 -112'),
                                  OWS.UpperCorner('45 -87'))

    bbox_el.attrib['crs'] = "EPSG:4326"
    bbox = BoundingBox(bbox_el)

    assert int(bbox.minx) == -112
    assert int(bbox.miny) == 20
    assert int(bbox.maxx) == -87
    assert int(bbox.maxy) == 45


def test_bbox_input():
    """ Test extent parameter
    """
    param = QgsProcessingParameterExtent("BBOX")

    inp = parse_input_definition(param)

    assert isinstance(inp, BoundingBoxInput)
    assert inp.crss[0] == "EPSG:4326"

    inp.data = ['15', '50', '16', '51']
    value = geometryio.input_to_extent(inp)

    assert isinstance(value, QgsReferencedRectangle)
    assert isinstance(value, QgsRectangle)

    assert value.xMinimum() == 15
    assert value.yMaximum() == 51
    assert value.yMinimum() == 50
    assert value.xMaximum() == 16

    # Test CRS
    crs = value.crs()
    assert crs.isValid()
    assert crs.authid() == 'EPSG:4326'


def test_bbox_input_with_context(outputdir):
    """ Test extent parameter with context
    """
    context = ProcessingContext(str(outputdir), 'france_parts_3857.qgs')

    project = context.project()
    project_crs = project.crs()
    assert project_crs.isValid()
    assert project_crs.authid() == 'EPSG:3857'

    param = QgsProcessingParameterExtent("BBOX")
    inp = parse_input_definition(param, context=context)

    assert isinstance(inp, BoundingBoxInput)
    assert inp.crss[0] == "EPSG:3857"
    assert inp.crs == "EPSG:3857"

    # see create_bbox_inputs at L532 app/Service.py
    inp.data = ['15', '50', '16', '51']
    value = geometryio.input_to_extent(inp)

    assert isinstance(value, QgsReferencedRectangle)

    # Test CRS
    crs = value.crs()
    assert crs.isValid()
    assert crs.authid() == 'EPSG:3857'


def test_point_input_gml():
    """ Test input point from gml
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.GML)
    inp.data = ('<gml:Point srsName="EPSG:4326">'
                '<gml:coordinates>4,42</gml:coordinates>'
                '</gml:Point>')

    assert inp.data_format.mime_type == FORMATS.GML.mime_type

    value = geometryio.input_to_point(inp)
    assert isinstance(value, QgsReferencedPointXY)


def test_point_input_json():
    """ Test input point from json
    """
    # without a crs
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp.data = '{"coordinates":[4.0,42.0],"type":"Point"}'

    assert inp.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value = geometryio.input_to_point(inp)
    assert isinstance(value, QgsGeometry)

    # with a crs
    param2 = QgsProcessingParameterPoint("POINT")
    inp2 = parse_input_definition(param2)

    assert isinstance(inp2, ComplexInput)
    assert not inp2.as_reference

    inp2.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp2.data = (
        '{'
            '"type":"Point","coordinates":[-3326534.0,5498576.0],'
            '"crs":{'
                '"type":"name","properties":{"name":"EPSG:3857"}'
            '}'
        '}'
    )

    assert inp2.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value2 = geometryio.input_to_point(inp2)
    assert isinstance(value2, QgsReferencedPointXY)
    assert value2.crs().authid() == 'EPSG:3857'
    assert value2.asWkt() == 'POINT(-3326534 5498576)'


def test_point_input_wkt():
    """ Test input point from wkt
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'CRS=EPSG:4326;POINT(6 10)'

    assert inp.data_format.mime_type == FORMATS.WKT.mime_type

    value = geometryio.input_to_point(inp)
    assert isinstance(value, QgsReferencedPointXY)
    assert value.crs().authid() == 'EPSG:4326'
    assert value.asWkt() == 'POINT(6 10)'

    # postgis SRID
    inp2 = parse_input_definition(QgsProcessingParameterPoint("POINT"))
    inp2.data_format = Format.from_definition(FORMATS.WKT)
    inp2.data = 'SRID=3785;POINT(365340 3161978)'
    value2 = geometryio.input_to_point(inp2)
    assert isinstance(value2, QgsReferencedPointXY)
    assert value2.crs().authid() == 'EPSG:3785'
    assert value2.asWkt() == 'POINT(365340 3161978)'


def test_linestring_input_gml():
    """ Test input point from gml
    """
    param = QgsProcessingParameterGeometry("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.GML)
    inp.data = ('<gml:LineString srsName="EPSG:4326">'
                '<gml:coordinates>45.67,88.56 55.56,89.44</gml:coordinates>'
                '</gml:LineString>')

    assert inp.data_format.mime_type == FORMATS.GML.mime_type

    value = geometryio.input_to_geometry(inp)
    assert isinstance(value, QgsReferencedGeometry)
    assert value.wkbType() == QgsWkbTypes.LineString


def test_multipoint_input_json():
    """ Test input point from json
    """
    # without a crs
    param = QgsProcessingParameterPoint("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp.data = '{"coordinates":[[10, 40], [40, 30], [20, 20], [30, 10]],"type":"MultiPoint"}'

    assert inp.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value = geometryio.input_to_geometry(inp)
    assert isinstance(value, QgsGeometry)
    assert value.wkbType() == QgsWkbTypes.MultiPoint

    # with a crs
    param2 = QgsProcessingParameterPoint("GEOM")
    inp2 = parse_input_definition(param2)

    assert isinstance(inp2, ComplexInput)
    assert not inp2.as_reference

    inp2.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp2.data = (
        '{'
            '"coordinates":[[465340, 4161978], [465352, 4161918]],'
            '"type":"MultiPoint", "crs":{'
                '"type":"name","properties":{'
                    '"name":"EPSG:3785"'
                '}'
            '}'
        '}'
    )

    assert inp2.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value2 = geometryio.input_to_geometry(inp2)
    assert isinstance(value2, QgsReferencedGeometry)
    assert value2.crs().authid() == 'EPSG:3785'
    assert value2.asWkt() == 'MultiPoint ((465340 4161978),(465352 4161918))'


def test_multipoint_input_wkt():
    """ Test input point from gml
    """
    param = QgsProcessingParameterPoint("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'CRS=EPSG:4326;MULTIPOINT((3.5 5.6), (4.8 10.5))'

    assert inp.data_format.mime_type == FORMATS.WKT.mime_type

    value = geometryio.input_to_geometry(inp)
    assert isinstance(value, QgsReferencedGeometry)
    assert value.wkbType() == QgsWkbTypes.MultiPoint
    assert value.crs().authid() == 'EPSG:4326'
    assert value.asWkt(2) == 'MultiPoint ((3.5 5.6),(4.8 10.5))'

    # postgis SRID
    inp2 = parse_input_definition(QgsProcessingParameterPoint("GEOM"))
    inp2.data_format = Format.from_definition(FORMATS.WKT)
    inp2.data = 'SRID=3785;MULTIPOINT((465340 4161978), (465352 4161918))'
    value2 = geometryio.input_to_geometry(inp2)
    assert isinstance(value2, QgsReferencedGeometry)
    assert value.wkbType() == QgsWkbTypes.MultiPoint
    assert value2.crs().authid() == 'EPSG:3785'
    assert value2.asWkt() == 'MultiPoint ((465340 4161978),(465352 4161918))'


def test_geometry_crs_json():
    """ Test passing crs from json
    """
    param = QgsProcessingParameterGeometry("GEOM")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.GEOJSON)
    inp.data = ('{ "geometry": {"coordinates":[445277.96, 5160979.44],"type":"Point"},'
                '  "crs": { '
                '    "type": "name", '
                '    "properties": { "name": "EPSG:3785" }'
                '}}')

    assert inp.data_format.mime_type == FORMATS.GEOJSON.mime_type

    value = geometryio.input_to_geometry(inp)
    assert isinstance(value, QgsReferencedGeometry)
    assert value.crs().authid() == "EPSG:3785"
    assert value.wkbType() == QgsWkbTypes.Point


def test_nocrs_input_wkt():
    """ Test input point from wkt
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp, ComplexInput)
    assert not inp.as_reference

    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'POINT(6 10)'

    assert inp.data_format.mime_type == FORMATS.WKT.mime_type

    value = geometryio.input_to_point(inp)
    assert isinstance(value, QgsGeometry)
    assert value.wkbType() == QgsWkbTypes.Point


def test_geometry_geometrytypes():
    """ Test geometryTypes Metadata
    """
    # Single geometry
    param = QgsProcessingParameterGeometry("GEOM", geometryTypes=[QgsWkbTypes.LineGeometry])

    inp = parse_input_definition(param)

    assert get_metadata(inp, 'processing:geometryType')[0].href == "Line"

    # Check allow multipart
    assert len(get_metadata(inp, 'processing:allowMultipart')) == 1

    # Multi Geometry
    param = QgsProcessingParameterGeometry("GEOM",
            geometryTypes=[QgsWkbTypes.LineGeometry, QgsWkbTypes.PointGeometry],
    )

    inp = parse_input_definition(param)

    assert get_metadata(inp, 'processing:geometryType', 2)[0].href == "Line"
    assert get_metadata(inp, 'processing:geometryType', 2)[1].href == "Point"

    assert len(get_metadata(inp, 'processing:allowMultipart')) == 1

    # Test output XML
    xml = inp.describe_xml()

    def _get_geometryTypes(el):
        for metadata_el in xpath_ns(el, './ows:Metadata'):
            if metadata_el.attrib['{http://www.w3.org/1999/xlink}title'] == 'processing:geometryType':
                yield metadata_el.attrib['{http://www.w3.org/1999/xlink}href']

    geomtypes = tuple(_get_geometryTypes(xml))
    assert len(geomtypes) == 2
    for type_ in geomtypes:
        assert type_ in ("Line", "Point")


def test_geometry_nomultipart():
    """ Test geometry multipart Metadata
    """
    # Single geometry
    param = QgsProcessingParameterGeometry("GEOM", geometryTypes=[QgsWkbTypes.LineGeometry],
                                           allowMultipart=False)

    inp = parse_input_definition(param)

    assert get_metadata(inp, 'processing:geometryType')[0].href == "Line"

    # No multipart
    assert get_metadata(inp, 'processing:allowMultipart', minOccurence=0) == []


def test_geometry_algorithm(outputdir, data):
    """ Test geometry algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testinputgeometry')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inp = inputs['INPUT'][0]
    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'CRS=EPSG:4326;MULTIPOINT((3.5 5.6), (4.8 10.5))'

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    # Check marshalled value
    value = parameters['INPUT']
    assert isinstance(value, QgsReferencedGeometry)
    assert value.wkbType() == QgsWkbTypes.MultiPoint

    context.wms_url = f"http://localhost/wms/?MAP=test/{alg.name()}.qgs"
    # Run algorithm
    with chdir(outputdir):
        _results = run_algorithm(
            alg,
            parameters=parameters,
            feedback=feedback,
            context=context,
            uuid="uuid",
            outputs=outputs,
        )

    out = json.loads(outputs.get('OUTPUT').data)
    assert out['type'] == 'MultiPoint'


def test_geometry_script(outputdir, data):
    """ Test geometry script
    """
    alg = _find_algorithm('script:testinputgeometry')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inp = inputs['INPUT'][0]
    inp.data_format = Format.from_definition(FORMATS.WKT)
    inp.data = 'CRS=EPSG:4326;MULTIPOINT((3.5 5.6), (4.8 10.5))'

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    # Check marshalled value
    value = parameters['INPUT']
    assert isinstance(value, QgsReferencedGeometry)
    assert value.wkbType() == QgsWkbTypes.MultiPoint

    context.wms_url = f"http://localhost/wms/?MAP=test/{alg.name()}.qgs"
    # Run algorithm
    with chdir(outputdir):
        _results = run_algorithm(
            alg,
            parameters=parameters,
            feedback=feedback,
            context=context,
            uuid="uuid",
            outputs=outputs,
        )

    out = json.loads(outputs.get('OUTPUT').data)
    assert out['type'] == 'MultiPoint'
