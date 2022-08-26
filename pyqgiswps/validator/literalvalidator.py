#
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

""" Validator classes used for LiteralInputs
"""
import logging
from urllib.parse import urlparse

from pyqgiswps.validator.mode import MODE
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE, RANGECLOSURETYPE


LOGGER = logging.getLogger('SRVLOG')


def validate_anyvalue(data_input, mode):
    """Just placeholder, anyvalue is always valid
    """

    return True


def validate_allowed_values(data_input, mode):
    """Validate allowed values
    """

    passed = False
    if mode == MODE.NONE:
        passed = True
    else:
        data = data_input.data
        allowed_values = data_input.allowed_values

        LOGGER.debug('validating allowed values: %s in %s', data, allowed_values.json)
        allowed_type = allowed_values.allowed_type

        if allowed_type == ALLOWEDVALUETYPE.VALUE:
            passed = _validate_value(allowed_values, data)

        elif allowed_type == ALLOWEDVALUETYPE.LAYER:
            passed = _validate_layer(allowed_values, data)

        elif allowed_type == ALLOWEDVALUETYPE.RANGE:
            passed = _validate_range(allowed_values, data)

    LOGGER.debug('validation result: %r', passed)
    return passed


def _validate_value(allowed_values, data):
    """Validate data against given value directly

    :param value: list or tupple with allowed data
    :param data: the data itself (string or number)
    """
    return data in allowed_values.values


def _validate_range_min(interval, data):
    passed = False
    if interval.minval <= data:
        if interval.spacing and isinstance(data, (int, float)):
            spacing = abs(interval.spacing)
            diff = data - interval.minval
            passed = diff % spacing == 0
        else:
            passed = True

        if passed:
            if interval.range_closure in (RANGECLOSURETYPE.CLOSED, RANGECLOSURETYPE.CLOSEDOPEN):
                passed = (interval.minval <= data)
            elif interval.range_closure in (RANGECLOSURETYPE.OPEN, RANGECLOSURETYPE.OPENCLOSED):
                passed = (interval.minval < data)
    else:
        passed = False

    return passed


def _validate_range_max(interval, data):
    """Validate data against given range
    """
    if interval.range_closure in (RANGECLOSURETYPE.CLOSED, RANGECLOSURETYPE.OPENCLOSED):
        passed = (data <= interval.maxval)
    elif interval.range_closure in (RANGECLOSURETYPE.OPEN, RANGECLOSURETYPE.CLOSEDOPEN):
        passed = (data < interval.maxval)
    else:
        passed = False

    return passed


def _validate_range_minmax(interval, data):
    """Validate data against given range
    """
    passed = False

    if interval.minval <= data <= interval.maxval:

        if interval.spacing and isinstance(data, (int, float)):
            spacing = abs(interval.spacing)
            diff = data - interval.minval
            passed = diff % spacing == 0
        else:
            passed = True

        if passed:
            if interval.range_closure == RANGECLOSURETYPE.CLOSED:
                passed = (interval.minval <= data <= interval.maxval)
            elif interval.range_closure == RANGECLOSURETYPE.OPEN:
                passed = (interval.minval < data < interval.maxval)
            elif interval.range_closure == RANGECLOSURETYPE.OPENCLOSED:
                passed = (interval.minval < data <= interval.maxval)
            elif interval.range_closure == RANGECLOSURETYPE.CLOSEDOPEN:
                passed = (interval.minval <= data < interval.maxval)
    else:
        passed = False

    return passed


def _validate_range(interval, data):
    """Validate data against given range
    """
    LOGGER.debug('validating range: %s (%s) in %r', data, type(data), interval)
    if interval.minval is not None and interval.maxval is not None:
        passed = _validate_range_minmax(interval, data)
    elif interval.minval is not None:
        passed = _validate_range_min(interval, data)
    elif interval.maxval is not None:
        passed = _validate_range_max(interval, data)
    else:
        passed = True

    LOGGER.debug('validation result: %r', passed)
    return passed


def _validate_layer(allowed_values, data):
    """Validate data against a layer expression directly

    :param value: list or tuple with allowed data
    :param data: the data itself (string or number)
    """
    if data.find('layer:',0,6) == 0:
        data = urlparse(data).path
   
    return data in allowed_values.values
