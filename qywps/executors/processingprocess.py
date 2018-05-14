""" Wrap qgis processing algorithms in WPS process
"""
import os
import logging
import mimetypes
import traceback

from urllib.parse import urlparse, urlencode

from functools import partial
from qywps.app.Common import Metadata
from qywps.exceptions import MissingParameterValue
from qywps.inout.formats import Format
from qywps.app.Process import Process as WPSProcess
from qywps.inout import (LiteralInput, 
                        ComplexInput,
                        BoundingBoxInput, 
                        LiteralOutput, 
                        ComplexOutput,
                        BoundingBoxOutput)

from qywps.inout.literaltypes import AnyValue, NoValue, ValuesReference, AllowedValue
from qywps.validator.allowed_value import ALLOWEDVALUETYPE

from qywps import configuration

from qgis.core import QgsApplication
from qgis.core import QgsProcessingException
from qgis.core import (QgsProcessing,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterNumber,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputHtml,
                       QgsProcessingOutputFile,
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputVectorLayer,
                       QgsProcessingParameterLimitedDataTypes,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterField,
                       QgsProcessingUtils,
                       QgsProcessingFeedback,
                       QgsReferencedRectangle,
                       QgsRectangle,
                       QgsMapLayer,
                       QgsWkbTypes,
                       QgsProperty,
                       QgsCoordinateReferenceSystem)

from qywps.executors.processingcontext import Context

from processing.core.Processing import (Processing, 
                                        ProcessingConfig,
                                        RenderingStyles)

LOGGER = logging.getLogger("QYWPS")

DESTINATION_LAYER_TYPES = (QgsProcessingParameterFeatureSink, 
                           QgsProcessingParameterVectorDestination, 
                           QgsProcessingParameterRasterDestination)

OUTPUT_LITERAL_TYPES = ("string","number","enum","number")
OUTPUT_LAYER_TYPES = ( QgsProcessingOutputVectorLayer, QgsProcessingOutputRasterLayer )

INPUT_LAYER_TYPES = ('source','layer','vector','raster','sink')

# Map processing source types to string
SourceTypes = {
    QgsProcessing.TypeMapLayer: 'TypeMapLayer',
    QgsProcessing.TypeVectorAnyGeometry : 'TypeVectorAnyGeometry',
    QgsProcessing.TypeVectorPoint : 'TypeVectorPoint',
    QgsProcessing.TypeVectorLine: 'TypeVectorLine',
    QgsProcessing.TypeVectorPolygon: 'TypeVectorPolygon',
    QgsProcessing.TypeRaster: 'TypeRaster', 
    QgsProcessing.TypeFile: 'TypeFile', 
    QgsProcessing.TypeVector: 'TypeVector', 
}


class ProcessingAlgorithmNotFound(Exception):
    pass

class ProcessingTypeParseError(Exception):
    pass

class ProcessingInputTypeNotSupported(ProcessingTypeParseError):
    pass

class ProcessingOutputTypeNotSupported(ProcessingTypeParseError):
    pass

class ProcessingAlgorithmError(Exception):
    pass


def _is_optional( param ):
    return (param.flags() & QgsProcessingParameterDefinition.FlagOptional) !=0


def _find_algorithm( algid ):
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().algorithmById( algid )
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


_generic_version="1.0a1"


