#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Wrap qgis processing algorithms in WPS process
"""
import os
import logging
import mimetypes
import traceback

from functools import partial

from os.path import normpath, basename
from urllib.parse import urlparse, urlencode, parse_qs

from functools import partial
from qywps.app.Common import Metadata
from qywps.exceptions import (NoApplicableCode,
                              InvalidParameterValue,
                              MissingParameterValue,
                              ProcessException)

from qywps.inout.formats import Format
from qywps.app.Process import WPSProcess
from qywps.inout import (LiteralInput,
                        ComplexInput,
                        BoundingBoxInput,
                        LiteralOutput,
                        ComplexOutput,
                        BoundingBoxOutput)

from qywps.inout.literaltypes import AnyValue, NoValue, ValuesReference, AllowedValue
from qywps.validator.allowed_value import ALLOWEDVALUETYPE

from qywps import configuration

from qgis.PyQt.QtCore import QVariant

from qgis.core import QgsApplication
from qgis.core import QgsProcessingException
from qgis.core import (QgsProcessing,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterNumber,
                       QgsProcessingFeatureSourceDefinition,
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
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingUtils,
                       QgsProcessingFeedback,
                       QgsReferencedRectangle,
                       QgsRectangle,
                       QgsMapLayer,
                       QgsVectorLayer,
                       QgsWkbTypes,
                       QgsProperty,
                       QgsCoordinateReferenceSystem,
                       QgsFeatureRequest)


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

INPUT_LAYER_TYPES = ('source','layer','vector','raster')

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


def _is_optional( param ):
    return (int(param.flags()) & QgsProcessingParameterDefinition.FlagOptional) !=0


def _find_algorithm( algid ):
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().algorithmById( algid )
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


def _create_algorithm( algid, **context ):
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().createAlgorithmById( algid, context )
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


_generic_version="1.0generic"


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
        kwargs['max_occurs'] = len(options) if param.allowMultiple() else 1
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
            kwargs['data_type'] = 'string'
            return LiteralInput(**kwargs)
        ext = param.extension()
        if ext:
            mime = mimetypes.types_map.get(param.extension())
            if mime is not None:
                kwargs['supported_formats'] = [Format(mime)]
            kwargs['metadata'].append(Metadata('processing:extension',param.extension()))
        return ComplexInput(**kwargs)
    elif typ == 'fileDestination':
        extension = '.'+param.defaultFileExtension()
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:format', mimetypes.types_map.get(extension,'')))
        return LiteralInput(**kwargs)
    elif typ == 'folderDestination':
        kwargs['data_type'] = 'string'
        return LiteralInput(**kwargs)

def parse_metadata( param, kwargs ):
    """ Parse freeform metadata
    """
    kwargs['metadata'].extend(Metadata('processing:meta:%s' % k, str(v)) for k,v in param.metadata().items())


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
    elif isinstance(param, (QgsProcessingParameterVectorDestination, QgsProcessingParameterFeatureSink)):
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
        'metadata'  : [
            Metadata('processing:type',param.type()),
        ]
    }

    # Handle defaultValue
    # XXX In some case QVariant are 
    # not converted to python object (SIP bug ?)
    # Problem stated in getting QgsProcessingParameterFeatureSource
    # from processing.core.parameters.getParameterFromString
    defaultValue = param.defaultValue()
    if isinstance(defaultValue, QVariant):
        defaultValue = None if defaultValue.isNull() else defaultValue.value()

    kwargs['default'] = defaultValue

    # Check for optional flags
    if _is_optional(param):
        kwargs['min_occurs'] = 0

    inp = parse_literal_input(param,kwargs)      \
            or parse_layer_input(param,kwargs)   \
            or parse_extent_input(param, kwargs) \
            or parse_file_input(param, kwargs)
    if inp is None:
        raise ProcessingInputTypeNotSupported("%s:'%s'" %(type(param),param.type()))

    parse_metadata(param, kwargs)

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
        if isinstance(outdef, QgsProcessingOutputVectorLayer):
            return ComplexOutput(supported_formats=[
                        Format("application/x-ogc-wms"),
                        Format("application/x-ogc-wfs")
                    ], as_reference=True, **kwargs)
        elif isinstance(outdef, QgsProcessingOutputRasterLayer):
            return ComplexOutput(supported_formats=[
                        Format("application/x-ogc-wms"),
                        Format("application/x-ogc-wcs")
                    ], as_reference=True, **kwargs)
        else:
            return ComplexOutput(supported_formats=[Format("application/x-ogc-wms")], 
                                 as_reference=True, **kwargs)


def parse_file_output( outdef, kwargs, alg=None ):
    """ Parse file output def
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


