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

    def __init__(self, project, workdir):
        super().__init__()
        self.workdir = workdir
        self.setProject(project)

        # Create the destination project
        self.destination_project = QgsProject()

    def write_result(self, workdir, name):
        """ Save results to disk
        """
        return self.destination_project.write(os.path.join(workdir,name+'.qgs'))


def test_provider(application): 
    registry = application.processingRegistry()
    provider = registry.providerById('qywps_test')
    assert provider is not None
    assert provider.id() == 'qywps_test'
    assert len(provider.algorithms()) > 0
    assert registry.algorithmById('qywps_test:testsimplevalue') is not None, 'qywps_test:testsimplevalue' 
    assert registry.algorithmById('qywps_test:testcopylayer') is not None,   'qywps_test:testcopylayer'


def test_simple_algorithms(application):
    """ Execute a simple algorithm
    """
    alg = _find_algorithm('qywps_test:testsimplevalue')

    context  = QgsProcessingContext()
    feedback = QgsProcessingFeedback() 

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
    
    inputs['PARAM1'][0].data = '1'
    inputs['PARAM2'][0].data = 'stuff'

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert parameters['PARAM1'] == 1
    assert parameters['PARAM2'] == 'stuff'

    # Run algorithm
    results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=handle_algorithm_results,
                                      feedback=feedback, context=context)   

    assert results['OUTPUT'] == "1 stuff"

    write_outputs( alg, results, outputs )

    assert outputs['OUTPUT'].data == "1 stuff"


def test_option_algorithms(application):
    """ Execute a simple choice  algorithm
    """
    alg = _find_algorithm('qywps_test:testoptionvalue')

    context  = QgsProcessingContext()
    feedback = QgsProcessingFeedback() 

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
    
    inputs['INPUT'][0].data = 'value1'

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert parameters['INPUT'] == 0

    # Run algorithm
    results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=handle_algorithm_results,
                                      feedback=feedback, context=context)   

    assert results['OUTPUT'] == 'selection is 0'

    write_outputs( alg, results, outputs )

    assert outputs['OUTPUT'].data == "selection is 0"



def test_layer_algorithm(application, outputdir, data):
    """ Copy layer 
    """
    alg = _find_algorithm('qywps_test:testcopylayer')

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
   
    inputs['INPUT'][0].data = 'france_parts'
    inputs['OUTPUT'][0].data = 'france_parts_2'

    # Load source project
    source      = QgsProject()
    rv = source.read(data.join('france_parts.qgs').strpath)
    assert rv == True

    workdir = outputdir.strpath

    context  = Context(source, workdir)
    feedback = QgsProcessingFeedback() 

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert isinstance( parameters['OUTPUT'], QgsProcessingOutputLayerDefinition)

    # Run algorithm
    with chdir(outputdir.strpath):
        results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=handle_algorithm_results,
                                          feedback=feedback, context=context)   
    
    assert context.destination_project.count() == 1

    handle_layer_outputs(alg, results, context)
    assert results['OUTPUT'] == parameters['OUTPUT'].destinationName

    output_uri = "http://localhost/wms/MAP=test/{name}.qgs".format(name=alg.name())

    write_outputs( alg, results, outputs, output_uri, context )



