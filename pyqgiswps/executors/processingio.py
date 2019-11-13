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

from pyqgiswps.app.Common import Metadata
from pyqgiswps.exceptions import (NoApplicableCode,
                              InvalidParameterValue,
                              MissingParameterValue,
                              ProcessException)

from pyqgiswps.inout.formats import Format
from pyqgiswps.inout import (LiteralInput,
                        ComplexInput,
                        BoundingBoxInput,
                        LiteralOutput,
                        ComplexOutput,
                        BoundingBoxOutput)

from pyqgiswps.inout.literaltypes import AnyValue, NoValue, ValuesReference, AllowedValue
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE

from pyqgiswps import config

from pyqgiswps.app.WPSResponse import WPSResponse
from pyqgiswps.app.WPSRequest  import WPSRequest

from qgis.PyQt.QtCore import QVariant

from qgis.core import QgsApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingFeatureSourceDefinition,
                       QgsProcessingOutputDefinition,
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


from .processingcontext import MapContext, ProcessingContext


from processing.core.Processing import (Processing,
                                        ProcessingConfig,
                                        RenderingStyles)

from typing import Mapping, Any, TypeVar, Union, Tuple

WPSInput  = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]

LOGGER = logging.getLogger('SRVLOG')

DESTINATION_LAYER_TYPES = (QgsProcessingParameterFeatureSink,
                           QgsProcessingParameterVectorDestination,
                           QgsProcessingParameterRasterDestination)

OUTPUT_LITERAL_TYPES = ("string","number","enum","number")
OUTPUT_LAYER_TYPES = ( QgsProcessingOutputVectorLayer, QgsProcessingOutputRasterLayer )

INPUT_VECTOR_LAYER_TYPES = (QgsProcessingParameterVectorLayer, QgsProcessingParameterFeatureSource)
INPUT_RASTER_LAYER_TYPES = (QgsProcessingParameterRasterLayer,)

INPUT_LAYER_TYPES = INPUT_VECTOR_LAYER_TYPES + INPUT_RASTER_LAYER_TYPES + (QgsProcessingParameterMapLayer,)

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

class ProcessingTypeParseError(Exception):
    pass

class ProcessingInputTypeNotSupported(ProcessingTypeParseError):
    pass

class ProcessingOutputTypeNotSupported(ProcessingTypeParseError):
    pass


def _is_optional( param: QgsProcessingParameterDefinition ) -> bool:
    return (int(param.flags()) & QgsProcessingParameterDefinition.FlagOptional) !=0


def parse_literal_input( param: QgsProcessingParameterDefinition, kwargs ) -> LiteralInput:
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


def parse_file_input( param: QgsProcessingParameterDefinition, kwargs) -> Union[LiteralInput,ComplexInput]:
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


def parse_metadata( param: QgsProcessingParameterDefinition, kwargs ) -> None:
    """ Parse freeform metadata
    """
    kwargs['metadata'].extend(Metadata('processing:meta:%s' % k, str(v)) for k,v in param.metadata().items())


def parse_allowed_layers(param: QgsProcessingParameterDefinition, kwargs, context: MapContext) -> None:
    """ Find candidate layers according to datatypes
    """
    if context is None:
        return

    datatypes = []
    if isinstance(param, QgsProcessingParameterLimitedDataTypes):
        datatypes = param.dataTypes()

    if not datatypes: 
        if isinstance(param, INPUT_VECTOR_LAYER_TYPES):
            datatypes = [QgsProcessing.TypeVector]
        elif isinstance(param, INPUT_VECTOR_RASTER_TYPES):
            datatypes = [QgsProcessing.TypeRaster]
        else:
            datatypes = [QgsProcessing.TypeMapLayer]

    project = context.project()
    def _is_allowed(lyr):
        if lyr.type() == QgsMapLayer.VectorLayer:
            geomtype = lyr.geometryType()
            return (geomtype == QgsWkbTypes.PointGeometry and QgsProcessing.TypeVectorPoint in datatypes) \
            or (geomtype == QgsWkbTypes.LineGeometry      and QgsProcessing.TypeVectorLine in datatypes)  \
            or (geomtype == QgsWkbTypes.PolygonGeometry   and QgsProcessing.TypeVectorPolygon in datatypes) \
            or QgsProcessing.TypeVectorAnyGeometry in datatypes \
            or QgsProcessing.TypeVector in datatypes \
            or QgsProcessing.TypeMapLayer in datatypes
        elif lyr.type() == QgsMapLayer.RasterLayer: 
            return QgsProcessing.TypeRaster in datatypes \
                or QgsProcessing.TypeMapLayer in datatypes
        return False
        
    kwargs['allowed_values'] = [lyr.name() for lyr in project.mapLayers().values() if _is_allowed(lyr)]
    

