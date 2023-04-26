##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

"""Unit tests for literal validator
"""

from pyqgiswps.validator.literalvalidator import *
from pyqgiswps.inout.literaltypes import AllowedValues

def get_input(allowed_values, data = 1):

    class FakeInput:
        data = 1
        data_type = 'data'


    fake_input = FakeInput()
    fake_input.data = data
    fake_input.allowed_values = allowed_values

    return fake_input


def test_anyvalue_validator():
    """ Test anyvalue validator"""
    inpt = get_input(allowed_values = None)
    assert validate_anyvalue(inpt, MODE.NONE)


def test_allowedvalues_values_validator():
    """Test allowed values - values"""
    allowed_value = AllowedValues()
    allowed_value.allowed_type = ALLOWEDVALUETYPE.VALUE
    allowed_value.values = [1]

    inpt = get_input(allowed_values=allowed_value)
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Allowed value 1 allowed'

    inpt.data = 2
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'Allowed value 2 NOT allowed'


def test_allowedvalues_ranges_validator():
    """ Test allowed values - ranges"""

    allowed_value = AllowedValues()
    allowed_value.allowed_type = ALLOWEDVALUETYPE.RANGE
    allowed_value.minval = 1
    allowed_value.maxval = 11
    allowed_value.spacing = 2
    allowed_value.range_closure = RANGECLOSURETYPE.CLOSED

    inpt = get_input(allowed_values=allowed_value)

    inpt.data = 1
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Range CLOSED closure'

    inpt.data = 12
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'Value too big'

    inpt.data = 5
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Spacing not fit'

    inpt.data = 4
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'Spacing fits'

    inpt.data = 11
    allowed_value.range_closure = RANGECLOSURETYPE.CLOSED
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Open Range'

    allowed_value.range_closure = RANGECLOSURETYPE.CLOSEDOPEN
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'CLOSEDOPEN Range'

    inpt.data = 1
    allowed_value.range_closure = RANGECLOSURETYPE.OPENCLOSED
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'OPENCLOSED Range'


def test_allowed_partial_range_validator():
    """ Test partial range """
    allowed_value = AllowedValues()
    allowed_value.allowed_type = ALLOWEDVALUETYPE.RANGE
    allowed_value.minval = 1
    allowed_value.spacing = 2
    allowed_value.range_closure = RANGECLOSURETYPE.CLOSED

    inpt = get_input(allowed_values=allowed_value)

    inpt.data = 1
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Range CLOSED closure'

    inpt.data = 13
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Value too big'

    inpt.data = 5
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Spacing not fit'

    inpt.data = 4
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'Spacing fits'

    inpt.data = 1
    allowed_value.range_closure = RANGECLOSURETYPE.OPENCLOSED
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'OPENCLOSED Range'

    allowed_value.minval = None
    allowed_value.maxval = 11
 
    inpt.data = -1
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Value too small'

    inpt.data = 12
    assert not validate_allowed_values(inpt, MODE.SIMPLE), 'Value too big'

    inpt.data = 11
    allowed_value.range_closure = RANGECLOSURETYPE.CLOSED
    assert validate_allowed_values(inpt, MODE.SIMPLE), 'Open Range'
