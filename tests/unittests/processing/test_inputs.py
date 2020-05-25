""" Test parsing processing itputs to WPS inputs
"""
import os
from pathlib import Path

from pyqgiswps.utils.contexts import chdir 

from pyqgiswps import WPS, OWS
from pyqgiswps.owsutils.ows import BoundingBox
from pyqgiswps.inout import (LiteralInput, 
                             ComplexInput,
                             BoundingBoxInput, 
                             LiteralOutput, 
                             ComplexOutput,
                             BoundingBoxOutput)

from pyqgiswps.inout.formats import FORMATS, Format

from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE
from pyqgiswps.executors.processingio import(
            parse_literal_input,
            parse_extent_input,
            parse_input_definition,
            parse_literal_output,
            parse_output_definition,
            parse_point_input,
            input_to_processing,
            input_to_point,
            processing_to_output,
            input_to_extent,
            _is_optional,
        ) 

from pyqgiswps.executors.io import filesio
from pyqgiswps.executors.processingprocess import _find_algorithm

from qgis.core import QgsApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputHtml,
                       QgsProcessingOutputFile,
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputVectorLayer,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterField,
                       QgsProcessingParameterPoint,
                       QgsProcessingUtils,
                       QgsProcessingFeedback,
                       QgsProcessingContext,
                       QgsReferencedRectangle,
                       QgsRectangle,
                       QgsReferencedPointXY,
                       QgsGeometry,
                       QgsCoordinateReferenceSystem,
                       QgsProject)

from processing.core.Processing import Processing


