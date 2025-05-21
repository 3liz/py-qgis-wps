"""
    Test Processing file io
"""
from urllib.parse import parse_qs, urlencode, urlparse

import pytest

from qgis.core import (
    Qgis,
    QgsProcessingContext,
    QgsProcessingOutputLayerDefinition,
    QgsProcessingParameterMeshLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
    QgsProject,
)

from pyqgiswps.executors.io import layersio
from pyqgiswps.executors.processfactory import get_process_factory
from pyqgiswps.executors.processingio import (
    parse_input_definition,
)
from pyqgiswps.executors.processingprocess import MapContext, _find_algorithm
from pyqgiswps.tests import HTTPTestCase, chconfig


def get_metadata(inp, name, minOccurence=1, maxOccurence=None):
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

    value = layersio.get_processing_value(param, [inp], context)
    assert value == "layername"


def test_arbitrary_layer_scheme():
    """ Test arbitrary layer scheme does not trig an error
    """
    param = QgsProcessingParameterVectorLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "foobar:layername"

    context = QgsProcessingContext()

    value = layersio.get_processing_value(param, [inp], context)
    assert value == "foobar:layername"


def test_multilayer_with_selection():
    """ Test map context return allowed layers
    """
    alg = _find_algorithm('pyqgiswps_test:testinputmultilayer')
    context = MapContext('france_parts.qgs')
    inputs = {p.name(): [parse_input_definition(p, alg, context)] for p in alg.parameterDefinitions()}

    inpt = inputs['INPUT'][0]
    allowed_values = {value for value in inpt.allowed_values.values}

    assert 'france_parts' in allowed_values
    data = 'layer:france_parts?' + urlencode((('select', 'OBJECTID=2662 OR OBJECTID=2664'),))

    inpt.data = data
    # self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE))


def test_vector_default_fileext():
    """ Tests default vector file extension config
    """
    param = QgsProcessingParameterVectorDestination("LAYER", "")
    with chconfig('processing', 'vector.fileext', 'csv'):
        ext, _defval = layersio.get_default_destination_values(param, None)
        assert ext == 'csv'


def test_raster_default_fileext():
    """ Tests default vector file extension config
    """
    param = QgsProcessingParameterRasterDestination("LAYER", "")
    with chconfig('processing', 'raster.fileext', 'foo'):
        ext, _defval = layersio.get_default_destination_values(param, None)
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
    value = layersio.get_processing_value(param, [inp], context)
    assert isinstance(value, QgsProcessingOutputLayerDefinition)
    assert value.destinationName == 'bar'
    assert value.sink.staticValue() == './LAYER.shp'

    # Check unsafe option
    with chconfig('processing', 'unsafe.raw_destination_input_sink', 'yes'):
        inp.data = "/foobar.csv"
        value = layersio.get_processing_value(param, [inp], context)
        assert value.destinationName == 'foobar'
        assert value.sink.staticValue() == 'foobar.csv'

    # Check unsafe option with default extension
    with chconfig('processing', 'unsafe.raw_destination_input_sink', 'yes'):
        inp.data = "/foobar"
        value = layersio.get_processing_value(param, [inp], context)
        assert value.destinationName == 'foobar'
        assert value.sink.staticValue() == 'foobar.shp'

    # Check unsafe option with layername
    with chconfig('processing', 'unsafe.raw_destination_input_sink', 'yes'),\
        chconfig('processing', 'destination_root_path', '/unsafe'):
        inp.data = "file:/path/to/foobar.csv|layername=foobaz"
        value = layersio.get_processing_value(param, [inp], context)
        assert value.destinationName == 'foobaz'
        assert value.sink.staticValue() == '/unsafe/path/to/foobar.csv'

    # Check unsafe option with url
    with chconfig('processing', 'unsafe.raw_destination_input_sink', 'yes'):
        inp.data = "postgres://service=foobar|layername=foobaz"
        value = layersio.get_processing_value(param, [inp], context)
        assert value.destinationName == 'foobaz'
        assert value.sink.staticValue() == 'postgres://service=foobar'


def test_mesh_layer():
    param = QgsProcessingParameterMeshLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "layer:layername"

    assert get_metadata(inp, "processing:dataTypes")[0].href == "TypeMesh"

    context = QgsProcessingContext()

    value = layersio.get_processing_value(param, [inp], context)
    assert value == "layername"


@pytest.mark.usefixtures("workdir_class")
class TestsLayerIO(HTTPTestCase):

    def get_processes(self):
        return get_process_factory()._create_qgis_processes()

    def test_output_layer(self):
        """ Test output layer and dataUrl
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0'
               '&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200

        output = rv.xpath('/wps:ExecuteResponse'
                          '/wps:ProcessOutputs'
                          '/wps:Output'
                          '/wps:Reference')

        assert len(output) == 1
        assert output[0].get('mimeType') == "application/x-ogc-wms"

        # retrieve status_location_url
        execute_response = rv.xpath('/wps:ExecuteResponse')
        assert len(execute_response) == 1
        status_location_url = execute_response[0].get('statusLocation')

        # retrieve uuid
        parsed_url = urlparse(status_location_url)
        q = parse_qs(parsed_url.query)
        assert 'uuid' in q
        uuid = q['uuid'][0]

        # Get the project
        project_path = self.workdir / uuid / "pyqgiswps_test_testcopylayer.qgs"
        assert project_path.is_file()

        project = QgsProject()
        project.read(str(project_path))

        # check dataUrl
        layers = [layer for _, layer in project.mapLayers().items()]
        assert len(layers) == 1
        expected_data_url = f"{parsed_url.scheme}://{parsed_url.netloc}/jobs/{uuid}/files/OUTPUT.shp"
        if Qgis.QGIS_VERSION_INT >= 33800:
            server_properties = layers[0].serverProperties()
            assert server_properties.dataUrl() == expected_data_url
            assert server_properties.dataUrlFormat() == "text/plain"
        else:
            assert layers[0].dataUrl() == expected_data_url
            assert layers[0].dataUrlFormat() == "text/plain"