def parse_literal_input( param, kwargs ):
    """ 
    """
    typ = param.type()

    if typ == 'string':
        kwargs['data_type'] = 'string'
    elif typ == 'boolean':
        kwargs['data_type'] = 'boolean'
    elif typ == 'enum':
        options = param.options()
        kwargs['data_type'] = 'string'
        kwargs['allowed_values'] = options
        if param.defaultValue() is not None:
            # XXX Values for processing enum are indices
            kwargs['default'] = options[param.defaultValue()]
    elif typ == 'number':
        kwargs['data_type'] = { QgsProcessingParameterNumber.Double :'float',
                                QgsProcessingParameterNumber.Integer:'integer' 
                               }[param.dataType()]
        kwargs['allowed_values'] = [(param.minimum(),param.maximum())]
    elif typ =='field':
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:parentLayerParameterName',
                param.parentLayerParameterName()))
        kwargs['metadata'].append(Metadata('processing:dataType',{
                QgsProcessingParameterField.Any: 'Any',
                QgsProcessingParameterField.Numeric: 'Numeric',
                QgsProcessingParameterField.String: 'String',
                QgsProcessingParameterField.DateTime: 'DateTime'
            }[param.dataType()]))
    elif typ =='crs':
        kwargs['data_type'] = 'string'
    elif typ == 'band':
        kwargs['data_type'] = 'nonNegativeInteger'
    else:
        return None

    return LiteralInput(**kwargs)


def parse_file_input( param, kwargs):
    """ Input is file
    """
    typ = param.type()
    if typ == 'file':
        if param.behavior() == QgsProcessingParameterFile.Folder:
            raise ProcessingInputTypeNotSupported('folder')
        ext = param.extension()
        if ext:
            mime = mimetypes.types_map.get(param.extension())
            if mime is not None:
                kwargs['supported_formats'] = [Format(mime)]
            kwargs['metadata'].append(Metadata('processing:extension',param.extension()))
        return ComplexInput(**kwargs)
    elif typ == 'fileDestination':
        extension = '.'+param.defaultFileExtension()
        # XXX File destination is name for a destination file
        # It does not make sense here to let the client choose 
        # the name of a file here so we just set a default value as string
        kwargs['data_type'] = 'string'
        kwargs['default']   = param.name()+extension
        kwargs['metadata'].append(Metadata('processing:format', mimetypes.types_map.get(extension,'')))
        kwargs['metadata'].append(Metadata('processing:mutable','no'))
        return LiteralInput(**kwargs)


def parse_layer_input(param, kwargs):
    """ Layers input are passe as layer name

        We treat layer destination the same as input since they refer to
        layers ids in qgisProject
    """
    typ = param.type()
    if typ in INPUT_LAYER_TYPES:
        kwargs['data_type'] = 'string'
    elif isinstance(param, QgsProcessingParameterRasterDestination):
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:extension',param.defaultFileExtension()))
    elif isinstance(param, QgsProcessingParameterVectorDestination):
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:dataType' , str(param.dataType())))
        kwargs['metadata'].append(Metadata('processing:extension', param.defaultFileExtension()))
    elif typ == 'multilayer':
        kwargs['data_type']  = 'string'
        kwargs['min_occurs'] = param.minimumNumberInputs()
        kwargs['max_occurs'] = 20
        kwargs['metadata'].append(Metadata('processing:layerType' , str(param.layerType())))
    else:
        return None

    if isinstance(param, QgsProcessingParameterLimitedDataTypes):
        kwargs['metadata'].append(Metadata('processing:dataTypes', ','.join(SourceTypes[typ] for typ in param.dataTypes())))

    return LiteralInput(**kwargs)


def parse_extent_input( param, kwargs ):
    """
    """
    typ = param.type()
    if typ == "extent":
       # XXX This is the default, do not presume anything
       # about effective crs at compute time
       kwargs['crss'] = ['EPSG:4326']
    else:
       return None
    
    return BoundingBoxInput(**kwargs)


def parse_input_definition( param, alg=None ):
    """ Create WPS input from QgsProcessingParamDefinition

        see https://qgis.org/api/qgsprocessingparameters_8h_source.html#l01312
    """
    kwargs = {
        'identifier': param.name() ,
        'title'     : param.description(),
        'abstract'  : param.description(),
        'default'   : param.defaultValue(),
        'metadata'  : [
            Metadata('processing:type',param.type()),
        ]
    }

    # Check for optional flags
    if _is_optional:
        kwargs['min_occurs'] = 0


    inp = parse_literal_input(param,kwargs)      \
            or parse_layer_input(param,kwargs)   \
            or parse_extent_input(param, kwargs) \
            or parse_file_input(param, kwargs)
    if inp is None:
        raise ProcessingInputTypeNotSupported("%s:'%s'" %(type(param),param.type()))

    return inp
    