def parse_layer_spec( layerspec, context, allow_selection=False ):
    """ Parse a layer specification

        if allow_selection is set to True: 'select' parameter
        is interpreted has holding a qgis feature request expression

        :return: A tuple (path, query)
    """
    u = urlparse(layerspec)
    p = u.path
    if u.scheme == 'file':
        p = context.resolve_path(p)
    elif u.scheme and u.scheme != 'layer':
        raise InvalidParameterValue("Bad scheme: %s" % layerspec)

    if not allow_selection:
        return p, False

    has_selection = False
    qs = parse_qs(u.query)
    feat_requests = qs.get('select',[])
    feat_rects    = qs.get('rect',[])
    if feat_rects or feat_requests:
        has_selection = True
        layer = context.getMapLayer(p)
        if not layer:
            LOGGER.error("No layer path for url %s", u)
            raise InvalidParameterValue("No layer '%s' found" % u.path, )

        if layer.type() != QgsMapLayer.VectorLayer:
            LOGGER.warning("Can apply selection only to vector layer")
        else:
            behavior = QgsVectorLayer.SetSelection
            try:
                LOGGER.debug("Applying features selection: %s", qs)
                # Apply filter rect first
                if feat_rects:
                    rect = QgsRectangle(feat_rects[-1].split(',')[:4])
                    layer.selectByRect(rect, behavior=behavior)
                    behavior = QgsVectorLayer.IntersectSelection
                # Selection by expressions
                if feat_requests:
                    ftreq = feat_requests[-1]
                    layer.selectByExpression(ftreq, behavior=behavior )
            except:
                LOGGER.error(traceback.format_exc())
                raise NoApplicableCode("Feature selection failed")
    return p, has_selection


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
        param.setSupportsNonFileBasedOutput(False)
        # Enforce pushing created layers to layersToLoadOnCompletion list
        if param.defaultFileExtension():
            sink = "./%s.%s" % (param.name(), param.defaultFileExtension())
        else:
            # No file extension defined: we assume to use a stored layer
            sink = "%s_%s" % (param.name(), alg.name())
        value = QgsProcessingOutputLayerDefinition(sink, context.destination_project)
        value.destinationName = inp[0].data

    elif isinstance(param, QgsProcessingParameterFeatureSource):
        # Support feature selection
        value, has_selection = parse_layer_spec(inp[0].data, context, allow_selection=True)
        value = QgsProcessingFeatureSourceDefinition(value, selectedFeaturesOnly=has_selection)

    elif typ in INPUT_LAYER_TYPES:
        value, _ = parse_layer_spec(inp[0].data, context)

    elif typ == 'multilayer':
        if len(inp) > 1:
           value = [parse_layer_spec(i.data, context)[0] for i in inp]
        else:
           value, _ = parse_layer_spec(inp[0].data, context)

    elif typ == 'enum':
        # XXX Processing wants the index of the value in option list
        if param.allowMultiple() and len(inp) > 1:
            opts  = param.options()
            value = [opts.index(d.data) for d in inp] 
        else:
            value = param.options().index(inp[0].data)

    elif typ == 'extent':
        r = inp[0].data
        rect  = QgsRectangle(r[0],r[2],r[1],r[3])
        ref   = QgsCoordinateReferenceSystem(inp.crs)
        value = QgsReferencedRectangle(rect, ref)

    elif typ == 'crs':
        # XXX CRS may be expressed as EPSG (or QgsProperty ?)
        value = inp[0].data

    elif typ in ('fileDestination','folderDestination'):
        # Normalize path
        value = basename(normpath(inp[0].data))
        if value != inp[0].data:
            LOGGER.warning("Value for file or folder destination '%s' has been truncated from '%s' to '%s'",
                    identifier, inp[0].data, value )

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
                    # Try to load custom style from workdir
                    style = os.path.join(context.workdir, details.outputName + '.qml')
                    if not os.path.exists(style):
                        style = RenderingStyles.getStyle(alg.id(), details.outputName)
                    LOGGER.debug("Getting style for %s: %s <%s>", alg.id(), details.outputName, style)
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
                    LOGGER.debug("Adding style to layer %s (outputName %s)", details.name, details.outputName)
                    layer.loadNamedStyle(style)

                # Add layer to destination project
                LOGGER.debug("Adding Map layer '%s' (outputName %s) to Qgs Project", l, details.outputName )
                details.project.addMapLayer(context.temporaryLayerStore().takeMapLayer(layer))

                # Handle post processing
                if details.postProcessor():
                    details.postProcessor().postProcessLayer(layer, context, feedback)

            else:
                LOGGER.warning("No layer found found for %s", l)
        except Exception:
            LOGGER.error("Processing: Error loading result layer:\n{}".format(traceback.format_exc()))
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
        self.uuid       = uuid_str[:8]

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

    def reportError(self, error, fatalError=False ):
        (LOGGER.critical if fatalError else LOGGER.error)("%s:%s %s", self.name, self.uuid, error)

    def pushInfo(self, info):
        LOGGER.info("%s:%s %s",self.name, self.uuid, info)

    def pushDebugInfo(self, info):
        LOGGER.debug("%s:%s %s",self.name, self.uuid, info)


