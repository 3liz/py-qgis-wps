"""
    Test Processing file io
"""
import pytest

from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase, assert_response_accepted
from time import sleep
from test_common import async_test

from qgis.core import (QgsProcessingContext,
                       QgsProcessingParameterVectorLayer)


from pyqgiswps.executors.io import layersio
from pyqgiswps.executors.processingio import(
            parse_input_definition,
            parse_output_definition,
        )

from pyqgiswps.exceptions import (NoApplicableCode,
                                  InvalidParameterValue,
                                  MissingParameterValue,
                                  ProcessException)


def test_invalidparameter_value():
    """ Test invalid layer scheme
    """
    param = QgsProcessingParameterVectorLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "badscheme:foobar"

    context = QgsProcessingContext()

    with pytest.raises(InvalidParameterValue):
        value = layersio.get_processing_value( param, [inp], context)