def test_literal_input():
    param = QgsProcessingParameterNumber("TEST", "LiteralInteger",
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "integer"
    assert len(inp.allowed_values) == 1
    assert inp.allowed_values[0].allowed_type == ALLOWEDVALUETYPE.RANGE
    assert inp.allowed_values[0].minval == param.minimum()
    assert inp.allowed_values[0].maxval == param.maximum()
    assert inp.default == param.defaultValue()



def test_options_input():
    options = ["opt0","opt1","opt2"]
    param   = QgsProcessingParameterEnum("OPTION","Option",
                    options=options, defaultValue=1)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert inp.allowed_values[0].value == options[0]
    assert inp.allowed_values[1].value == options[1]
    assert inp.allowed_values[2].value == options[2]
    assert inp.default == options[1]


def test_multi_options_input():
    options = ["opt0","opt1","opt2"]
    param   = QgsProcessingParameterEnum("OPTION","Option",
                    options=options, allowMultiple=True, defaultValue=1)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert inp.allowed_values[0].value == options[0]
    assert inp.allowed_values[1].value == options[1]
    assert inp.allowed_values[2].value == options[2]
    assert inp.default == options[1]
    assert inp.max_occurs == len(options)


def test_field_input():
    param = QgsProcessingParameterField(
                "XFIELD",
                'X Field',
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Any
            )

    inp = parse_input_definition(param)
    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert get_metadata(inp,'processing:dataType')[0].href == 'Any'
    assert get_metadata(inp,'processing:parentLayerParameterName')[0].href == 'INPUT'
    

def test_optional_input():
    param = QgsProcessingParameterField(
                "XFIELD",
                'X Field',
                parentLayerParameterName='INPUT',
                optional=True,
                type=QgsProcessingParameterField.Any
            )

    inp = parse_input_definition(param)
    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert inp.min_occurs == 0


def test_source_types_metadata():
    param = QgsProcessingParameterFeatureSource( "FSOURCE", '',  
            [QgsProcessing.TypeVectorLine,
             QgsProcessing.TypeVectorPoint])

    inp = parse_input_definition(param)
    assert get_metadata(inp,'processing:dataTypes')[0].href == 'TypeVectorLine,TypeVectorPoint'
 

def test_freeform_metadata():
    param = QgsProcessingParameterNumber("TEST", "LiteralInteger",
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    param.setMetadata({'meta1':'value1', 'meta2':'value2' })

    inp = parse_input_definition(param)
    assert get_metadata(inp,'processing:meta:meta1')[0].href == 'value1'
    assert get_metadata(inp,'processing:meta:meta2')[0].href == 'value2'
    

def test_optional_inputs():
    not_optional_param = QgsProcessingParameterNumber("TEST1", "LiteralInteger",
              type=QgsProcessingParameterNumber.Integer,
              minValue=1, defaultValue=10)

    assert not _is_optional(not_optional_param)

    optional_param = QgsProcessingParameterNumber("TEST2", "LiteralInteger",
              type=QgsProcessingParameterNumber.Integer,
              optional = True,
              minValue=1, defaultValue=10)

    assert _is_optional(optional_param)

    optional_input     = parse_input_definition(optional_param) 
    not_optional_input = parse_input_definition(not_optional_param) 

    assert optional_input.min_occurs == 0
    assert not_optional_input.min_occurs > 0


def test_file_destination():
    alg = _find_algorithm('pyqgiswps_test:testfiledestination')

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    inputs['OUTPUT'][0].data = '/bad/..//path/to/file'

    context  = QgsProcessingContext()
    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )

    assert parameters['OUTPUT'] == 'file.json'


def test_file_output_mimetypes():
    """ Test file output mimetype 
    """
    outdef  = QgsProcessingOutputFile("OUTPUT","test output file") 
    context = QgsProcessingContext()
    context.store_url = "store:{file}"
    context.workdir   = "/path/to/workdir"

    out = parse_output_definition(outdef)

    output = processing_to_output('file.png', outdef, out, output_uri=None, context=context)
    assert isinstance(output, ComplexOutput)
    assert output.as_reference
    assert output.url == "store:file.png"
    assert output.data_format.mime_type == 'image/png'

    output = processing_to_output('binaryfile', outdef, out, output_uri=None, context=context) 
    assert output.data_format.mime_type == 'application/octet-stream'


def test_input_title():
    param = QgsProcessingParameterNumber("Input_title",
                  description="A short description",
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    inp = parse_input_definition(param)

    assert inp.title == "Input title"
    assert inp.abstract == "A short description"


def get_metadata( inp, name, minOccurence=1, maxOccurence=None ):
    if maxOccurence is None:
        maxOccurence = minOccurence
    assert minOccurence <= maxOccurence
    m = list(filter(lambda m: m.title == name, inp.metadata))
    assert len(m) >= minOccurence
    assert len(m) <= maxOccurence
    return m


def test_bbox_input():
    """ Test extent parameter
    """ 
    param = QgsProcessingParameterExtent("BBOX")
    
    inp = parse_input_definition(param)

    assert isinstance(inp,BoundingBoxInput)

    # see create_bbox_inputs at L532 app/Service.py
    inp.data = ['15', '50', '16', '51']
    value = input_to_extent( inp ) 

    assert isinstance(value,QgsReferencedRectangle)


def test_file_input( outputdir ):
    """ Test file parameter
    """
    param = QgsProcessingParameterFile("FILE", extension=".txt")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data = "Hello world"

    context = QgsProcessingContext()
    context.workdir = outputdir.strpath

    value = filesio.get_processing_value( param, [inp], context)

    outputpath = (Path(context.workdir)/param.name()).with_suffix(param.extension())
    assert value == outputpath.name
    assert outputpath.exists()
    
    with outputpath.open('r') as f:
        assert f.read() == inp.data


def test_point_input_gml():
    """ Test input point from gml
    """
    param = QgsProcessingParameterPoint("POINT")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data_format = Format.from_definition(FORMATS.GML)
    inp.data = '<gml:Point srsName="EPSG:4326"><gml:coordinates>4,42</gml:coordinates></gml:Point>'

    assert inp.data_format.mime_type == FORMATS.GML.mime_type

    value = input_to_point( inp )
    assert isinstance( value, (QgsGeometry, QgsReferencedPointXY))


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

    value = input_to_point( inp )
    assert isinstance( value, (QgsGeometry, QgsReferencedPointXY))


