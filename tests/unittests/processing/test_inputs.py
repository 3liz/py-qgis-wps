""" Test parsing processing itputs to WPS inputs
"""
import os

#from pyqgiswps.utils.qgis import setup_qgis_paths
#setup_qgis_paths()

from pyqgiswps.utils.contexts import chdir 

from pyqgiswps.inout import (LiteralInput, 
                        ComplexInput,
                        BoundingBoxInput, 
                        LiteralOutput, 
                        ComplexOutput,
                        BoundingBoxOutput)

from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE
from pyqgiswps.executors.processingio import(
            parse_literal_input,
            parse_layer_input,
            parse_extent_input,
            parse_input_definition,
            parse_literal_output,
            parse_layer_output,
            parse_output_definition,
            input_to_processing,
            processing_to_output,
            _is_optional,
        ) 

from pyqgiswps.executors.processingprocess import(
        handle_algorithm_results,
        handle_layer_outputs,
        write_outputs,
        _find_algorithm)


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
                       QgsProcessingParameterFile,
                       QgsProcessingParameterField,
                       QgsProcessingUtils,
                       QgsProcessingFeedback,
                       QgsProcessingContext,
                       QgsReferencedRectangle,
                       QgsRectangle,
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


def test_input_title():
    param = QgsProcessingParameterNumber(
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
    assert isinstance(inp, LiteralInput)
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

    assert parameters['OUTPUT'] == 'file'


def test_file_output_mimetypes():
    """ Test file output mimetype 
    """
    outdef  = QgsProcessingOutputFile("OUTPUT","test output file") 
    context = QgsProcessingContext()
    context.workdir = "/path/to/workdir"

    out = parse_output_definition(outdef)

    output = processing_to_output('file.png', outdef, out, output_uri=None, context=context)  
    assert output.output_format == 'image/png'

    output = processing_to_output('binaryfile', outdef, out, output_uri=None, context=context)  
    assert output.output_format == 'application/octet-stream'


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


