
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original parts are Copyright 2016 OSGeo Foundation,            
# represented by PyWPS Project Steering Committee,               
# and released under MIT license.                                
# Please consult PYWPS_LICENCE.txt for details
#
"""Literaltypes are used for LiteralInputs, to make sure, input data are OK
"""

from urllib.parse import urlparse
from dateutil.parser import parse as date_parser
import datetime
from pyqgiswps.exceptions import InvalidParameterValue
from pyqgiswps.validator.allowed_value import RANGECLOSURETYPE
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE

import pyqgiswps.ogc as ogc

from typing import Optional, List, Dict, Union, Any, TypeVar


import logging
LOGGER = logging.getLogger('SRVLOG')


# JsonValue type definition
JsonValue = Union[str,List['JsonValue'],Dict[str,'JsonValue'],int,float,bool,None]

# Literal value type definition
LiteralInputValue = TypeVar('LiteralInputValue')

# Comparable type for value range
LiteralNumeric = TypeVar('LiteralNumeric',int,float)


# Literal data types
LITERAL_DATA_TYPES = ('float', 'boolean', 'integer', 'string',
                      'positiveInteger', 'anyURI', 'time', 'date', 'dateTime',
                      'scale', 'angle',
                      'nonNegativeInteger')





# currently we are supporting just ^^^ data types, feel free to add support for
# more
# 'measure', 'angleList',
# 'angle', 'integerList',
# 'positiveIntegerList',
# 'lengthOrAngle', 'gridLength',
# 'measureList', 'lengthList',
# 'gridLengthList', 'scaleList', 'timeList',
# 'nonNegativeInteger', 'length'


class AnyValue:
    """Any value for literal input
    """
    @property
    def json(self) -> JsonValue:
        return {'type': 'anyvalue'}

    @staticmethod
    def to_json_serializable( data: Any ):
        return to_json_serializable(data)


class NoValue:
    """No value allowed
    NOTE: not really implemented
    """

    @property
    def json(self) -> JsonValue:
        return {'type': 'novalue'}


class ValuesReference:
    """Any value for literal input
    NOTE: not really implemented
    """

    @property
    def json(self) -> JsonValue:
        return {'type': 'valuesreference'}


class AllowedValue(AnyValue, *ogc.exports.AllowedValue):
    """Allowed value parameters
    the values are evaluated in literal validator functions

    :param pyqgiswps.validator.allowed_value.ALLOWEDVALUETYPE allowed_type: VALUE or RANGE
    :param value: single value
    :param minval: minimal value in case of Range
    :param maxval: maximal value in case of Range
    :param spacing: spacing in case of Range
    :param pyqgiswps.input.literaltypes.RANGECLOSURETYPE range_closure:
    """

    def __init__(self, allowed_type: ALLOWEDVALUETYPE = ALLOWEDVALUETYPE.VALUE, 
                 value: Optional[Any]=None,
                 minval: Optional[LiteralNumeric]=None, 
                 maxval: Optional[LiteralNumeric]=None, 
                 spacing: Optional[LiteralNumeric]=None,
                 range_closure: RANGECLOSURETYPE = RANGECLOSURETYPE.CLOSED) -> None:

        AnyValue.__init__(self)

        self.allowed_type = allowed_type
        self.value = value
        self.minval = minval
        self.maxval = maxval
        self.spacing = spacing
        self.range_closure = range_closure

    @property
    def is_range(self):
        return self.allowed_type == ALLOWEDVALUETYPE.RANGE

    def __repr__(self) -> str:
        return f"AllowedValue(minval={self.minval}, maxval={self.maxval}, range_closure={self.range_closure})"

    @property
    def json(self) -> JsonValue:
        value = self.value
        if hasattr(value, 'json'):
            value = value.json
        return {
            'type': 'allowedvalue',
            'allowed_type': self.allowed_type,
            'value' : to_json_serializable(value),
            'minval': to_json_serializable(self.minval),
            'maxval': to_json_serializable(self.maxval),
            'spacing': self.spacing,
            'range_closure': self.range_closure
        }


def convert(data_type: str, data: LiteralInputValue) -> Any:
    """function for decoration of convert
    """
    convert = None
    if data_type in LITERAL_DATA_TYPES:
        if data_type == 'string':
            convert = convert_string
        elif data_type == 'integer':
            convert = convert_integer
        elif data_type == 'float':
            convert = convert_float
        elif data_type == 'boolean':
            convert = convert_boolean
        elif data_type == 'positiveInteger':
            convert = convert_positiveInteger
        elif data_type == 'anyURI':
            convert = convert_anyURI
        elif data_type == 'time':
            convert = convert_time
        elif data_type == 'date':
            convert = convert_date
        elif data_type == 'dateTime':
            convert = convert_datetime
        elif data_type == 'scale':
            convert = convert_scale
        elif data_type == 'angle':
            convert = convert_angle
        elif data_type == 'nonNegativeInteger':
            convert = convert_positiveInteger
        else:
            raise InvalidParameterValue(
                "Invalid data_type value of LiteralInput " + \
                "set to '{}'".format(data_type))
    try:
        return convert(data)
    except ValueError:
        raise InvalidParameterValue(
            "Could not convert value '{}' to format '{}'".format(
                data, data_type))


