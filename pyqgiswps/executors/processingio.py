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
from pathlib import Path

from pyqgiswps.app.Common import Metadata
from pyqgiswps.exceptions import (NoApplicableCode,
                              InvalidParameterValue,
                              MissingParameterValue,
                              ProcessException)

from pyqgiswps.inout.formats import Format, FORMATS
from pyqgiswps.inout import (LiteralInput,
                        ComplexInput,
                        BoundingBoxInput,
                        LiteralOutput,
                        ComplexOutput,
                        BoundingBoxOutput)

from pyqgiswps.inout.literaltypes import AnyValue, NoValue, ValuesReference, AllowedValue
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE

from pyqgiswps.app.WPSResponse import WPSResponse
from pyqgiswps.app.WPSRequest  import WPSRequest

from pyqgiswps.config import confservice

from osgeo import ogr

from qgis.PyQt.QtCore import QVariant

from qgis.core import QgsApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterNumber,
                       QgsProcessingOutputDefinition,
                       QgsProcessingParameterLimitedDataTypes,
                       QgsProcessingParameterField,
                       QgsProcessingParameterPoint,
                       QgsProcessingUtils,
                       QgsProcessingFeedback,
                       QgsReferencedRectangle,
                       QgsReferencedPointXY,
                       QgsRectangle,
                       QgsGeometry,
                       QgsWkbTypes,
                       QgsProperty,
                       QgsCoordinateReferenceSystem,
                       QgsFeatureRequest)


from .processingcontext import MapContext, ProcessingContext

from typing import Mapping, Any, TypeVar, Union, Tuple, Generator

from .io import filesio, layersio, datetimeio

WPSInput  = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]

LOGGER = logging.getLogger('SRVLOG')

class ProcessingTypeParseError(Exception):
    pass

class ProcessingInputTypeNotSupported(ProcessingTypeParseError):
    pass

class ProcessingOutputTypeNotSupported(ProcessingTypeParseError):
    pass


def _is_optional( param: QgsProcessingParameterDefinition ) -> bool:
    return (int(param.flags()) & QgsProcessingParameterDefinition.FlagOptional) !=0

def _is_hidden( param: QgsProcessingParameterDefinition ) -> bool:
    return (int(param.flags()) & QgsProcessingParameterDefinition.FlagHidden) !=0


# ==================
# Inputs converters
# ==================

def parse_literal_input( param: QgsProcessingParameterDefinition, kwargs ) -> LiteralInput:
    """ Convert processing input to Literal Input 
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
        default_value = param.defaultValue()
        if default_value is not None:
            # XXX Values for processing enum are indices
            if isinstance(default_value, list):
                default_value = default_value[0]
            if not isinstance(default_value, int):
                raise InvalidParameterValue('Unsupported default value for parameter %s: %s' % (param.name(), default_value))
            if default_value < 0 or default_value >= len(options):
                LOGGER.error("Out of range default value for enum parameter %s: %s",param.name(),default_value)
                default_value = 0
 
            kwargs['default'] = options[default_value]

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


def parse_metadata( param: QgsProcessingParameterDefinition, kwargs ) -> None:
    """ Parse freeform metadata
    """
    kwargs['metadata'].extend(Metadata('processing:meta:%s' % k, str(v)) for k,v in param.metadata().items())


def parse_extent_input( param: QgsProcessingParameterDefinition, kwargs ) -> BoundingBoxInput:
    """ Convert extent processing input to bounding box input"
    """
    typ = param.type()
    if typ == "extent":
       # XXX This is the default, do not presume anything
       # about effective crs at compute time
       kwargs['crss'] = ['EPSG:4326']
       return BoundingBoxInput(**kwargs)


def parse_point_input( param: QgsProcessingParameterDefinition, kwargs) -> ComplexInput:
    """ Convert processing point input to complex input
    """
    if isinstance(param, QgsProcessingParameterPoint):
        kwargs['supported_formats'] = [Format.from_definition(FORMATS.GEOJSON),
                                       Format.from_definition(FORMATS.GML)]
        return ComplexInput(**kwargs)
       

def parse_input_definition( param: QgsProcessingParameterDefinition, alg: QgsProcessingAlgorithm=None,  
                            context: MapContext=None ) -> WPSInput:
    """ Create WPS input from QgsProcessingParamDefinition
