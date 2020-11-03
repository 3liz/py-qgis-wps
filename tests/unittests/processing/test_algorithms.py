""" Test parsing processing itputs to WPS inputs
"""
import os
from urllib.parse import urlparse, parse_qs, urlencode

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


def test_provider(): 
    registry = QgsApplication.processingRegistry()
    provider = registry.providerById('pyqgiswps_test')
    assert provider is not None
    assert provider.id() == 'pyqgiswps_test'
    assert len(provider.algorithms()) > 0
    assert registry.algorithmById('pyqgiswps_test:testsimplevalue') is not None, 'pyqgiswps_test:testsimplevalue' 
    assert registry.algorithmById('pyqgiswps_test:testcopylayer') is not None,   'pyqgiswps_test:testcopylayer'


def test_simple_algorithms():
    """ Execute a simple algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testsimplevalue')

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
    results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context, outputs=outputs, output_uri="")   

    assert results['OUTPUT'] == "1 stuff"
    assert outputs['OUTPUT'].data == "1 stuff"
    

def test_option_algorithms():
    """ Execute a simple choice  algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testoptionvalue')

    context  = QgsProcessingContext()
    feedback = QgsProcessingFeedback() 

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
    
    inputs['INPUT'][0].data = 'value1'

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert parameters['INPUT'] == 0

    # Run algorithm
    results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context, outputs=outputs, output_uri="")   
    
    assert results['OUTPUT'] == 'selection is 0'
    assert outputs['OUTPUT'].data == "selection is 0"


def test_option_multi_algorithms():
    """ Execute a multiple choice  algorithm
    """
    alg = _find_algorithm('pyqgiswps_test:testmultioptionvalue')

    context  = QgsProcessingContext()
    feedback = QgsProcessingFeedback() 

    inputs  = { p.name(): parse_input_definition(p)  for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
    
    source = inputs['INPUT']
    inputs['INPUT'] = [source.clone(),source.clone()]
    inputs['INPUT'][0].data = 'value1'
    inputs['INPUT'][1].data = 'value3'

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert parameters['INPUT'] == [0,2]

    # Run algorithm
    results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context, outputs=outputs, output_uri="")   

    assert results['OUTPUT'] == 'selection is 0,2'
    assert outputs['OUTPUT'].data == "selection is 0,2"


def test_layer_algorithm(outputdir, data):
    """ Copy layer 
    """
    alg = _find_algorithm('pyqgiswps_test:testcopylayer')

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

    destination = get_valid_filename(alg.id())

    assert isinstance( parameters['OUTPUT'], QgsProcessingOutputLayerDefinition)

    output_uri = "http://localhost/wms/MAP=test/{name}.qgs".format(name=destination)

    # Run algorithm
    with chdir(outputdir.strpath):
        results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context, outputs=outputs, output_uri=output_uri)   
   
    destination_name = parameters['OUTPUT'].destinationName
    assert context.destination_project.count() == 1

def test_buffer_algorithm(outputdir, data):
    """ Test simple layer output 
    """
    alg = _find_algorithm('pyqgiswps_test:simplebuffer')

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
   
    inputs['INPUT'][0].data = 'france_parts'
    inputs['OUTPUT_VECTOR'][0].data = 'buffer'
    inputs['DISTANCE'][0].data = 0.05

    # Load source project
    source      = QgsProject()
    rv = source.read(data.join('france_parts.qgs').strpath)
    assert rv == True

    workdir = outputdir.strpath

    context  = Context(source, workdir)
    feedback = QgsProcessingFeedback() 

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert isinstance( parameters['OUTPUT_VECTOR'], QgsProcessingOutputLayerDefinition)
    assert isinstance( parameters['DISTANCE'], float)

    output_uri = "http://localhost/wms/?MAP=test/{name}.qgs".format(name=alg.name())
    # Run algorithm
    with chdir(outputdir.strpath):
        results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context, outputs=outputs, output_uri=output_uri)   
   
    destination_name = parameters['OUTPUT_VECTOR'].destinationName

    assert context.destination_project.count() == 1

    out = outputs.get('OUTPUT_VECTOR')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == destination_name

    # Get the layer 
    srclayer = QgsProcessingUtils.mapLayerFromString('france_parts', context)
    assert srclayer is not None

    layers  = context.destination_project.mapLayersByName(destination_name)
    assert len(layers) == 1
    assert layers[0].featureCount() == srclayer.featureCount()


def test_output_vector_algorithm(outputdir, data):
    """ Test simple vector layer output 
    """
    alg = _find_algorithm('pyqgiswps_test:vectoroutput')

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
   
    inputs['INPUT'][0].data = 'france_parts'
    inputs['DISTANCE'][0].data = 0.05

    # Load source project
    source = QgsProject()
    rv = source.read(data.join('france_parts.qgs').strpath)
    assert rv == True

    workdir = outputdir.strpath

    context  = Context(source, workdir)
    feedback = QgsProcessingFeedback() 

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert isinstance( parameters['DISTANCE'], float)

    output_uri = "http://localhost/wms/?MAP=test/{name}.qgs".format(name=alg.name())
    # Run algorithm
    with chdir(outputdir.strpath):
        results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context,outputs=outputs, output_uri=output_uri)   
    
    assert context.destination_project.count() == 1

    out = outputs.get('OUTPUT')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    output_name = 'my_output_vector'
    
    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == output_name

    # Get the layer 
    srclayer = QgsProcessingUtils.mapLayerFromString('france_parts', context)
    assert srclayer is not None

    layers  = context.destination_project.mapLayersByName(output_name)
    assert len(layers) == 1
    assert layers[0].name() == 'my_output_vector'
    assert layers[0].featureCount() == srclayer.featureCount()



def test_selectfeatures_algorithm(outputdir, data):
    """ Test simple layer output 
    """
    alg = _find_algorithm('pyqgiswps_test:simplebuffer')

    inputs  = { p.name(): [parse_input_definition(p)] for p in  alg.parameterDefinitions() }
    outputs = { p.name(): parse_output_definition(p) for p in  alg.outputDefinitions() }
   
    inputs['INPUT'][0].data = 'layer:france_parts?'+urlencode((('select','OBJECTID=2662 OR OBJECTID=2664'),))
    inputs['OUTPUT_VECTOR'][0].data = 'buffer'
    inputs['DISTANCE'][0].data = 0.05

    # Load source project
    source      = QgsProject()
    rv = source.read(data.join('france_parts.qgs').strpath)
    assert rv == True

    workdir = outputdir.strpath

    context  = Context(source, workdir)
    feedback = QgsProcessingFeedback() 

    parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in inputs.items() )  

    assert isinstance( parameters['OUTPUT_VECTOR'], QgsProcessingOutputLayerDefinition)
    assert isinstance( parameters['DISTANCE'], float)

    output_uri = "http://localhost/wms/?MAP=test/{name}.qgs".format(name=alg.name())
    # Run algorithm
    with chdir(outputdir.strpath):
        results = run_algorithm(alg, parameters=parameters, feedback=feedback, context=context, outputs=outputs, output_uri=output_uri)   
    
    assert context.destination_project.count() == 1

    out = outputs.get('OUTPUT_VECTOR')
    assert out.data_format.mime_type == "application/x-ogc-wms"

    destination_name = parameters['OUTPUT_VECTOR'].destinationName

    query = parse_qs(urlparse(out.url).query)
    assert query['layers'][0] == destination_name

    # Get the layer 
    layers = context.destination_project.mapLayersByName(destination_name)
    assert len(layers) == 1
    assert layers[0].featureCount() == 2


