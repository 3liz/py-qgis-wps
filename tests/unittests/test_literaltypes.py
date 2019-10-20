"""Unit tests for IOs
"""
##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import datetime
import pytest
from qywps.inout.literaltypes import *


def test_integer():
    """Test integer convertor"""
    assert convert_integer('1.0') == 1
    assert convert_integer(1) == 1
    with pytest.raises(ValueError):
        convert_integer('a')


def test_float():
    """Test float convertor"""
    assert convert_float('1.0') == 1.0
    assert convert_float(1) == 1.0
    with pytest.raises(ValueError):
        convert_float('a')


def test_string():
    """Test string convertor"""
    assert convert_string('1.0') == '1.0'
    assert convert_string(1) == '1'
    assert convert_string('a') == 'a'


def test_boolean():
    """Test boolean convertor"""
    assert convert_boolean('1.0')
    assert convert_boolean(1)
    assert convert_boolean('a')
    assert not convert_boolean('f')
    assert not convert_boolean('falSe')
    assert not convert_boolean(False)
    assert not convert_boolean(0)
    assert convert_boolean(-1)


def test_time():
    """Test time convertor"""
    assert convert_time("12:00:00") ==  datetime.time(12, 0, 0)
    assert isinstance( convert_time(datetime.time(14)), datetime.time)


def test_date():
    """Test date convertor"""
    assert convert_date("2011-07-21") == datetime.date(2011, 7, 21)
    assert isinstance( convert_date(datetime.date(2012, 12, 31)), datetime.date)


def test_datetime():
    """Test datetime convertor"""
    assert convert_datetime("2016-09-22T12:00:00") == datetime.datetime(2016, 9, 22, 12)
    assert isinstance(convert_datetime("2016-09-22T12:00:00Z"), datetime.datetime)
    assert isinstance(convert_datetime("2016-09-22T12:00:00+01:00"), datetime.datetime)
    assert isinstance(convert_datetime(datetime.datetime(2016, 9, 22, 6)), datetime.datetime)

