""" Test parsing processing itputs to WPS inputs
"""
import os

from os import PathLike
from urllib.parse import parse_qs, urlencode, urlparse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputLayerDefinition,
    QgsProcessingUtils,
    QgsProject,
)

from pyqgiswps.config import confservice
from pyqgiswps.executors.processingio import (
    input_to_processing,
    parse_input_definition,
    parse_output_definition,
)
from pyqgiswps.executors.processingprocess import _find_algorithm, run_algorithm
from pyqgiswps.utils.contexts import chdir
from pyqgiswps.utils.filecache import get_valid_filename


class Context(QgsProcessingContext):

    confservice.set('wps.request', 'host_url', 'http://localhost/test-algos/')

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


def get_expected_data_url(uuid: str, filename: str) -> str:
    host_url = confservice.get('wps.request', 'host_url').rstrip("/")
    return f"{host_url}/jobs/{uuid}/files/{filename}"


def test_provider():
    registry = QgsApplication.processingRegistry()
    provider = registry.providerById('pyqgiswps_test')
    assert provider is not None
    assert provider.id() == 'pyqgiswps_test'
    assert len(provider.algorithms()) > 0
    assert registry.algorithmById('pyqgiswps_test:testsimplevalue') is not None, 'pyqgiswps_test:testsimplevalue'
    assert registry.algorithmById('pyqgiswps_test:testcopylayer') is not None, 'pyqgiswps_test:testcopylayer'


def test_simple_algorithms():
    """ Execute a simple algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testsimplevalue')

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['PARAM1'][0].data = '1'
    inputs['PARAM2'][0].data = 'stuff'

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert parameters['PARAM1'] == 1
    assert parameters['PARAM2'] == 'stuff'

    # Run algorithm
    results = run_algorithm(
        alg,
        parameters=parameters,
        feedback=feedback,
        context=context,
        uuid="uuid",
        outputs=outputs,
    )

    assert results['OUTPUT'] == "1 stuff"
    assert outputs['OUTPUT'].data == "1 stuff"


def test_option_algorithms():
    """ Execute a simple choice  algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testoptionvalue')

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['INPUT'][0].data = 'value1'

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert parameters['INPUT'] == 0

    # Run algorithm
    results = run_algorithm(
        alg,
        parameters=parameters,
        feedback=feedback,
        context=context,
        uuid="uuid",
        outputs=outputs,
    )

    assert results['OUTPUT'] == 'selection is 0'
    assert outputs['OUTPUT'].data == "selection is 0"


