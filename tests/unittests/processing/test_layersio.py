"""
    Test Processing file io
"""
import pytest

from urllib.parse import urlparse, parse_qs, urlencode

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

from pyqgiswps.executors.processingprocess import (
            MapContext, 
            ProcessingContext,
            _find_algorithm
        )

from pyqgiswps.exceptions import (NoApplicableCode,
                                  InvalidParameterValue,
                                  MissingParameterValue,
                                  ProcessException)


def test_layer_scheme():
    """ Test arbitrary layer scheme deos not trig an error
    """
    param = QgsProcessingParameterVectorLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "layer:layername"

    context = QgsProcessingContext()

    value = layersio.get_processing_value( param, [inp], context)
    assert value == "layername"


def test_arbitrary_layer_scheme():
    """ Test arbitrary layer scheme deos not trig an error
    """
    param = QgsProcessingParameterVectorLayer("LAYER", "")

    inp = parse_input_definition(param)
    inp.data = "foobar:layername"

    context = QgsProcessingContext()

    value = layersio.get_processing_value( param, [inp], context)
    assert value == "foobar:layername"


def test_multilayer_with_selection():
    """ Test map context return allowed layers
    """
    alg = _find_algorithm('pyqgiswps_test:testinputmultilayer')
    context = MapContext('france_parts.qgs')
    inputs  = { p.name(): [parse_input_definition(p,alg,context)] for p in  alg.parameterDefinitions() }

    inpt = inputs['INPUT'][0]
    allowed_values = { v.value for v in inpt.allowed_values }

    assert 'france_parts' in allowed_values
    data = 'layer:france_parts?'+urlencode((('select','OBJECTID=2662 OR OBJECTID=2664'),))

    inpt.data = data
    #self.assertTrue(validate_allowed_values(inpt, MODE.SIMPLE))    

