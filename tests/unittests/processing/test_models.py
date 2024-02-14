""" Test parsing processing itputs to WPS inputs
"""
import os
from os import PathLike
from urllib.parse import urlparse, parse_qs, urlencode

from typing import Tuple

from pyqgiswps.utils.contexts import chdir
from pyqgiswps.utils.filecache import get_valid_filename

from pyqgiswps.inout import (LiteralInput,
                        ComplexInput,
                        BoundingBoxInput,
                        LiteralOutput,
                        ComplexOutput,
                        BoundingBoxOutput)

from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE
from pyqgiswps.executors.processingio import(
            parse_input_definition,
            parse_output_definition,
            input_to_processing,
            processing_to_output,
        )

from pyqgiswps.executors.processingprocess import(
            run_algorithm,
            _find_algorithm)

from qgis.core import QgsApplication
from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputHtml,
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputVectorLayer,
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


class Context(QgsProcessingContext):

    def __init__(self, project: QgsProject, workdir: PathLike ) -> None:
        super().__init__()
        self.workdir = str(workdir)
        self.setProject(project)

        # Create the destination project
        self.destination_project = QgsProject()

    def write_result(self, workdir:str , name:str) -> Tuple[bool,str]:
        """ Save results to disk
        """
        name = get_valid_filename(name)
        return self.destination_project.write(os.path.join(workdir,name+'.qgs')), name


def test_centroides_algorithms(outputdir, data):
    """ Execute an algorithm from a model
    """
    alg = _find_algorithm('model:centroides')

    # Load source project
    source      = QgsProject()
    rv = source.read(str(data/'france_parts.qgs'))
    assert rv == True

    context  = Context(source, outputdir)
    feedback = QgsProcessingFeedback()

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }

    inputs['input'][0].data = 'france_parts'
    inputs['native:centroids_1:OUTPUT'][0].data = 'output_layer'

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )

    assert isinstance( parameters['native:centroids_1:OUTPUT'], QgsProcessingOutputLayerDefinition)

    destination_name = parameters['native:centroids_1:OUTPUT'].destinationName
    assert destination_name == 'output_layer'

    # Destination project
    destination_project = get_valid_filename(alg.id())

    context.wms_url = f"http://localhost/wms/?MAP=test/{destination_project}.qgs"
    # Run algorithm
    with chdir(outputdir):
        results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context,
                                outputs=outputs)

    assert context.destination_project.count() == 1

    out = outputs.get('native:centroids_1:OUTPUT')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == destination_name

    # Get the layer
    layers = context.destination_project.mapLayersByName(destination_name)
    assert len(layers) == 1