def handle_layer_outputs(alg, results, context ):
    """ Replace output values by the layer names
    """
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

    def __init__(self, algorithm, context=None):
        """ Initialize algorithm with a create context

            The create context may be used by the algorithm to provide
            contextualized inputs (i.e inputs that depends on the context source project or 
            associated data)

            WPSInputs and Outputs are parsed from the processing definition.
        """
        self._create_context = context or {}

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

        version = alg.version() if hasattr(alg,'versions') else _generic_version

        handler = partial(QgsProcess._handler, create_context=self._create_context)

        super().__init__(handler,
                identifier = alg.id(),
                version    = version,
                title      = alg.displayName(),
                abstract   = alg.shortHelpString(),
                inputs     = inputs,
                outputs    = outputs)

    @staticmethod
    def createInstance( ident, **context ):
        """ Create a contextualized instance
        """
        LOGGER.debug("Creating contextualized process for %s: %s", ident, context)
        alg = _create_algorithm(ident, **context)
        return QgsProcess(alg, context)

    @staticmethod
    def _handler( request, response, create_context ):
        """  WPS process handler
        """
        uuid_str = str(response.uuid)
        LOGGER.info("Starting task %s:%s", uuid_str[:8], request.identifier)

        alg = QgsApplication.processingRegistry().createAlgorithmById(request.identifier, create_context)

        workdir  = response.process.workdir
        context  = Context(workdir, map_uri=request.map_uri)
        feedback = Feedback(response, alg.id(), uuid_str=uuid_str)

        context.setFeedback(feedback)
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometrySkipInvalid)

        # Convert parameters from WPS inputs
        parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in request.inputs.items() )

        try:
            # XXX Warning, a new instance of the algorithm without create_context will be created at the 'run' call
            # see https://qgis.org/api/qgsprocessingalgorithm_8cpp_source.html#l00414
            # We can deal with that because we will have a QgsProcessingContext and we should not 
            # rely on the create_context at this time.
            results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=handle_algorithm_results,
                                              feedback=feedback, context=context)
        except QgsProcessingException as e:
            raise ProcessException("%s" % e)

        LOGGER.info("Task finished %s:%s", request.identifier, uuid_str )

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