def parse_layer_input(param: QgsProcessingParameterDefinition, kwargs,
                      context: MapContext = None) -> LiteralInput:
    """ Layers input are passe as layer name

        We treat layer destination the same as input since they refer to
        layers ids in qgisProject
    """
    typ = param.type()
    if isinstance(param, INPUT_LAYER_TYPES):
        kwargs['data_type'] = 'string'
        parse_allowed_layers(param, kwargs, context)
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


def parse_extent_input( param: QgsProcessingParameterDefinition, kwargs ) -> BoundingBoxInput:
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


def parse_input_definition( param: QgsProcessingParameterDefinition, alg: QgsProcessingAlgorithm=None,  
                            context: MapContext=None ) -> WPSInput:
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

    inp = parse_literal_input(param,kwargs) \
            or parse_layer_input(param,kwargs, context) \
            or parse_extent_input(param, kwargs) \
            or parse_file_input(param, kwargs)
    if inp is None:
        raise ProcessingInputTypeNotSupported("%s:'%s'" %(type(param),param.type()))

    parse_metadata(param, kwargs)

    return inp


def parse_literal_output( outdef: QgsProcessingOutputDefinition, kwargs ) -> LiteralOutput:
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


def parse_layer_output( outdef: QgsProcessingOutputDefinition, kwargs ) -> ComplexOutput:
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


def parse_file_output( outdef: QgsProcessingOutputDefinition, kwargs, 
                       alg: QgsProcessingAlgorithm=None ) -> ComplexOutput:
    """ Parse file output definition
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


def parse_output_definition( outdef: QgsProcessingOutputDefinition, alg: QgsProcessingAlgorithm=None, 
                             context: MapContext=None ) -> WPSOutput:
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


def parse_layer_spec( layerspec: str, context: ProcessingContext, allow_selection: bool=False ) -> Tuple[str,bool]:
    """ Parse a layer specification

        if allow_selection is set to True: 'select' parameter
        is interpreted has holding a qgis feature request expression

        :return: A tuple (path, bool)
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


def input_to_processing( identifier: str, inp: WPSInput, alg: QgsProcessingAlgorithm, 
                         context: ProcessingContext ) -> Tuple[str, Any]:
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

    elif isinstance(param, INPUT_LAYER_TYPES):
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


def format_output_url( response: WPSResponse, file_name:str ) -> str:
    """ Build output/store url for output file name
    """
    outputurl = config.get_config('server')['outputurl']
    return outputurl.format(
                host_url = response.wps_request.host_url,
                uuid     = response.uuid,
                file     = file_name)


def to_output_file( file_name: str, out: ComplexOutput, context: ProcessingContext ) -> ComplexOutput:
    """ Output file
    """
    if out.as_reference:
        out.url = format_output_url(context.response, file_name)
    else:
        out.file = os.path.join(context.workdir,file_name)

    return out


def processing_to_output( value: Any, outdef: QgsProcessingOutputDefinition, out: WPSOutput, 
                          output_uri: str, context: ProcessingContext ) -> None:
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
        mime = mimetypes.types_map.get(sfx.lower())
        if mime is None:
            LOGGER.warning("Cannot get file type for output %s: %s", outdef.name(), value)
            mime = "application/octet-stream"    
        out.output_format = mime
        return to_output_file( value, out, context )
    else:
        # Return raw value
        out.data = value


