"""
    Test Processing file io
"""
import pytest

from urllib.parse import urlparse, parse_qs, urlencode

from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase, assert_response_accepted, chconfig
from time import sleep
from test_common import async_test

from qgis.core import (QgsProcessingContext,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterMeshLayer,
                       QgsProcessingOutputLayerDefinition,)


from pyqgiswps.executors.io import layersio
from pyqgiswps.executors.processingio import(
            parse_input_definition,
            parse_output_definition,
        )

from pyqgiswps.executors.processingprocess import (
            MapContext, 
            ProcessingContext,
            _find_algorithm
        )

from pyqgiswps.exceptions import (NoApplicableCode,
                                  InvalidParameterValue,
                                  MissingParameterValue,
                                  ProcessException)

def get_metadata( inp, name, minOccurence=1, maxOccurence=None ):
    if maxOccurence is None:
        maxOccurence = minOccurence
    assert minOccurence <= maxOccurence
    m = list(filter(lambda m: m.title == name, inp.metadata))
    assert len(m) >= minOccurence
    assert len(m) <= maxOccurence
    return m



def test_layer_scheme():
    """ Test layer scheme
    """
    param = QgsProcessingParameterVectorLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "layer:layername"

    context = QgsProcessingContext()

    value = layersio.get_processing_value( param, [inp], context)
    assert value == "layername"


def test_arbitrary_layer_scheme():
    """ Test arbitrary layer scheme does not trig an error
    """
    param = QgsProcessingParameterVectorLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "foobar:layername"

    context = QgsProcessingContext()

    value = layersio.get_processing_value( param, [inp], context)
    assert value == "foobar:layername"


def test_multilayer_with_selection():
    """ Test map context return allowed layers
    """
    alg = _find_algorithm('pyqgiswps_test:testinputmultilayer')
    context = MapContext('france_parts.qgs')
    inputs  = { p.name(): [parse_input_definition(p,alg,context)] for p in  alg.parameterDefinitions() }

    inpt = inputs['INPUT'][0]
    allowed_values = { v.value for v in inpt.allowed_values }

    assert 'france_parts' in allowed_values
    data = 'layer:france_parts?'+urlencode((('select','OBJECTID=2662 OR OBJECTID=2664'),))

    inpt.data = data
    #self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE))    


def test_vector_default_fileext():
    """ Tests default vector file extension config
    """
    param = QgsProcessingParameterVectorDestination("LAYER", "")
    with chconfig('processing','vector.fileext','csv'):
        ext, defval = layersio.get_default_destination_values(param,None)
        assert ext == 'csv'

def test_raster_default_fileext():
    """ Tests default vector file extension config
    """
    param = QgsProcessingParameterRasterDestination("LAYER", "")
    with chconfig('processing','raster.fileext','foo'):
        ext, defval = layersio.get_default_destination_values(param,None)
        assert ext == 'foo'


def test_layer_destination():

    param = QgsProcessingParameterVectorDestination("LAYER", "",
                          defaultValue=QgsProcessingOutputLayerDefinition('foo.shp'))
    inp = parse_input_definition(param)
    assert inp.default == "foo"

    metadata = layersio.get_metadata(inp, 'processing:extension')
    assert len(metadata) == 1
    assert metadata[0] == 'shp'

    inp.data = "bar"

    context = QgsProcessingContext()
    context.destination_project = None

    inp.data = "bar"
    value = layersio.get_processing_value( param, [inp], context)
    assert isinstance(value, QgsProcessingOutputLayerDefinition)
    assert value.destinationName == 'bar'
    assert value.sink.staticValue() == './LAYER.shp'

    # Check unsafe option
    with chconfig('processing','unsafe.raw_destination_input_sink','yes'):
        inp.data = "/foobar.csv"
        value = layersio.get_processing_value( param, [inp], context)
        assert value.destinationName == 'foobar'
        assert value.sink.staticValue() == 'foobar.csv'

    # Check unsafe option with default extension
    with chconfig('processing','unsafe.raw_destination_input_sink','yes'):
        inp.data = "/foobar"
        value = layersio.get_processing_value( param, [inp], context)
        assert value.destinationName == 'foobar'
        assert value.sink.staticValue() == 'foobar.shp'

    # Check unsafe option with layername
    with chconfig('processing','unsafe.raw_destination_input_sink','yes'),\
         chconfig('processing','destination_root_path','/unsafe'):
        inp.data = "file:/path/to/foobar.csv|layername=foobaz"
        value = layersio.get_processing_value( param, [inp], context)
        assert value.destinationName == 'foobaz'
        assert value.sink.staticValue() == '/unsafe/path/to/foobar.csv'

     # Check unsafe option with url
    with chconfig('processing','unsafe.raw_destination_input_sink','yes'):
        inp.data = "postgres://service=foobar|layername=foobaz"
        value = layersio.get_processing_value( param, [inp], context)
        assert value.destinationName == 'foobaz'
        assert value.sink.staticValue() == 'postgres://service=foobar'

    
def test_mesh_layer():
    param = QgsProcessingParameterMeshLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "layer:layername"

    assert get_metadata(inp, "processing:dataTypes")[0].href == "TypeMesh" 

    context = QgsProcessingContext()

    value = layersio.get_processing_value( param, [inp], context)
    assert value == "layername"

