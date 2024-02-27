""" Test parsing processing itputs to WPS inputs
"""
import os
from urllib.parse import urlparse, parse_qs, urlencode
#from pyqgiswps.utils.qgis import setup_qgis_paths
#setup_qgis_paths()

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
            _find_algorithm,
        )

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
                       QgsProject,
                       QgsMapLayer)

from processing.core.Processing import Processing

from pyqgiswps.executors.processingprocess import MapContext, ProcessingContext


def test_context(outputdir, data):
    """ Context with Copy layer
    """
    alg = _find_algorithm('pyqgiswps_test:testcopylayer')

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }

    inputs['INPUT'][0].data = 'france_parts'
    inputs['OUTPUT'][0].data = 'france_parts_2'

    context  = ProcessingContext(str(outputdir), 'france_parts.qgs')
    feedback = QgsProcessingFeedback()

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )

    assert isinstance( parameters['OUTPUT'], QgsProcessingOutputLayerDefinition)

    destination = get_valid_filename(alg.id())

    context.wms_url = f"http://localhost/wms/MAP=test/{destination}.qgs"
    # Run algorithm
    with chdir(outputdir):
        results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context,
                                uuid="uuid", outputs=outputs)

    assert context.destination_project.count() == 1

    # Save destination project
    ok = context.write_result(context.workdir, destination)

    assert ok
    assert context.destination_project.fileName() == str(outputdir/(destination+'.qgs'))

    # WFS configuration inserted
    WFSLayers = context.destination_project.readListEntry('WFSLayers', '/')[0]
    assert len(WFSLayers) != 0

    # All Vector Layers has been published in WFS
    mapLayers = context.destination_project.mapLayers()
    assert len(WFSLayers) == len([lid for lid,lyr in mapLayers.items() if lyr.type() == QgsMapLayer.VectorLayer])

    # Verifying th WFS configuration
    for lid in WFSLayers:
        lyr = context.destination_project.mapLayer(lid)
        # Is the WFS layer id references a Map Layer
        assert lyr
        # Is the WFS layer id references a Vector Layer
        assert lyr.type() == QgsMapLayer.VectorLayer
        # The WFS layer precision is defined
        assert context.destination_project.readNumEntry("WFSLayersPrecision", "/"+lid)[0] == 6


def test_get_project_file(outputdir, data):
    """ Test we can get a project file
    """
    context  = ProcessingContext(str(outputdir), 'france_parts.qgs')

    # Fetch a file from rootdir
    path = context.resolve_path("france_parts/france_parts.shp")

    assert path.is_file()


def test_get_project_folder(outputdir, data):
    """ Test we can get a project folder
    """
    context = ProcessingContext(str(outputdir), 'france_parts.qgs')

    # Fetch a file from rootdir
    path = context.resolve_path("france_parts")

    assert path.is_dir()


def test_map_vector_context(outputdir, data):
    """ Test map context return allowed layers
    """
    alg = _find_algorithm('pyqgiswps_test:testcopylayer')
    context = MapContext('france_parts.qgs')
    inputs  = { p.name(): [parse_input_definition(p,alg,context)] for p in  alg.parameterDefinitions() }

    layers = { l.name() for l in context.project().mapLayers().values() if l.type() == QgsMapLayer.VectorLayer }

    allowed_values = { value for value in inputs['INPUT'][0].allowed_values.values }

    assert len(allowed_values) == len(layers)
    assert allowed_values == layers


def test_map_raster_context(outputdir, data):
    """ Test map context return allowed layers
    """
    alg = _find_algorithm('pyqgiswps_test:testinputrasterlayer')
    context = MapContext('raster_layer.qgs')
    inputs  = { p.name(): [parse_input_definition(p,alg,context)] for p in  alg.parameterDefinitions() }

    layers = { l.name() for l in context.project().mapLayers().values() if l.type() == QgsMapLayer.RasterLayer }

    allowed_values = { value for value in inputs['INPUT'][0].allowed_values.values }

    assert len(allowed_values) == len(layers)
    assert allowed_values == layers


def test_multilayer_context(outputdir, data):
    """ Test map context return allowed layers
    """
    alg = _find_algorithm('pyqgiswps_test:testinputmultilayer')
    context = MapContext('france_parts.qgs')
    inputs  = { p.name(): [parse_input_definition(p,alg,context)] for p in  alg.parameterDefinitions() }

    layers = { l.name() for l in context.project().mapLayers().values() }

    allowed_values = { value for value in inputs['INPUT'][0].allowed_values.values }

    assert len(allowed_values) == len(layers)
    assert allowed_values == layers


def test_context_crs(outputdir, data):
    """ Test crs
    """
    context = ProcessingContext(str(outputdir), 'france_parts.qgs')

    crs_1 = context.project().crs()
    crs_2 = context.destination_project.crs()
    assert crs_1 == crs_2


def test_context_crs_default(outputdir, data):
    """ Test default crs
    """
    context = ProcessingContext(str(outputdir),None)

    crs = context.destination_project.crs()
    assert crs.isValid()
