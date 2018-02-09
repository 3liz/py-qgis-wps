""" Test parsing processing itputs to WPS inputs
"""
import os

from qywps.utils.qgis import setup_qgis_paths
setup_qgis_paths()

from qywps.utils.contexts import chdir 

from qywps.inout import (LiteralInput, 
                        ComplexInput,
                        BoundingBoxInput, 
                        LiteralOutput, 
                        ComplexOutput,
                        BoundingBoxOutput)

from qywps.validator.allowed_value import ALLOWEDVALUETYPE
from qywps.executors.processingprocess import(
            parse_literal_input,
            parse_layer_input,
            parse_extent_input,
            parse_input_definition,
            parse_literal_output,
            parse_layer_output,
            parse_output_definition,
            input_to_processing,
            processing_to_output,
            handle_algorithm_results,
            handle_layer_outputs,
            write_outputs,
            _find_algorithm,
        ) 

from qgis.core import QgsApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputHtml,
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
    


def get_metadata( inp, name, minOccurence=1, maxOccurence=None ):
    if maxOccurence is None:
        maxOccurence = minOccurence
    assert minOccurence <= maxOccurence
    m = list(filter(lambda m: m.title == name, inp.metadata))
    assert len(m) >= minOccurence
    assert len(m) <= maxOccurence
    return m