def convert_boolean(inpt: LiteralInputValue) -> bool:
    """Return boolean value from input boolean input

    >>> convert_boolean('1')
    True
    >>> convert_boolean('-1')
    True
    >>> convert_boolean('FaLsE')
    False
    >>> convert_boolean('FaLsEx')
    True
    >>> convert_boolean(0)
    False
    """

    val = False
    if str(inpt).lower() in ['false', 'f']:
        val = False
    else:
        try:
            val = int(inpt)
            if val == 0:
                val = False
            else:
                val = True
        except Exception:
            val = True
    return val


def convert_float(inpt: LiteralInputValue) -> float:
    """Return float value from inpt

    >>> convert_float('1')
    1.0
    """

    return float(inpt)


def convert_integer(inpt: LiteralInputValue) -> int:
    """Return integer value from input inpt

    >>> convert_integer('1.0')
    1
    """

    return int(float(inpt))


def convert_string(inpt: LiteralInputValue) -> str:
    """Return string value from input lit_input

    >>> convert_string(1)
    '1'
    """
    return str(inpt)


def convert_positiveInteger(inpt: LiteralInputValue) -> int:
    """Return value of input"""

    inpt = convert_integer(inpt)
    if inpt < 0:
        raise InvalidParameterValue(
            'The value "{}" is not of type positiveInteger'.format(inpt))
    else:
        return inpt


def convert_anyURI(inpt: LiteralInputValue) -> str:
    """Return value of input

    :rtype: url components
    """

    inpt = convert_string(inpt)
    components = urlparse(inpt)

    if components[0] and components[1]:
        return components.geturl()
    else:
        raise InvalidParameterValue(
            'The value "{}" does not seem to be of type anyURI'.format(inpt))


def convert_time(inpt: LiteralInputValue ) -> datetime.time:
    """Return value of input
    time formating assumed according to ISO standard:

    https://www.w3.org/TR/xmlschema-2/#time

    Examples: 12:00:00

    :rtype: datetime.time object
    """
    if not isinstance(inpt, datetime.time):
        inpt = convert_datetime(inpt).time()
    return inpt


def convert_date(inpt: LiteralInputValue) -> datetime.date:
    """Return value of input
    date formating assumed according to ISO standard:

    https://www.w3.org/TR/xmlschema-2/#date

    Examples: 2016-09-20

    :rtype: datetime.date object
    """
    if not isinstance(inpt, datetime.date):
        inpt = convert_datetime(inpt).date()
    return inpt


def convert_datetime(inpt: LiteralInputValue ) -> datetime.datetime:
    """Return value of input
    dateTime formating assumed according to ISO standard:

    * http://www.w3.org/TR/NOTE-datetime
    * https://www.w3.org/TR/xmlschema-2/#dateTime

    Examples: 2016-09-20T12:00:00, 2012-12-31T06:30:00Z,
              2017-01-01T18:00:00+01:00

    :rtype: datetime.datetime object
    """
    if not isinstance(inpt, datetime.datetime):
        inpt = convert_string(inpt)
        inpt = date_parser(inpt)
    return inpt


def convert_scale(inpt: LiteralInputValue) -> float:
    """Return value of input"""

    return convert_float(inpt)


def convert_angle(inpt: LiteralInputValue) -> float:
    """Return value of input

    return degrees
    """

    inpt = convert_float(inpt)
    return inpt % 360


def make_allowedvalues(allowed_values: Any) -> List[AllowedValue]:
    """ convert given value list to AllowedValue objects

        List/tuple value are intepreted as range

        :return: list of pyqgiswps.inout.literaltypes.AllowedValue
    """

    new_allowedvalues = []

    for value in allowed_values:

        if isinstance(value, AllowedValue):
            new_allowedvalues.append(value)

        elif type(value) == tuple or type(value) == list:
            minval = maxval = spacing = None
            if len(value) == 2:
                minval = value[0]
                maxval = value[1]
            else:
                minval = value[0]
                spacing = value[1]
                maxval = value[2]
            new_allowedvalues.append(
                AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE,
                             minval=minval, maxval=maxval,
                             spacing=spacing)
            )

        else:
            new_allowedvalues.append(AllowedValue(value=value))

    return new_allowedvalues


def is_anyvalue(value: Any) -> bool:
    """Check for any value object of given value
    """
    is_av = False

    if value == AnyValue:
        is_av = True
    elif value is None:
        is_av = True
    elif isinstance(value, AnyValue):
        is_av = True
    elif str(value).lower() == 'anyvalue':
        is_av = True

    return is_av


def to_json_serializable( data: Any ) -> JsonValue:
    """ Convern Literal to serializable value
    """
    # Convert datetime to string
    if isinstance(data, (datetime.date,datetime.time,datetime.datetime)):
        return data.replace(microsecond=0).isoformat()
    elif isinstance(data, datetime.date):
        return data.isoformat()
    else:
        return data

