""" Test parsing processing itputs to WPS inputs
"""
import os

from os import PathLike
from typing import Tuple
from urllib.parse import parse_qs, urlparse

from qgis.core import (
    Qgis,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputLayerDefinition,
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

    confservice.set('wps.request', 'host_url', 'http://localhost/test-models/')

    def __init__(self, project: QgsProject, workdir: PathLike) -> None:
        super().__init__()
        self.workdir = str(workdir)
        self.setProject(project)

        # Create the destination project
        self.destination_project = QgsProject()

    def write_result(self, workdir: str, name: str) -> Tuple[bool, str]:
        """ Save results to disk
        """
        name = get_valid_filename(name)
        return self.destination_project.write(os.path.join(workdir, name + '.qgs')), name


def test_centroides_algorithms(outputdir, data):
    """ Execute an algorithm from a model
    """
    alg = _find_algorithm('model:centroides')

    # Load source project
    source = QgsProject()
    rv = source.read(str(data / 'france_parts.qgs'))
    assert rv

    context = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    inputs = {p.name(): [parse_input_definition(p)] for p in alg.parameterDefinitions()}
    outputs = {p.name(): parse_output_definition(p) for p in alg.outputDefinitions()}

    inputs['input'][0].data = 'france_parts'
    inputs['native:centroids_1:OUTPUT'][0].data = 'output_layer'

    parameters = dict(input_to_processing(ident, inp, alg, context) for ident, inp in inputs.items())

    assert isinstance(parameters['native:centroids_1:OUTPUT'], QgsProcessingOutputLayerDefinition)

    destination_name = parameters['native:centroids_1:OUTPUT'].destinationName
    assert destination_name == 'output_layer'

    # Destination project
    destination_project = get_valid_filename(alg.id())

    context.wms_url = f"http://localhost/wms/?MAP=test/{destination_project}.qgs"
    uuid = "uuid-model"
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

    out = outputs.get('native:centroids_1:OUTPUT')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == destination_name

    # Get the layer
    layers = context.destination_project.mapLayersByName(destination_name)
    assert len(layers) == 1

    host_url = confservice.get('wps.request', 'host_url').rstrip("/")
    expected_data_url = f"{host_url}/jobs/{uuid}/files/native_centroids_1_OUTPUT.gpkg"
    if Qgis.QGIS_VERSION_INT >= 33800:
        server_properties = layers[0].serverProperties()
        assert server_properties.dataUrl() == expected_data_url
        assert server_properties.dataUrlFormat() == "text/plain"
    else:
        assert layers[0].dataUrl() == expected_data_url
        assert layers[0].dataUrlFormat() == "text/plain"
