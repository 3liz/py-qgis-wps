##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

"""Unit tests for literal validator
"""

import unittest
from qywps.validator.literalvalidator import *
from qywps.inout.literaltypes import AllowedValue

def get_input(allowed_values, data = 1):

    class FakeInput(object):
        data = 1
        data_type = 'data'


    fake_input = FakeInput()
    fake_input.data = data
    fake_input.allowed_values = allowed_values

    return fake_input


class ValidateTest(unittest.TestCase):
    """Literal validator test cases"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_anyvalue_validator(self):
        """Test anyvalue validator"""
        inpt = get_input(allowed_values = None)
        self.assertTrue(validate_anyvalue(inpt, MODE.NONE))

    def test_allowedvalues_values_validator(self):
        """Test allowed values - values"""
        allowed_value = AllowedValue()
        allowed_value.allowed_type = ALLOWEDVALUETYPE.VALUE
        allowed_value.value = 1

        inpt = get_input(allowed_values = [allowed_value])
        self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE), 'Allowed value 1 allowed')

        inpt.data = 2
        self.assertFalse(validate_allowed_values(inpt, MODE.SIMPLE), 'Allowed value 2 NOT allowed')

    def test_allowedvalues_ranges_validator(self):
        """Test allowed values - ranges"""

        allowed_value = AllowedValue()
        allowed_value.allowed_type = ALLOWEDVALUETYPE.RANGE
        allowed_value.minval = 1
        allowed_value.maxval = 11
        allowed_value.spacing = 2
        allowed_value.range_closure = RANGECLOSURETYPE.CLOSED

        inpt = get_input(allowed_values = [allowed_value])

        inpt.data = 1
        self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE), 'Range CLOSED closure')

        inpt.data = 12
        self.assertFalse(validate_allowed_values(inpt, MODE.SIMPLE), 'Value too big')

        inpt.data = 5
        self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE), 'Spacing not fit')

        inpt.data = 4
        self.assertFalse(validate_allowed_values(inpt, MODE.SIMPLE), 'Spacing fits')

        inpt.data = 11
        allowed_value.range_closure = RANGECLOSURETYPE.CLOSED
        self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE), 'Open Range')

        allowed_value.range_closure = RANGECLOSURETYPE.CLOSEDOPEN
        self.assertFalse(validate_allowed_values(inpt, MODE.SIMPLE), 'CLOSEDOPEN Range')

        inpt.data = 1
        allowed_value.range_closure = RANGECLOSURETYPE.OPENCLOSED
        self.assertFalse(validate_allowed_values(inpt, MODE.SIMPLE), 'OPENCLOSED Range')

    def test_combined_validator(self):
        """Test allowed values - ranges and values combination"""

        allowed_value1 = AllowedValue()
        allowed_value1.allowed_type = ALLOWEDVALUETYPE.RANGE
        allowed_value1.minval = 1
        allowed_value1.maxval = 11
        allowed_value1.spacing = 2
        allowed_value1.range_closure = RANGECLOSURETYPE.CLOSED

        allowed_value2 = AllowedValue()
        allowed_value2.allowed_type = ALLOWEDVALUETYPE.VALUE
        allowed_value2.value = 15

        inpt = get_input(allowed_values = [allowed_value1, allowed_value2])

        inpt.data = 1
        self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE), 'Range CLOSED closure')

        inpt.data = 15
        self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE), 'AllowedValue')

        inpt.data = 13
        self.assertFalse(validate_allowed_values(inpt, MODE.SIMPLE), 'Out of range')



def load_tests(loader=None, tests=None, pattern=None):
    if not loader:
        loader = unittest.TestLoader()
    suite_list = [
        loader.loadTestsFromTestCase(ValidateTest)
    ]
    return unittest.TestSuite(suite_list)