def parse_literal_output( outdef, kwargs ):
    """
    """
    typ = outdef.type()
    if typ == 'outputString':
        kwargs['data_type'] = 'string'
    elif typ == 'outputNumber':
        kwargs['data_type'] = 'float'
    else:
        return None
 
    return LiteralOutput(**kwargs)


def parse_layer_output( outdef, kwargs ):
    """ Parse layer output

        A layer output is merged to a qgis project, we return 
        the wms uri associated to the project
    """
    if isinstance(outdef, OUTPUT_LAYER_TYPES ):
        return ComplexOutput(supported_formats=[Format("application/x-ogc-wms")], as_reference=True, **kwargs)


def parse_file_output( outdef, kwargs, alg=None ):
    """ Parse html output def
    """
    if isinstance(outdef, QgsProcessingOutputHtml):
        mime = mimetypes.types_map.get('.html')
        return ComplexOutput(supported_formats=[Format(mime)],**kwargs)
    elif isinstance(outdef, QgsProcessingOutputFile):
        # Try to get a corresponding inputFileDefinition
        mime = None
        if alg:
            inputdef = alg.parameterDefinition(outdef.name())
            if isinstance(inputdef, QgsProcessingParameterFileDestination):
                mime = mimetypes.types_map.get("."+inputdef.defaultFileExtension())
        if mime is None:
            LOGGER.warning("Cannot set file type for output %s", outdef.name())
            mime = "application/octet-stream"
        return ComplexOutput(supported_formats=[Format(mime)], **kwargs)


def parse_output_definition( outdef, alg=None ):
    """ Create WPS output

        XXX Create more QgsProcessingOutputDefinition for handling:
            - output matrix
            - output json vector
    """
    kwargs = {
        'identifier': outdef.name() ,
        'title'     : outdef.description(),
        'abstract'  : outdef.description(),
    }

    output = parse_literal_output( outdef, kwargs) \
            or parse_layer_output( outdef, kwargs )\
            or parse_file_output( outdef, kwargs, alg )
    if output is None:
        raise ProcessingOutputTypeNotSupported(outdef.type())

    return output 


def input_to_processing( identifier, inp, alg, context ):
    """ Convert wps input to processing param

        see https://qgis.org/api/classQgsProcessingOutputLayerDefinition.html
        see https://qgis.org/api/qgsprocessingparameters_8cpp_source.html#L272

        see ./python/plugins/processing/tools/general.py:111
        see ./python/plugins/processing/gui/Postprocessing.py:50
        see ./python/plugins/processing/core/Processing.py:126 
    """
    param = alg.parameterDefinition(identifier)

    typ = param.type()

    if isinstance(param, DESTINATION_LAYER_TYPES):
        # Do not supports memory: layer since we are storing destination project to file
        param.setSupportsNonFileBasedOutputs(False)
        # Enforce pushing created layers to layersToLoadOnCompletion list
        if param.defaultFileExtension():
            sink = "./%s.%s" % (param.name(), param.defaultFileExtension())
        else:
            # No file extension defined: we assume to use a stored layer
            sink = "%s_%s" % (param.name(), alg.name())
        value = QgsProcessingOutputLayerDefinition(sink, context.destination_project)
        value.destinationName = inp[0].data
    elif typ == 'enum':
        # XXX Processing wants the index of the value in option list
        value = param.options().index(inp[0].data)  
    elif typ == 'extent':
        r = inp[0].data
        rect  = QgsRectangle(r[0],r[2],r[1],r[3])
        ref   = QgsCoordinateReferenceSystem(inp.crs)
        value = QgsReferencedRectangle(rect, ref)
    elif typ == 'crs':
        # XXX CRS may be expressed as EPSG (or QgsProperty ?)
        value = inp[0].data
    elif typ == 'fileDestination':
        # Coerce with the the default value (see above) as we do not let client set
        # output file name
        if inp[0].data != inp[0].default:
            LOGGER.warning("Dropping modified value for fileDestination")
        value = inp[0].default
    elif len(inp):
        # Return raw value
        value = inp[0].data
    else:
        # Return undefined value
        if not _is_optional(param): 
            LOGGER.warning("Required input %s has no value", identifier) 
        value = None
    
    return param.name(), value