def test_option_multi_algorithms():
    """ Execute a multiple choice  algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testmultioptionvalue')

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    inputs = {p.name(): parse_input_definition(p) for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    source = inputs['INPUT']
    inputs['INPUT'] = [source.clone(), source.clone()]
    inputs['INPUT'][0].data = 'value1'
    inputs['INPUT'][1].data = 'value3'

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert parameters['INPUT'] == [0, 2]

    # Run algorith
    results = run_algorithm(
        alg,
        parameters=parameters,
        feedback=feedback,
        context=context,
        uuid="uuid",
        outputs=outputs,
    )

    assert results['OUTPUT'] == 'selection is 0,2'
    assert outputs['OUTPUT'].data == "selection is 0,2"


def test_layer_algorithm(outputdir, data):
    """ Copy layer
    """
    alg = _find_algorithm('pyqgiswps_test:testcopylayer')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['INPUT'][0].data = 'france_parts'
    inputs['OUTPUT'][0].data = 'france_parts_2'

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    destination = get_valid_filename(alg.id())

    assert isinstance(parameters['OUTPUT'], QgsProcessingOutputLayerDefinition)

    context.wms_url = f"http://localhost/wms/MAP=test/{destination}.qgs"

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

    output = parameters['OUTPUT']
    assert output.destinationName == 'france_parts_2'
    assert output.sink.staticValue() == './OUTPUT.shp'
    assert context.destination_project.count() == 1


def test_buffer_algorithm(outputdir, data):
    """ Test simple layer output
    """
    alg = _find_algorithm('pyqgiswps_test:simplebuffer')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['INPUT'][0].data = 'france_parts'
    inputs['OUTPUT_VECTOR'][0].data = 'buffer'
    inputs['DISTANCE'][0].data = 0.05

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert isinstance(parameters['OUTPUT_VECTOR'], QgsProcessingOutputLayerDefinition)
    assert isinstance(parameters['DISTANCE'], float)

    context.wms_url = f"http://localhost/wms/?MAP=test/{alg.name()}.qgs"
    uuid = "uuid-1234"
    # Run algorithm
    with chdir(outputdir):
        _results = run_algorithm(
            alg,
            parameters=parameters,
            feedback=feedback,
            context=context,
            uuid=uuid,
            outputs=outputs,
        )

    destination_name = parameters['OUTPUT_VECTOR'].destinationName

    assert context.destination_project.count() == 1

    out = outputs.get('OUTPUT_VECTOR')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == destination_name

    # Get the layer
    srclayer = QgsProcessingUtils.mapLayerFromString('france_parts', context)
    assert srclayer is not None

    layers = context.destination_project.mapLayersByName(destination_name)
    assert len(layers) == 1
    output_layer = layers[0]
    assert output_layer.featureCount() == srclayer.featureCount()

    # check data url
    if Qgis.QGIS_VERSION_INT >=33800:
        server_properties = output_layer.serverProperties()
        assert server_properties.dataUrl() == get_expected_data_url(uuid, "OUTPUT_VECTOR.gpkg")
        assert server_properties.dataUrlFormat() == "text/plain"
    else:
        assert output_layer.dataUrl() == get_expected_data_url(uuid, "OUTPUT_VECTOR.gpkg")
        assert output_layer.dataUrlFormat() == "text/plain"


def test_output_vector_algorithm(outputdir, data):
    """ Test simple vector layer output
    """
    alg = _find_algorithm('pyqgiswps_test:vectoroutput')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['INPUT'][0].data = 'france_parts'
    inputs['DISTANCE'][0].data = 0.05

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert isinstance(parameters['DISTANCE'], float)

    context.wms_url = f"http://localhost/wms/?MAP=test/{alg.name()}.qgs"
    uuid = "uuid-france"
    # Run algorithm
    with chdir(outputdir):
        _results = run_algorithm(
            alg,
            parameters=parameters,
            feedback=feedback,
            context=context,
            uuid=uuid,
            outputs=outputs,
        )

    assert context.destination_project.count() == 1

    out = outputs.get('OUTPUT')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    output_name = 'my_output_vector'

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == output_name

    # Get the layer
    srclayer = QgsProcessingUtils.mapLayerFromString('france_parts', context)
    assert srclayer is not None

    layers = context.destination_project.mapLayersByName(output_name)
    assert len(layers) == 1
    output_layer = layers[0]
    assert output_layer.name() == 'my_output_vector'
    assert output_layer.featureCount() == srclayer.featureCount()

    # check data url
    if Qgis.QGIS_VERSION_INT >=33800:
        server_properties = output_layer.serverProperties()
        assert server_properties.dataUrl() == get_expected_data_url(uuid, f"{output_name}.shp")
        assert server_properties.dataUrlFormat() == "text/plain"
    else:
        assert output_layer.dataUrl() == get_expected_data_url(uuid, f"{output_name}.shp")
        assert output_layer.dataUrlFormat() == "text/plain"


def test_selectfeatures_algorithm(outputdir, data):
    """ Test simple layer output
    """
    alg = _find_algorithm('pyqgiswps_test:simplebuffer')

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['INPUT'][0].data = 'layer:france_parts?' + urlencode((('select', 'OBJECTID=2662 OR OBJECTID=2664'),))
    inputs['OUTPUT_VECTOR'][0].data = 'buffer'
    inputs['DISTANCE'][0].data = 0.05

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert isinstance(parameters['OUTPUT_VECTOR'], QgsProcessingOutputLayerDefinition)
    assert isinstance(parameters['DISTANCE'], float)

    context.wms_url = f"http://localhost/wms/?MAP=test/{alg.name()}.qgs"
    uuid = "uuid-select-12"
    # Run algorithm
    with chdir(outputdir):
        _results = run_algorithm(
            alg,
            parameters=parameters,
            feedback=feedback,
            context=context,
            uuid=uuid,
            outputs=outputs,
        )

    assert context.destination_project.count() == 1

    out = outputs.get('OUTPUT_VECTOR')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    destination_name = parameters['OUTPUT_VECTOR'].destinationName

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == destination_name

    # Get the layer
    layers = context.destination_project.mapLayersByName(destination_name)
    assert len(layers) == 1
    output_layer = layers[0]
    assert output_layer.featureCount() == 2

    # check data url
    if Qgis.QGIS_VERSION_INT >=33800:
        server_properties = output_layer.serverProperties()
        assert server_properties.dataUrl() == get_expected_data_url(uuid, "OUTPUT_VECTOR.gpkg")
        assert server_properties.dataUrlFormat() == "text/plain"
    else:
        assert output_layer.dataUrl() == get_expected_data_url(uuid, "OUTPUT_VECTOR.gpkg")
        assert output_layer.dataUrlFormat() == "text/plain"
