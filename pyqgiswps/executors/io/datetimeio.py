#
# Copyright 2020 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Handle datetime
"""
import logging

from pyqgiswps.inout import LiteralInput
from pyqgiswps.inout.literaltypes import AllowedValues, convert_time

from qgis.PyQt.QtCore import Qt, QDateTime, QDate, QTime
from qgis.core import (QgsProcessingParameterDefinition,
                       QgsProcessingParameterDateTime)

from ..processingcontext import ProcessingContext

from datetime import datetime
from typing import Any

LOGGER = logging.getLogger('SRVLOG')


# ------------------------------------
# Processing parameters ->  WPS input
# ------------------------------------

def parse_input_definition(param: QgsProcessingParameterDefinition, kwargs) -> LiteralInput:
    """ Convert processing input to File Input
    """
    typ = param.type()
    if typ != 'datetime':
        return None

    def to_value(qdt):
        return qdt.toPyDateTime() if qdt.isValid() else None

    defval = kwargs['default']

    dtype = param.dataType()
    if dtype == QgsProcessingParameterDateTime.Date:
        kwargs['data_type'] = 'date'
        maxval = (to_value(param.maximum()) or datetime.max).date()
        minval = (to_value(param.minimum()) or datetime.min).date()
        if defval:
            defval = QDateTime(defval).toPyDateTime().date()
    elif dtype == QgsProcessingParameterDateTime.Time:
        kwargs['data_type'] = 'time'
        maxval = (to_value(param.maximum()) or datetime.max).time()
        minval = (to_value(param.minimum()) or datetime.min).time()
        if defval:
            defval = convert_time(defval.toString(Qt.ISODate))
    else:
        kwargs['data_type'] = 'dateTime'
        maxval = to_value(param.maximum()) or datetime.max
        minval = to_value(param.minimum()) or datetime.min
        if defval:
            defval = defval.toPyDateTime()

    kwargs['default'] = defval

    return LiteralInput(allowed_values=AllowedValues.range(minval, maxval), **kwargs)

# --------------------------------------
# WPS inputs ->  processing inputs data
# --------------------------------------


def get_processing_value(param: QgsProcessingParameterDefinition, inp: LiteralInput,
                         context: ProcessingContext) -> Any:
    """ Return processing value from wps inputs

        Processes other inputs than layers
    """
    typ = param.type()
    if typ != 'datetime':
        return None

    value = inp[0].data

    # Convert python datetime to appropriate object
    dtype = param.dataType()
    if dtype == QgsProcessingParameterDateTime.Date:
        value = QDate(value)
    elif dtype == QgsProcessingParameterDateTime.Time:
        value = QTime(value)
    else:
        value = QDateTime(value)

    return value
