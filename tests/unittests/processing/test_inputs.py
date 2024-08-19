""" Test parsing processing itputs to WPS inputs
"""
from urllib.parse import parse_qs, urlparse

import pytest

from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingOutputFile,
    QgsProcessingOutputMultipleLayers,
    QgsProcessingParameterDistance,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterScale,
    QgsUnitTypes,
)

from pyqgiswps.executors.processingio import (
    _is_optional,
    input_to_processing,
    parse_input_definition,
    parse_output_definition,
    processing_to_output,
)
from pyqgiswps.executors.processingprocess import _find_algorithm
from pyqgiswps.inout import (
    ComplexOutput,
    LiteralInput,
)
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE


def get_metadata(inp, name, minOccurence=1, maxOccurence=None):
    if maxOccurence is None:
        maxOccurence = minOccurence
    assert minOccurence <= maxOccurence
    m = list(filter(lambda m: m.title == name, inp.metadata))
    assert len(m) >= minOccurence
    assert len(m) <= maxOccurence
    return m


def test_literal_input():
    param = QgsProcessingParameterNumber("TEST", "LiteralInteger",
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "integer"
    assert inp.allowed_values.allowed_type == ALLOWEDVALUETYPE.RANGE
    assert inp.allowed_values.minval == param.minimum()
    assert inp.allowed_values.maxval == param.maximum()
    assert inp.default == param.defaultValue()


def test_scale_input():
    param = QgsProcessingParameterScale("TEST", "LiteralScale", defaultValue=2.0)
    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "scale"
    assert inp.default == param.defaultValue()


def test_distance_input():
    param = QgsProcessingParameterDistance("TEST", "LiteralDistance",
            defaultValue=2.0,
            minValue=1.0,
            maxValue=100.0)
    param.setDefaultUnit(QgsUnitTypes.DistanceMeters)
    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "length"
    assert inp.default == param.defaultValue()
    assert inp.allowed_values.allowed_type == ALLOWEDVALUETYPE.RANGE
    assert inp.allowed_values.minval == param.minimum()
    assert inp.allowed_values.maxval == param.maximum()
    assert get_metadata(inp, 'processing:defaultUnit')[0].href == QgsUnitTypes.toString(param.defaultUnit())


@pytest.mark.skipif(Qgis.QGIS_VERSION_INT < 32200, reason="requires qgis 3.22+")
def test_duration_input():
    from qgis.core import QgsProcessingParameterDuration

    param = QgsProcessingParameterDuration("TEST", "LiteralDuration",
            defaultValue=2.0,
            minValue=1.0,
            maxValue=100.0)
    param.setDefaultUnit(QgsUnitTypes.TemporalSeconds)
    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "time"
    assert inp.default == param.defaultValue()
    assert inp.allowed_values.allowed_type == ALLOWEDVALUETYPE.RANGE
    assert inp.allowed_values.minval == param.minimum()
    assert inp.allowed_values.maxval == param.maximum()
    assert get_metadata(inp, 'processing:defaultUnit')[0].href == QgsUnitTypes.toString(param.defaultUnit())


def test_options_input():
    options = ["opt0", "opt1", "opt2"]
    param = QgsProcessingParameterEnum("OPTION", "Option",
                    options=options, defaultValue=1)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert inp.allowed_values.values[0] == options[0]
    assert inp.allowed_values.values[1] == options[1]
    assert inp.allowed_values.values[2] == options[2]
    assert inp.default == options[1]


def test_multi_options_input():
    options = ["opt0", "opt1", "opt2"]
    param = QgsProcessingParameterEnum("OPTION", "Option",
                    options=options, allowMultiple=True, defaultValue=1)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert inp.allowed_values.values[0] == options[0]
    assert inp.allowed_values.values[1] == options[1]
    assert inp.allowed_values.values[2] == options[2]
    assert inp.default == options[1]
    assert inp.max_occurs == len(options)


def test_bad_options_default_value():
    """ Test with an invalid default value

        This should not invalidate the input but log a warning and
        reset the option default value to 0
    """
    options = ["opt0", "opt1", "opt2"]
    param = QgsProcessingParameterEnum("OPTION", "Option",
                    options=options, defaultValue=450)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.default == options[0]


def test_field_input():
    param = QgsProcessingParameterField(
                "XFIELD",
                'X Field',
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Any,
            )

    inp = parse_input_definition(param)
    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert get_metadata(inp, 'processing:dataType')[0].href == 'Any'
    assert get_metadata(inp, 'processing:parentLayerParameterName')[0].href == 'INPUT'


def test_optional_input():
    param = QgsProcessingParameterField(
                "XFIELD",
                'X Field',
                parentLayerParameterName='INPUT',
                optional=True,
                type=QgsProcessingParameterField.Any,
            )

    inp = parse_input_definition(param)
    assert isinstance(inp, LiteralInput)
    assert inp.data_type == 'string'
    assert inp.min_occurs == 0


def test_source_types_metadata():
    param = QgsProcessingParameterFeatureSource("FSOURCE", '',
            [QgsProcessing.TypeVectorLine,
             QgsProcessing.TypeVectorPoint])

    inp = parse_input_definition(param)
    assert get_metadata(inp, 'processing:dataTypes')[0].href == 'TypeVectorLine,TypeVectorPoint'


def test_freeform_metadata():
    param = QgsProcessingParameterNumber("TEST", "LiteralInteger",
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    param.setMetadata({'meta1': 'value1', 'meta2': 'value2'})

    inp = parse_input_definition(param)
    assert get_metadata(inp, 'processing:meta:meta1')[0].href == 'value1'
    assert get_metadata(inp, 'processing:meta:meta2')[0].href == 'value2'


def test_optional_inputs():
    not_optional_param = QgsProcessingParameterNumber("TEST1", "LiteralInteger",
              type=QgsProcessingParameterNumber.Integer,
              minValue=1, defaultValue=10)

    assert not _is_optional(not_optional_param)

    optional_param = QgsProcessingParameterNumber("TEST2", "LiteralInteger",
              type=QgsProcessingParameterNumber.Integer,
              optional=True,
              minValue=1, defaultValue=10)

    assert _is_optional(optional_param)

    optional_input = parse_input_definition(optional_param)
    not_optional_input = parse_input_definition(not_optional_param)

    assert optional_input.min_occurs == 0
    assert not_optional_input.min_occurs > 0


def test_file_destination():
    alg = _find_algorithm('pyqgiswps_test:testfiledestination')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    inputs['OUTPUT'][0].data = '/bad/..//path/to/file'

    context = QgsProcessingContext()
    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert parameters['OUTPUT'] == 'file.json'


def test_file_output_mimetypes():
    """ Test file output mimetype
    """
    outdef = QgsProcessingOutputFile("OUTPUT", "test output file")
    context = QgsProcessingContext()
    context.workdir = "/path/to/workdir"

    out = parse_output_definition(outdef)

    output = processing_to_output('file.png', outdef, out, context=context)
    assert isinstance(output, ComplexOutput)
    assert output.as_reference
    assert output.url == "store:file.png"
    assert output.data_format.mime_type == 'image/png'

    output = processing_to_output('binaryfile', outdef, out, context=context)
    assert output.data_format.mime_type == 'application/octet-stream'


def test_input_title():
    input_title = "This is the title"
    input_abstract = "This is the input abstract"
    param = QgsProcessingParameterNumber("Input_title",
                  description=input_title,
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    param.setHelp(input_abstract)

    inp = parse_input_definition(param)

    assert inp.title == input_title
    assert inp.abstract == input_abstract


def test_output_multiple_layers(outputdir, data):
    """ Test QgsProcessingOutputMultipleLayers
    """
    outdef = QgsProcessingOutputMultipleLayers("LAYERS")

    # Load source project
    layer1 = str(data / 'france_parts' / 'france_parts.shp')
    layer2 = str(data / 'raster_layer.tiff')

    context = QgsProcessingContext()
    context.wms_url = 'test:multilayer?service=WMS'

    outp = parse_output_definition(outdef)
    output = processing_to_output([layer1, layer2], outdef, outp, context=context)

    assert isinstance(output, ComplexOutput)
    assert output.as_reference
    assert output.data_format.mime_type == 'application/x-ogc-wms'

    query = parse_qs(urlparse(output.url).query)
    assert query['layers'][0] == 'france_parts,raster_layer'


def test_parameter_abstract():

    helpstr = """
      This is a help text.
      It must appears in the 'abstract' field of
      wps
    """

    title = "Parameter with help"

    param = QgsProcessingParameterNumber("TEST", title,
                  type=QgsProcessingParameterNumber.Integer,
                  minValue=1, defaultValue=10)

    param.setHelp(helpstr)

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.title      == title
    assert inp.abstract   == helpstr