def format_output_url( response, file_name ):
    """ Build output/store url for output file name
    """
    outputurl = configuration.get_config('server')['outputurl']
    return outputurl.format(
                host_url = response.wps_request.host_url,
                uuid     = response.uuid,
                file     = file_name)


def to_output_file( file_name, out, context ):
    """ Output file
    """
    if out.as_reference:
        out.url = format_output_url(context.response, file_name)
    else:
        out.file = os.path.join(context.workdir,file_name)

    return out


def processing_to_output( value, outdef, out, output_uri, context=None ):
    """ Map processing output to WPS
    """
    if isinstance(outdef, OUTPUT_LAYER_TYPES):
        out.output_format = "application/x-ogc-wms"
        out.url = output_uri + '&' + urlencode((('layer',value),))
    elif isinstance(outdef, QgsProcessingOutputHtml):
        out.output_format = mimetypes.types_map['.html']
        return to_output_file( value, out, context )
    elif isinstance(outdef, QgsProcessingOutputFile):
        _, sfx = os.path.splitext(value)
        out.output_format = mimetypes.types_map[sfx]
        return to_output_file( value, out, context )
    else:
        # Return raw value
        out.data = value


def handle_algorithm_results(alg, context, feedback, **kwargs):
    """ Handle algorithms result layeri
    
        Insert result layers into destination project
    """
    wrongLayers = []
    for l, details in context.layersToLoadOnCompletion().items():
        if feedback.isCanceled():
            return False
        try:
            # Take as layer
            layer = QgsProcessingUtils.mapLayerFromString(l, context)
            if layer is not None:
                if not ProcessingConfig.getSetting(ProcessingConfig.USE_FILENAME_AS_LAYER_NAME):
                    layer.setName(details.name)
                # Set styles
                style = None
                if details.outputName:
                    style = RenderingStyles.getStyle(alg.id(), details.outputName)
                if style is None:
                    if layer.type() == QgsMapLayer.RasterLayer:
                        style = ProcessingConfig.getSetting(ProcessingConfig.RASTER_STYLE)
                    else:
                        if layer.geometryType() == QgsWkbTypes.PointGeometry:
                            style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_POINT_STYLE)
                        elif layer.geometryType() == QgsWkbTypes.LineGeometry:
                            style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_LINE_STYLE)
                        else:
                            style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_POLYGON_STYLE)
                if style:
                    layer.loadNamedStyle(style)
                # Add layer to destination project
                details.project.addMapLayer(context.temporaryLayerStore().takeMapLayer(layer))
            else:
                LOGGER.warn("No layer found found for %s" % l)
        except Exception:
            LOGGER.error("Processing: Error loading result layer:\n{}".format(traceback.print_exc()))
            wrongLayers.append(str(l))

    if wrongLayers:
        msg = "The following layers were not correctly generated:"
        msg += "\n".join("%s" % lay for lay in wrongLayers)
        msg += "You can check the log messages to find more information about the execution of the algorithm"
        feedback.reportError(msg)

    return len(wrongLayers) == 0


