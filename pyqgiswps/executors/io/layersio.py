#
# Copyright 2018-2020 3liz
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

from urllib.parse import urlparse, urlencode, parse_qs

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingFeatureSourceDefinition,
                       QgsProcessingOutputDefinition,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputVectorLayer,
                       QgsProcessingOutputMapLayer,
                       QgsProcessingOutputMultipleLayers,
                       QgsProcessingParameterLimitedDataTypes,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingUtils,
                       QgsProcessingContext,
                       QgsMapLayer,
                       QgsVectorLayer,
                       QgsWkbTypes,
                       QgsProperty,
                       QgsCoordinateReferenceSystem,
                       QgsFeatureRequest)

from ..processingcontext import MapContext, ProcessingContext

from pyqgiswps.app.Common import Metadata
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE
from pyqgiswps.inout.formats import Format, FORMATS
from pyqgiswps.inout.literaltypes import AllowedValue
from pyqgiswps.inout import (LiteralInput,
                             ComplexInput,
                             BoundingBoxInput,
                             LiteralOutput,
                             ComplexOutput,
                             BoundingBoxOutput)

from pyqgiswps.exceptions import (NoApplicableCode,
                                  InvalidParameterValue,
                                  MissingParameterValue,
                                  ProcessException)

from pyqgiswps.utils.filecache import get_valid_filename

from typing import Mapping, Any, TypeVar, Union, Tuple

WPSInput  = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]

LOGGER = logging.getLogger('SRVLOG')


DESTINATION_LAYER_TYPES = (QgsProcessingParameterFeatureSink,
                           QgsProcessingParameterVectorDestination,
                           QgsProcessingParameterRasterDestination)

OUTPUT_LAYER_TYPES = ( QgsProcessingOutputVectorLayer, 
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputMapLayer,
                       QgsProcessingOutputMultipleLayers)

INPUT_VECTOR_LAYER_TYPES = (QgsProcessingParameterVectorLayer, QgsProcessingParameterFeatureSource)
INPUT_RASTER_LAYER_TYPES = (QgsProcessingParameterRasterLayer,)
INPUT_OTHER_LAYER_TYPES  = (QgsProcessingParameterMapLayer, QgsProcessingParameterMultipleLayers)

INPUT_LAYER_TYPES = INPUT_VECTOR_LAYER_TYPES + INPUT_RASTER_LAYER_TYPES + INPUT_OTHER_LAYER_TYPES


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

# Allowed inputs formats

RASTER_INPUT_FORMATS=(Format.from_definition(FORMATS.NETCDF),
                      Format.from_definition(FORMATS.GEOTIFF))

VECTOR_INPUT_FORMATS=(Format.from_definition(FORMATS.GEOJSON),
                      Format.from_definition(FORMATS.GML),
                      Format.from_definition(FORMATS.SHP))

# ------------------------------------
# Processing parameters ->  WPS input
# ------------------------------------

def get_layers_type(param: QgsProcessingParameterDefinition,  kwargs) -> None:
    """ Set datatype as metadata
    """
    datatypes = []
    if isinstance(param, QgsProcessingParameterLimitedDataTypes):
        datatypes = param.dataTypes()

    if not datatypes: 
        if isinstance(param, INPUT_VECTOR_LAYER_TYPES):
            datatypes = [QgsProcessing.TypeVector]
        elif isinstance(param, INPUT_RASTER_LAYER_TYPES):
            datatypes = [QgsProcessing.TypeRaster]
        elif isinstance( param, QgsProcessingParameterMultipleLayers):
            datatypes = [param.layerType()]
        else:
            datatypes = [QgsProcessing.TypeMapLayer]

    kwargs['metadata'].append(Metadata('processing:dataTypes', ','.join(SourceTypes[dtyp] for dtyp in datatypes)))
    
    return datatypes


def get_layers_from_context(kwargs, context: MapContext, datatypes) -> None:
    """ Find candidate layers according to datatypes
    """
    #
    # Create the list of allowed layers according to datatypes
    #
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
            
    _allowed_layer = lambda l: AllowedValue(value=l.name(), allowed_type=ALLOWEDVALUETYPE.LAYER)

    kwargs['allowed_values'] = [_allowed_layer(lyr) for lyr in project.mapLayers().values() if _is_allowed(lyr)]
  