the description is used in QGIS UI as the title in WPS.
        see https://qgis.org/api/qgsprocessingparameters_8h_source.html#l01312
    """
    kwargs = {
        'identifier': param.name() ,
        'title'     : param.description() or param.name().replace('_',' '),
        'abstract'  : param.help(),
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
            or layersio.parse_input_definition(param,kwargs,context) \
            or parse_extent_input(param, kwargs) \
            or filesio.parse_input_definition(param, kwargs) \
            or datetimeio.parse_input_definition(param, kwargs) \
            or parse_point_input(param, kwargs)
    if inp is None:
        raise ProcessingInputTypeNotSupported("%s:'%s'" %(type(param),param.type()))

    parse_metadata(param, kwargs)

    return inp


def parse_input_definitions( alg: QgsProcessingAlgorithm, context: MapContext  ) -> Generator[WPSInput,None,None]:
    """ Parse algorithm inputs definitions 
    """
    for param in alg.parameterDefinitions():
        try:
            if not _is_hidden(param):
                yield parse_input_definition(param, alg, context=context)
            else:
                LOGGER.info("%s: dropping hidden param: %s", alg.id(),param.name())
        except ProcessingTypeParseError as e:
            LOGGER.error("%s: unsupported param %s",alg.id(),e)


# ==================
# Output converters
# ==================

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
             or layersio.parse_output_definition( outdef, kwargs ) \
             or filesio.parse_output_definition( outdef, kwargs, alg )
    if output is None:
        raise ProcessingOutputTypeNotSupported(outdef.type())

    return output


def parse_output_definitions( alg: QgsProcessingAlgorithm, context: MapContext  ) -> Generator[WPSOutput,None,None]:
    """ Parse algorithm inputs definitions 
    """
    for param in alg.outputDefinitions():
        try:
            yield parse_output_definition(param, alg, context=context)
        except ProcessingTypeParseError as e:
            LOGGER.error("%s: unsupported output param %s",alg.id(),e)



# ==================================================
# Convert input WPS values to processing inputs data
# ==================================================


def input_to_extent( inp: WPSInput ) -> QgsReferencedRectangle:
    """ Convert input to processing extent data
    """
    r = inp.data
    rect  = QgsRectangle(float(r[0]),float(r[2]),float(r[1]),float(r[3]))
    ref   = QgsCoordinateReferenceSystem(inp.crs)
    return QgsReferencedRectangle(rect, ref)


def input_to_point( inp: WPSInput ):
    """ Handle point from complex input
    """
    data_format = inp.data_format
    geom = None
    if data_format.mime_type == FORMATS.GEOJSON.mime_type:
        geom = ogr.CreateGeometryFromJson(inp.data)
    elif data_format.mime_type == FORMATS.GML.mime_type:
        # XXX Check that we do not get CRS  from GML
        # with ogr data
        geom = ogr.CreateGeometryFromGML(inp.data)
    if geom:
        srs  = geom.GetSpatialReference()
        geom = QgsGeometry.fromWkt(geom.ExportToWkt())
        if srs:
            srs = QgsCoordinateReferenceSystem.fromWkt(srs.ExportToWkt())
        if srs and srs.isValid():
            geom = QgsReferencedPointXY( geom.centroid().asPoint(), srs )
            
        return geom

    raise NoApplicableCode("Unsupported data format: %s" % data_format)


def get_processing_value( param: QgsProcessingParameterDefinition, inp: WPSInput,
                                context: ProcessingContext) -> Any:
    """ Return processing value from wps inputs

        Processes other inputs than layers
    """
    typ = param.type()

    if isinstance(param, QgsProcessingParameterPoint):
        value = input_to_point( inp[0] )

    elif typ == 'enum':
        # XXX Processing wants the index of the value in option list
        if param.allowMultiple() and len(inp) > 1:
            opts  = param.options()
            value = [opts.index(d.data) for d in inp] 
        else:
            value = param.options().index(inp[0].data)

    elif typ == 'extent':
        value = input_to_extent( inp[0] )

    elif typ == 'crs':
        # XXX CRS may be expressed as EPSG (or QgsProperty ?)
        value = inp[0].data

    elif len(inp):
        # Return raw value
        value = inp[0].data
    else:
        # Return undefined value
        if not _is_optional(param):
            LOGGER.warning("Required input %s has no value", param.name())
        value = None

    return value


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

    value = layersio.get_processing_value(param, inp, context) or \
            filesio.get_processing_value(param, inp, context)  or \
            datetimeio.get_processing_value(param, inp, context) or \
            get_processing_value(param, inp, context)
            
    return param.name(), value


# ==================================================
# Convert processing outputs to WPS output responses
# ==================================================

def raw_response( value: Any, out: WPSOutput) -> WPSOutput:
    """ Return raw value
    """
    out.data = value
    return out


def processing_to_output( value: Any, outdef: QgsProcessingOutputDefinition, out: WPSOutput, 
                          output_uri: str, context: ProcessingContext ) -> WPSOutput:
    """ Map processing output to WPS
    """
    return layersio.parse_response(value, outdef, out, output_uri,  context) or \
           filesio.parse_response(value, outdef, out, output_uri, context)   or \
           raw_response(value, out)

