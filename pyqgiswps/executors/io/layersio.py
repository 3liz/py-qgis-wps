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
import logging
import traceback

from pathlib import Path
from urllib.parse import quote, urlparse, urlencode, parse_qs

from qgis.core import (QgsProcessing,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterMeshLayer,
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
                       QgsProcessingDestinationParameter,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingUtils,
                       QgsProcessingContext,
                       QgsMapLayer,
                       QgsVectorLayer,
                       QgsWkbTypes,
                       QgsRectangle)

from ..processingcontext import MapContext, ProcessingContext

from pyqgiswps.app.common import Metadata
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE
from pyqgiswps.inout.formats import Format, FORMATS
from pyqgiswps.inout.literaltypes import AllowedValues
from pyqgiswps.inout import (LiteralInput,
                             ComplexInput,
                             BoundingBoxInput,
                             LiteralOutput,
                             ComplexOutput,
                             BoundingBoxOutput)

from pyqgiswps.exceptions import (NoApplicableCode,
                                  InvalidParameterValue)

from pyqgiswps.utils.filecache import get_valid_filename
from pyqgiswps.config import confservice

from typing import Any, Union, Tuple, Optional

WPSInput = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]

LOGGER = logging.getLogger('SRVLOG')


DESTINATION_VECTOR_LAYER_TYPES = (QgsProcessingParameterFeatureSink,
                                  QgsProcessingParameterVectorDestination)

DESTINATION_RASTER_LAYER_TYPES = (QgsProcessingParameterRasterDestination,)

DESTINATION_LAYER_TYPES = DESTINATION_VECTOR_LAYER_TYPES + DESTINATION_RASTER_LAYER_TYPES

OUTPUT_LAYER_TYPES = (QgsProcessingOutputVectorLayer,
                      QgsProcessingOutputRasterLayer,
                      QgsProcessingOutputMapLayer,
                      QgsProcessingOutputMultipleLayers)

INPUT_VECTOR_LAYER_TYPES = (QgsProcessingParameterVectorLayer, QgsProcessingParameterFeatureSource)
INPUT_RASTER_LAYER_TYPES = (QgsProcessingParameterRasterLayer,)
INPUT_OTHER_LAYER_TYPES = (QgsProcessingParameterMapLayer, QgsProcessingParameterMultipleLayers,
                           QgsProcessingParameterMeshLayer)

INPUT_LAYER_TYPES = INPUT_VECTOR_LAYER_TYPES + INPUT_RASTER_LAYER_TYPES + INPUT_OTHER_LAYER_TYPES


# Map processing source types to string
SourceTypes = {
    QgsProcessing.TypeMapLayer: 'TypeMapLayer',
    QgsProcessing.TypeVectorAnyGeometry: 'TypeVectorAnyGeometry',
    QgsProcessing.TypeVectorPoint: 'TypeVectorPoint',
    QgsProcessing.TypeVectorLine: 'TypeVectorLine',
    QgsProcessing.TypeVectorPolygon: 'TypeVectorPolygon',
    QgsProcessing.TypeRaster: 'TypeRaster',
    QgsProcessing.TypeFile: 'TypeFile',
    QgsProcessing.TypeVector: 'TypeVector',
    QgsProcessing.TypeMesh: 'TypeMesh',
}

# Allowed inputs formats

RASTER_INPUT_FORMATS = (Format.from_definition(FORMATS.NETCDF),
                        Format.from_definition(FORMATS.GEOTIFF))

VECTOR_INPUT_FORMATS = (Format.from_definition(FORMATS.GEOJSON),
                        Format.from_definition(FORMATS.GML),
                        Format.from_definition(FORMATS.SHP))

# ------------------------------------
# Processing parameters ->  WPS input
# ------------------------------------