def is_vector_type( datatypes ):
    return QgsProcessing.TypeVector in datatypes \
        or QgsProcessing.TypeVectorAnyGeometry in datatypes \
        or QgsProcessing.TypeVectorPoint in datatypes \
        or QgsProcessing.TypeVectorLine  in datatypes \
        or QgsProcessing.TypeVectorPolygon in datatypes

def is_raster_type( datatypes ):
    return QgsProcessing.TypeRaster in datatypes


def parse_input_definition(param: QgsProcessingParameterDefinition, kwargs,
                           context: MapContext = None) -> LiteralInput:
    """ Layers input may be passed in various forms:

        - For input layers and if a context is given: it will be a list of  available layers from 
          the source project as literal string.
        - If there is no context, the input will be defined as a complex input for valid
          gis data.

        We treat layer destination the same as input since they refer to
        layers ids in qgisProject
    """
    if isinstance(param, INPUT_LAYER_TYPES):
        typ = param.type()

        if typ == 'multilayer':
            num_inputs = param.minimumNumberInputs();
            kwargs['min_occurs'] = num_inputs if num_inputs >= 1 else 0
            kwargs['max_occurs'] = kwargs['min_occurs']

        # Set metadata for geometry type
        datatypes = get_layers_type(param, kwargs)

        kwargs['data_type'] = 'string'

        if context is not None:
            # Retrieve the list of layers
            # Inputs will be a list of strings from the source
            # project
            get_layers_from_context(kwargs, context, datatypes)
            # Set max occurs accordingly
            if typ == 'multilayer':
                kwargs['max_occurs'] = len(kwargs['allowed_values'])

        return LiteralInput(**kwargs)

    elif isinstance(param, QgsProcessingParameterRasterDestination):
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:extension',param.defaultFileExtension()))
        return LiteralInput(**kwargs)
    elif isinstance(param, (QgsProcessingParameterVectorDestination, QgsProcessingParameterFeatureSink)):
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:dataType' , str(param.dataType())))
        kwargs['metadata'].append(Metadata('processing:extension', param.defaultFileExtension()))
        return LiteralInput(**kwargs)
    else:
        return None


# --------------------------------------
# WPS inputs ->  processing inputs data
# --------------------------------------

def parse_layer_spec( layerspec: str, context: ProcessingContext, allow_selection: bool=False ) -> Tuple[str,bool]:
    """ Parse a layer specification

        if allow_selection is set to True: 'select' parameter
        is interpreted has holding a qgis feature request expression

        :return: A tuple (path, bool)
    """
    if layerspec.find('layer:',0,6) == -1:
        # Nothing to do with it
        return layerspec, False

    u = urlparse(layerspec)
    p = u.path

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


def get_processing_value( param: QgsProcessingParameterDefinition, inp: WPSInput, 
                          context: ProcessingContext ) -> Any:
    """ Return processing values from WPS input data
    """
    if isinstance(param, DESTINATION_LAYER_TYPES):
        #
        # Destination layer: a new layer is created as file with the input name. 
        # Do not supports memory layer because we need persistence
        #
        param.setSupportsNonFileBasedOutput(False)
        #
        # Enforce pushing created layers to layersToLoadOnCompletion list
        # i.e layer will be stored in the destination project
        #
        # Canonize the output_name
         
        # Use canonical file name
        sink = "./%s.%s" % (get_valid_filename(param.name()), param.defaultFileExtension())
        value = QgsProcessingOutputLayerDefinition(sink, context.destination_project)
        value.destinationName = inp[0].data
        LOGGER.debug("Handling destination layer: %s, details name: %s", param.name(), value.destinationName)

    elif isinstance(param, QgsProcessingParameterFeatureSource):
        #
        # Support feature selection
        #
        value, has_selection = parse_layer_spec(inp[0].data, context, allow_selection=True)
        value = QgsProcessingFeatureSourceDefinition(value, selectedFeaturesOnly=has_selection)

    elif isinstance(param, INPUT_LAYER_TYPES):
        if len(inp) > 1:
            value = [parse_layer_spec(i.data, context)[0] for i in inp]
        else:
            value, _ = parse_layer_spec(inp[0].data, context)
    else:
        value = None

    return value

