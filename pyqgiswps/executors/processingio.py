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
import logging

from pyqgiswps.app.common import Metadata
from pyqgiswps.exceptions import InvalidParameterValue

from pyqgiswps.inout import (LiteralInput,
                             ComplexInput,
                             BoundingBoxInput,
                             LiteralOutput,
                             ComplexOutput,
                             BoundingBoxOutput)

from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterNumber,
                       QgsProcessingOutputDefinition,
                       QgsProcessingParameterField,
                       QgsUnitTypes)

from .processingcontext import MapContext, ProcessingContext

from typing import Any, Union, Tuple, Generator

from .io import filesio, layersio, datetimeio, geometryio

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

def _number_data_type( param: QgsProcessingParameterNumber ) -> str:
    return { 
        QgsProcessingParameterNumber.Double :'float',
        QgsProcessingParameterNumber.Integer:'integer',
    }[param.dataType()]


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
        kwargs['data_type'] = _number_data_type(param)
        kwargs['allowed_values'] = [(param.minimum(),param.maximum())]
    elif typ == 'distance':
        kwargs['data_type'] = 'length'
        kwargs['allowed_values'] = [(param.minimum(),param.maximum())]
        kwargs['metadata'].extend((
            Metadata('processing:parentParameterName', param.parentParameterName()),
            Metadata('processing:defaultUnit', QgsUnitTypes.toString(param.defaultUnit())),
        ))
    elif typ == 'scale':
        kwargs['data_type'] = 'scale'
        kwargs['allowed_values'] = [(param.minimum(),param.maximum())]
    elif typ == 'duration':
        # XXX OGC duration is defined as time dataType
        kwargs['data_type'] = 'time'
        kwargs['allowed_values'] = [(param.minimum(),param.maximum())]
        kwargs['metadata'].append(
            Metadata('processing:defaultUnit', QgsUnitTypes.toString(param.defaultUnit())),
        )
    elif typ =='field':
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:parentLayerParameterName',
                                  param.parentLayerParameterName()))
        kwargs['metadata'].append(Metadata('processing:dataType', { 
            QgsProcessingParameterField.Any: 'Any',
            QgsProcessingParameterField.Numeric: 'Numeric',
            QgsProcessingParameterField.String: 'String',
            QgsProcessingParameterField.DateTime: 'DateTime',
        }[param.dataType()]))
    elif typ == 'band':
        kwargs['data_type'] = 'nonNegativeInteger'
    else:
        return None

    return LiteralInput(**kwargs)


def parse_metadata( param: QgsProcessingParameterDefinition, kwargs ) -> None:
    """ Parse freeform metadata
    """
    kwargs['metadata'].extend(Metadata('processing:meta:%s' % k, str(v)) for k,v in param.metadata().items())


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
        or layersio.parse_input_definition(param, kwargs, context) \
        or geometryio.parse_input_definition(param, kwargs, context) \
        or filesio.parse_input_definition(param, kwargs) \
        or datetimeio.parse_input_definition(param, kwargs)
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
    elif typ == 'outputBoolean':
        kwargs['data_type'] = 'boolean'
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
        'abstract'  : outdef.description() 
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


def get_processing_value( param: QgsProcessingParameterDefinition, inp: WPSInput,
                          context: ProcessingContext) -> Any:
    """ Return processing value from wps inputs

        Processes other inputs than layers
    """
    typ = param.type()
    if typ == 'enum':
        # XXX Processing wants the index of the value in option list
        if param.allowMultiple() and len(inp) > 1:
            opts  = param.options()
            value = [opts.index(d.data) for d in inp] 
        else:
            value = param.options().index(inp[0].data)
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
        filesio.get_processing_value(param, inp, context) or \
        datetimeio.get_processing_value(param, inp, context) or \
        geometryio.get_processing_value(param, inp, context) or \
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
                          context: ProcessingContext ) -> WPSOutput:
    """ Map processing output to WPS
    """
    return layersio.parse_response(value, outdef, out, context) or \
        filesio.parse_response(value, outdef, out, context) or \
        raw_response(value, out)