def get_layers_type(param: QgsProcessingParameterDefinition, kwargs) -> None:
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
        elif isinstance(param, QgsProcessingParameterMultipleLayers):
            datatypes = [param.layerType()]
        elif isinstance(param, QgsProcessingParameterMeshLayer):
            datatypes = [QgsProcessing.TypeMesh]
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
                or (geomtype == QgsWkbTypes.LineGeometry and QgsProcessing.TypeVectorLine in datatypes)  \
                or (geomtype == QgsWkbTypes.PolygonGeometry and QgsProcessing.TypeVectorPolygon in datatypes) \
                or QgsProcessing.TypeVectorAnyGeometry in datatypes \
                or QgsProcessing.TypeVector in datatypes \
                or QgsProcessing.TypeMapLayer in datatypes
        elif lyr.type() == QgsMapLayer.RasterLayer:
            return QgsProcessing.TypeRaster in datatypes \
                or QgsProcessing.TypeMapLayer in datatypes
        elif lyr.type() == QgsMapLayer.MeshLayer:
            return QgsProcessing.TypeMesh in datatypes \
                or QgsProcessing.TypeMapLayer in datatypes
        return False

    allowed_layers = [lyr.name() for lyr in project.mapLayers().values() if _is_allowed(lyr)]
    kwargs['allowed_values'] = AllowedValues(values=allowed_layers, allowed_type=ALLOWEDVALUETYPE.LAYER)


def is_vector_type(datatypes):
    return QgsProcessing.TypeVector in datatypes \
        or QgsProcessing.TypeVectorAnyGeometry in datatypes \
        or QgsProcessing.TypeVectorPoint in datatypes \
        or QgsProcessing.TypeVectorLine in datatypes \
        or QgsProcessing.TypeVectorPolygon in datatypes


def is_raster_type(datatypes):
    return QgsProcessing.TypeRaster in datatypes


def get_default_destination_values(param: QgsProcessingDestinationParameter, default: Optional[str]) -> Tuple[str, str]:
    """ Get default value from parameter
    """
    defval = param.defaultValue()
    ext = param.defaultFileExtension()

    # Check for default extensions override ?
    if isinstance(param, DESTINATION_VECTOR_LAYER_TYPES):
        ext = confservice.get('processing', 'vector.fileext') or ext
    elif isinstance(param, DESTINATION_RASTER_LAYER_TYPES):
        ext = confservice.get('processing', 'raster.fileext') or ext

    if isinstance(defval, QgsProcessingOutputLayerDefinition):
        sink = defval.sink
        if sink:
            # Try to get extension from the sink value
            sink = sink.staticValue()
            if sink:
                # Remove extra open options
                url = urlparse(sink.split('|', 1)[0])
                if url.path and url.scheme.lower() in ('', 'file'):
                    p = Path(url.path)
                    ext = p.suffix.lstrip('.') or ext
                    defval = defval.destinationName or p.stem
    else:
        defval = default

    return ext, defval


def parse_root_destination_path(param: QgsProcessingDestinationParameter,
                                value: str, default_extension: str) -> Tuple[str, str]:
    """ Parse input value as sink

        In this situation, value is interpreted as the output sink of the destination layer,
        It may be any source url supported by Qgis (but with options stripped)

        The layername may be specified by appending the '|layername=<name>' to the input string.
    """
    value, *rest = value.split('|', 2)

    destinationName = None

    # Check for layername option
    if len(rest) > 0 and rest[0].lower().startswith('layername='):
        destinationName = rest[0].split('=')[1].strip()

    url = urlparse(value)
    if url.path and url.scheme.lower() in ('', 'file'):
        p = Path(url.path)

        if p.is_absolute():
            root = Path(confservice.get('processing', 'destination_root_path'))
            p = root.joinpath(p.relative_to('/'))

        # Check for extension:
        if not p.suffix:
            p = p.with_suffix(f'.{default_extension}')

        destinationName = destinationName or p.stem
        sink = str(p)
    else:
        destinationName = destinationName or param.name()
        sink = value

    return sink, destinationName


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
            num_inputs = param.minimumNumberInputs()
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
                kwargs['max_occurs'] = len(kwargs['allowed_values'].values or 0)
        return LiteralInput(**kwargs)

    elif isinstance(param, DESTINATION_LAYER_TYPES):
        # Since QgsProcessingOutputLayerDefinition may
        # be defined as default value, get extension
        # and layer name from it
        extension, defval = get_default_destination_values(param, kwargs['default'])
        kwargs['default'] = defval

        kwargs['data_type'] = 'string'
        # Used to retrieve extension when handling wps response
        kwargs['metadata'].append(Metadata('processing:extension', extension))
        if isinstance(param, DESTINATION_VECTOR_LAYER_TYPES):
            kwargs['metadata'].append(Metadata('processing:dataType', str(param.dataType())))
        return LiteralInput(**kwargs)

    else:
        return None


# --------------------------------------
# WPS inputs ->  processing inputs data
# --------------------------------------

def get_metadata(inp, name):
    return [m.href for m in inp.metadata if m.title == name]