# -------------------------------------------
# Processing output definition -> WPS output
# -------------------------------------------

def parse_output_definition( outdef: QgsProcessingOutputDefinition, kwargs ) -> ComplexOutput:
    """ Parse layer output

        A layer output is merged to a qgis project, we return
        the wms uri associated to the project
    """
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
    elif isinstance(outdef, (QgsProcessingOutputMapLayer, QgsProcessingOutputMultipleLayers)):
        return ComplexOutput(supported_formats=[Format("application/x-ogc-wms")], 
                             as_reference=True, **kwargs)


def add_layer_to_load_on_completion( value: str, outdef: QgsProcessingOutputDefinition,
                                     context: ProcessingContext ) -> None:
    """ Add layer to load on completion

        The layer will be added to the destination project
    """

    multilayers = isinstance(outdef, QgsProcessingOutputMultipleLayers)
    outputName  = outdef.name()    

    if not multilayers and context.willLoadLayerOnCompletion( value ):
        # Do not add the layer twice: may be already added
        # an layer destination parameter
        details = context.layerToLoadOnCompletionDetails( value )
        if details.name:
            LOGGER.debug("Skipping already added layer for %s (details name: %s)", outputName, details.name)
            return (details.name,)
        else:
            try:
                layer = QgsProcessingUtils.mapLayerFromString(value, context, typeHint=details.layerTypeHint)
                if layer is not None:
                    details.setOutputLayerName(layer)
                    LOGGER.debug("Layer name for '%s' set to '%s'", outputName, layer.name())
                    return (layer.name(),)
            except Exception:
                LOGGER.error("Processing: Error loading result layer {}:\n{}".format(l,traceback.format_exc()))
        return ()

    if isinstance(outdef, QgsProcessingOutputVectorLayer):
        layerTypeHint = QgsProcessingUtils.LayerHint.Vector
    elif isinstance(outdef, QgsProcessingOutputRasterLayer):
        layerTypeHint = QgsProcessingUtils.LayerHint.Raster
    else:
        layerTypeHint = QgsProcessingUtils.LayerHint.UnknownType

    if hasattr(context, 'destination_project'):
        destination_project = context.destination_project
    else:
        destination_project = None

    def add_layer_details( l ):

        # Set empty name as we are calling setOutputLayerName
        details = QgsProcessingContext.LayerDetails("",
                        destination_project,
                        outputName,
                        layerTypeHint)
        try:
            layer = QgsProcessingUtils.mapLayerFromString(l, context, typeHint=details.layerTypeHint)
            if layer is not None:
                # Fix layer name
                # If details name is empty it well be set to the file name 
                # see https://qgis.org/api/qgsprocessingcontext_8cpp_source.html#l00128
                # XXX Make sure that Processing/Configuration/PREFER_FILENAME_AS_LAYER_NAME 
                # setting is set to false (see processfactory.py:129)
                details.setOutputLayerName(layer)
                LOGGER.debug("Layer name for '%s' set to '%s'", outputName, layer.name())
                context.addLayerToLoadOnCompletion(l,details)
                return layer.name()
            else:
               LOGGER.warning("No layer found for %s", l)
        except Exception:
            LOGGER.error("Processing: Error loading result layer {}:\n{}".format(l,traceback.format_exc()))

        return ()

    if multilayers:
        return tuple(name for name in (add_layer_details(l) for l in value) if name is not None)
    else:
        return (add_layer_details(value),)
    

def parse_response( value: Any, outdef: QgsProcessingOutputDefinition, out: WPSOutput, 
                    output_uri: str, context: QgsProcessingContext ) -> WPSOutput:
    """ Process processing response to WPS output 
    """
    if not isinstance(outdef, OUTPUT_LAYER_TYPES):
       return

    out.data_format = Format("application/x-ogc-wms")

    result = add_layer_to_load_on_completion( value, outdef, context )
    if result:
        result = ','.join(result)
        out.url = output_uri + '&' + urlencode((('layers',result),))
    else:
        out.url = output_uri