class Feedback(QgsProcessingFeedback):
    """ Handle processing proggress messages

        This is a wrapper around WPS status
    """

    def __init__(self, response, name, uuid_str ):
        super().__init__()
        self._response  = response
        self.name       = name
        self.uuid       = uuid_str
        self.has_error  = False

    def setProgress( self, progress ):
        """ We update the wps status 
        """
        self._response.update_status(status_percentage=int(progress+0.5))

    def setProgressText( self, message ):
        self._response.update_status(message=message)

    def cancel(self):
        """ Notify that job is cancelled
        """
        LOGGER.warning("Processing:%s:%s cancel() called", self.name, self.uuid)
        super(Feedback, self).cancel()
        # TODO Call update status  when 
        # https://projects.3liz.org/infra-v3/py-qgis-wps/issues/1 is fixed

    def reportError(self, txt ):
        LOGGER.error("Processing:%s:%s %s", self.name, self.uuid, txt)
        self.error_msg = txt
        self.has_error = True

    def pushInfo(self, txt):
        LOGGER.info("Processing:%s:%s %s",self.name, self.uuid, txt)

    def pushDebugInfo(self, txt):
        LOGGER.debug("Processing:%s:%s %s",self.name, self.uuid, txt)




def handle_layer_outputs(alg, results, context ):
    """
    """
    # Validate outputs
    # Replace outputs by the layer names
    for l, details in context.layersToLoadOnCompletion().items():
        if details.outputName in results:
            results[details.outputName] = details.name


def write_outputs( alg, results, outputs, output_uri=None,  context=None ):
    """ Set wps outputs and write project 
    """
    for outdef in alg.outputDefinitions():
        out = outputs.get(outdef.name())
        if out:
            processing_to_output(results[outdef.name()], outdef, out, output_uri, context)

    if context is not None:
        context.write_result(context.workdir, alg.name())


class QgsProcess(WPSProcess):

    def __init__(self, algorithm ):

        alg = _find_algorithm( algorithm ) if isinstance(algorithm, str) else algorithm

        def _parse( parser, alg, defs ):
            for param in defs:
                try:
                    yield parser(param, alg)
                except ProcessingTypeParseError as e:
                    LOGGER.error("%s: unsupported param %s",alg.id(),e) 

        # Create input/output
        inputs  = list(_parse(parse_input_definition, alg, alg.parameterDefinitions()))
        outputs = list(_parse(parse_output_definition, alg, alg.outputDefinitions()))

        self.map_required = any(p.type() in INPUT_LAYER_TYPES for p in alg.parameterDefinitions())

        super().__init__(QgsProcess._handler,
                identifier = alg.id(),
                version    = _generic_version,
                title      = alg.displayName(),
                abstract   = alg.shortHelpString(),
                inputs     = inputs,
                outputs    = outputs)
   
    def check( self, request ):
        """ Check request parameters
        """
        if self.map_required and request.map_uri is None:
            raise MissingParameterValue("Missing 'map' parameter", 'process')

    @staticmethod
    def _handler( request, response ):
        """  WPS process handler
        """

        LOGGER.debug("Starting task %s", request.identifier) 

        alg = QgsApplication.processingRegistry().createAlgorithmById(request.identifier)

        workdir  = response.process.workdir
        context  = Context(workdir, map_uri=request.map_uri)
        feedback = Feedback(response, alg.name(), uuid_str=str(response.uuid)) 

        context.setFeedback(feedback)

        # Convert parameters from WPS inputs
        parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in request.inputs.items() )

        try:
            results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=handle_algorithm_results,
                                              feedback=feedback, context=context)
        except QgsProcessingException as e:
            traceback.print_exc()
            raise ProcessingAlgorithmError("%s" % e)

        # Handle error 
        if feedback.has_error:
            LOGGER.error(feedback.error_msg)
            raise ProcessingAlgorithmError(feedback.error_msg)

        handle_layer_outputs(alg, results, context)

        # Get WMS output uri
        output_uri = configuration.get_config('server')['wms_response_uri'].format(
                            host_url=request.host_url,
                            uuid=response.uuid,
                            name=alg.name())

        context.response = response
        write_outputs( alg, results, response.outputs, output_uri, context)
        
        return response

    def clean(self):
        """ Override default

            We use the workdir as our final output dir
            The cleanup policy is driven by the request expiration time
        """
        pass