def parse_layer_spec(layerspec: str, context: ProcessingContext, allow_selection: bool = False) -> Tuple[str, bool]:
    """ Parse a layer specification

        if allow_selection is set to True: 'select' parameter
        is interpreted has holding a qgis feature request expression

        :return: A tuple (path, bool)
    """
    if layerspec.find('layer:', 0, 6) == -1:
        # Nothing to do with it
        return layerspec, False

    u = urlparse(layerspec)
    p = u.path

    if not allow_selection:
        return p, False

    has_selection = False
    qs = parse_qs(u.query)
    feat_requests = qs.get('select', [])
    feat_rects = qs.get('rect', [])
    if feat_rects or feat_requests:
        has_selection = True
        layer = context.getMapLayer(p)
        if not layer:
            LOGGER.error("No layer path for %s", layerspec)
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
                    layer.selectByExpression(ftreq, behavior=behavior)
            except Exception:
                LOGGER.error(traceback.format_exc())
                raise NoApplicableCode("Feature selection failed")
    return p, has_selection


def get_processing_value(param: QgsProcessingParameterDefinition, inp: WPSInput,
                         context: ProcessingContext) -> Any:
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

        # get extension from input metadata (should always exist for destination)
        extension = get_metadata(inp[0], 'processing:extension')[0]

        destination = inp[0].data

        if confservice.getboolean('processing', 'unsafe.raw_destination_input_sink'):
            sink, destination = parse_root_destination_path(param, destination, extension)
        else:
            # Use canonical file name
            sink = f"./{get_valid_filename(param.name())}.{extension}"

        value = QgsProcessingOutputLayerDefinition(sink, context.destination_project)
        value.destinationName = destination

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


def parse_output_definition(outdef: QgsProcessingOutputDefinition, kwargs) -> ComplexOutput:
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


def add_layer_to_load_on_completion(value: str, outdef: QgsProcessingOutputDefinition,
                                    context: ProcessingContext) -> Tuple[str, ...]:
    """ Add layer to load on completion

        The layer will be added to the destination project
    """

    multilayers = isinstance(outdef, QgsProcessingOutputMultipleLayers)
    outputName = outdef.name()

    if not multilayers and context.willLoadLayerOnCompletion(value):
        # Do not add the layer twice: may be already added
        # in layer destination parameter
        details = context.layerToLoadOnCompletionDetails(value)
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
                LOGGER.error("Processing: Error loading result layer {}:\n{}".format(
                    layer.name(), traceback.format_exc()))
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

    def add_layer_details(lyrname):

        # Set empty name as we are calling setOutputLayerName
        details = QgsProcessingContext.LayerDetails("", destination_project, outputName, layerTypeHint)
        try:
            layer = QgsProcessingUtils.mapLayerFromString(lyrname, context, typeHint=details.layerTypeHint)
            if layer is not None:
                # Fix layer name
                # Because if details name is empty it will be set to the file name
                # see https://qgis.org/api/qgsprocessingcontext_8cpp_source.html#l00128
                # XXX Make sure that Processing/Configuration/PREFER_FILENAME_AS_LAYER_NAME
                # setting is set to false (see processfactory.py:129)
                details.setOutputLayerName(layer)
                LOGGER.debug("Layer name for '%s' set to '%s'", outputName, layer.name())
                context.addLayerToLoadOnCompletion(lyrname, details)
                return layer.name()
            else:
                LOGGER.warning("No layer found for %s", lyrname)
        except Exception:
            LOGGER.error(f"Processing: Error loading result layer {lyrname}:\n{traceback.format_exc()}")

        return None

    if multilayers:
        return tuple(name for name in (add_layer_details(lyrname) for lyrname in value) if name is not None)
    else:
        name = add_layer_details(value)
        if name:
            return (name,)


def parse_response(value: Any, outdef: QgsProcessingOutputDefinition, out: WPSOutput,
                   context: QgsProcessingContext) -> Optional[WPSOutput]:
    """ Process processing response to WPS output
    """
    if not isinstance(outdef, OUTPUT_LAYER_TYPES):
        return

    out.data_format = Format("application/x-ogc-wms")

    output_url = context.wms_url

    result = add_layer_to_load_on_completion(value, outdef, context)
    if result:
        result = ','.join(result)
        out.url = output_url + '&' + urlencode((('layers', result),), quote_via=quote)
    else:
        out.url = output_url

    return out
