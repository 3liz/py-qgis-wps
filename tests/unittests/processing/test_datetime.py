# Copyright 2020 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import datetime

from qgis.core import QgsProcessingContext, QgsProcessingParameterDateTime
from qgis.PyQt.QtCore import QDate, QDateTime, QTime

from pyqgiswps.app.request import WPSRequest
from pyqgiswps.executors.io import datetimeio
from pyqgiswps.executors.processingio import (
    parse_input_definition,
)
from pyqgiswps.inout import LiteralInput
from pyqgiswps.ogc import OGCTYPE
from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE


def test_datetime_input():

    assert 'dateTime' in OGCTYPE

    param = QgsProcessingParameterDateTime("TEST", "DateTime",
                  type=QgsProcessingParameterDateTime.DateTime,
                  defaultValue=QDateTime.currentDateTime())

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "dateTime"
    assert inp.allowed_values.allowed_type == ALLOWEDVALUETYPE.RANGE
    assert isinstance(inp.allowed_values.minval, datetime.datetime)
    assert isinstance(inp.allowed_values.maxval, datetime.datetime)

    assert isinstance(inp.default, datetime.datetime)
    assert inp.default == param.defaultValue().toPyDateTime()

    inp.data = inp.default.isoformat()

    context = QgsProcessingContext()
    value = datetimeio.get_processing_value(param, [inp], context)
    assert isinstance(value, QDateTime)


def test_time_input():
    param = QgsProcessingParameterDateTime("TEST", "Time",
                  type=QgsProcessingParameterDateTime.Time,
                  defaultValue=QTime.currentTime())

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "time"
    assert inp.allowed_values.allowed_type == ALLOWEDVALUETYPE.RANGE
    assert isinstance(inp.allowed_values.minval, datetime.time)
    assert isinstance(inp.allowed_values.maxval, datetime.time)

    assert isinstance(inp.default, datetime.time)

    defval = param.defaultValue()
    assert inp.default.hour == defval.hour()
    assert inp.default.minute == defval.minute()
    assert inp.default.second == defval.second()

    inp.data = inp.default.isoformat()

    context = QgsProcessingContext()
    value = datetimeio.get_processing_value(param, [inp], context)
    assert isinstance(value, QTime)


def test_date_input():
    param = QgsProcessingParameterDateTime("TEST", "Date",
                  type=QgsProcessingParameterDateTime.Date,
                  defaultValue=QDate.currentDate())

    inp = parse_input_definition(param)

    assert isinstance(inp, LiteralInput)
    assert inp.identifier == "TEST"
    assert inp.data_type == "date"
    assert inp.allowed_values.allowed_type == ALLOWEDVALUETYPE.RANGE
    assert isinstance(inp.allowed_values.minval, datetime.date)
    assert isinstance(inp.allowed_values.maxval, datetime.date)

    assert isinstance(inp.default, datetime.date)
    assert inp.default == QDateTime(param.defaultValue()).toPyDateTime().date()

    inp.data = inp.default.isoformat()

    context = QgsProcessingContext()
    value = datetimeio.get_processing_value(param, [inp], context)
    assert isinstance(value, QDate)


def test_datetime_json():

    param = QgsProcessingParameterDateTime("TEST", "Date",
                  type=QgsProcessingParameterDateTime.DateTime,
                  defaultValue=QDateTime.currentDateTime())

    inp = parse_input_definition(param)
    assert isinstance(inp.default, datetime.datetime)

    inp.data = inp.default.isoformat()
    assert isinstance(inp.data, datetime.datetime)

    request = WPSRequest()
    request.inputs = {'datetime': [inp]}

    json = request.json
    assert json['inputs']['datetime'][0]['data'] == inp.default.replace(microsecond=0).isoformat()
