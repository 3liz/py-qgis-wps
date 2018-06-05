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

from qywps.validator.mode import MODE
from qywps.validator.allowed_value import ALLOWEDVALUETYPE, RANGECLOSURETYPE


LOGGER = logging.getLogger('QYWPS')


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

        LOGGER.debug('validating allowed values: %s in %s', data, data_input.allowed_values)
        for value in data_input.allowed_values:

            if value.allowed_type == ALLOWEDVALUETYPE.VALUE:
                passed = _validate_value(value, data)

            elif value.allowed_type == ALLOWEDVALUETYPE.RANGE:
                passed = _validate_range(value, data)

            if passed is True:
                break

    LOGGER.debug('validation result: %r', passed)
    return passed


def _validate_value(value, data):
    """Validate data against given value directly

    :param value: list or tupple with allowed data
    :param data: the data itself (string or number)
    """

    passed = False
    if data == value.value:
        passed = True

    return passed


def _validate_range(interval, data):
    """Validate data against given range
    """

    passed = False

    LOGGER.debug('validating range: %s (%s) in %r', data, type(data), interval)
    if interval.minval <= data <= interval.maxval:

        if interval.spacing:
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

    LOGGER.debug('validation result: %r', passed)
    return passed
