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

import datetime
import logging

from urllib.parse import urlparse

from dateutil.parser import parse as date_parser
from typing_extensions import (
    Any,
    List,
    Optional,
    Self,
    TypeVar,
    Union,
)

import pyqgiswps.ogc as ogc

from pyqgiswps.exceptions import InvalidParameterValue
from pyqgiswps.protos import JsonValue
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE, RANGECLOSURETYPE
from pyqgiswps.validator.base import to_json_serializable

LOGGER = logging.getLogger('SRVLOG')


# Forward alue type definition
LiteralInputValue = TypeVar(
    'LiteralInputValue',
    bound=Union[
        int,
        float,
        str,
        datetime.date,
        datetime.time,
        datetime.datetime,
    ],
)

# Comparable type for value range
LiteralNumeric = TypeVar('LiteralNumeric', bound=Union[int, float])

# Literal data types
LITERAL_DATA_TYPES = ogc.OGCTYPE.keys()


class AnyValue:
    """Any value for literal input
    """
    @property
    def json(self) -> JsonValue:
        return {'type': 'anyvalue'}


class AllowedValues(*ogc.exports.AllowedValues):
    """Allowed value parameters
    the values are evaluated in literal validator functions

    :param pyqgiswps.validator.allowed_value.ALLOWEDVALUETYPE allowed_type: VALUE or RANGE
    :param values: list of allowed values
    :param minval: minimal value in case of Range
    :param maxval: maximal value in case of Range
    :param spacing: spacing in case of Range
    :param pyqgiswps.input.literaltypes.RANGECLOSURETYPE range_closure:
    """

    def __init__(
        self,
        allowed_type: ALLOWEDVALUETYPE = ALLOWEDVALUETYPE.VALUE,
        values: Optional[List[LiteralInputValue]] = None,
        minval: Optional[LiteralInputValue] = None,
        maxval: Optional[LiteralInputValue] = None,
        spacing: Optional[LiteralNumeric] = None,
        range_closure: RANGECLOSURETYPE = RANGECLOSURETYPE.CLOSED,
    ):
        AnyValue.__init__(self)

        self.allowed_type = allowed_type
        self.values = values
        self.minval = minval
        self.maxval = maxval
        self.spacing = spacing
        self.range_closure = range_closure

    @property
    def is_range(self):
        return self.allowed_type == ALLOWEDVALUETYPE.RANGE

    @property
    def json(self) -> JsonValue:
        if self.values:
            values = [to_json_serializable(value) for value in self.values]
        else:
            values = None
        return {
            'type': 'allowedvalues',
            'allowed_type': self.allowed_type,
            'values': values,
            'minval': to_json_serializable(self.minval),
            'maxval': to_json_serializable(self.maxval),
            'spacing': self.spacing,
            'range_closure': self.range_closure,
        }

    @staticmethod
    def positiveValue() -> Self:
        """ Define range for value > 0 """
        return AllowedValues(
            ALLOWEDVALUETYPE.RANGE,
            minval=0,
            range_closure=RANGECLOSURETYPE.OPEN,
        )

    @staticmethod
    def nonNegativeValue() -> Self:
        """ Define range for value >= 0 """
        return AllowedValues(
            ALLOWEDVALUETYPE.RANGE,
            minval=0,
            range_closure=RANGECLOSURETYPE.CLOSED,
        )

    @staticmethod
    def range(
        minval: LiteralInputValue,
        maxval: LiteralInputValue,
        spacing: Optional[LiteralNumeric] = None,
        range_closure: RANGECLOSURETYPE = RANGECLOSURETYPE.CLOSED,
    ) -> Self:
        """ Define range of values """
        return AllowedValues(
            ALLOWEDVALUETYPE.RANGE,
            minval=minval,
            maxval=maxval,
            spacing=spacing,
            range_closure=range_closure,
        )


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
        elif data_type == 'length':
            convert = convert_float
    else:
        raise InvalidParameterValue(
            f"Invalid data_type value of LiteralInput set to '{data_type}'")
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
            f'The value "{inpt}" does not seem to be of type anyURI')


def convert_time(inpt: LiteralInputValue) -> datetime.time:
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


def convert_datetime(inpt: LiteralInputValue) -> datetime.datetime:
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


def is_anyvalue(value: Any) -> bool:
    """Check for any value object of given value
    """
    return (value == AnyValue) or (value is None) or isinstance(value, AnyValue)
