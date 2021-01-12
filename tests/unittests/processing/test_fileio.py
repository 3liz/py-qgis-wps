"""
    Test Processing file io
"""
import pytest
from pathlib import Path

from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase, assert_response_accepted
from pyqgiswps.executors.io import filesio

from pyqgiswps.inout import (LiteralInput, 
                             ComplexInput,
                             LiteralOutput, 
                             ComplexOutput)

from time import sleep
from test_common import async_test

from qgis.core import (QgsProcessingContext,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFileDestination)


from pyqgiswps.executors.io import filesio
from pyqgiswps.executors.processingio import(
            parse_input_definition,
            parse_output_definition,
        )


class TestsFileIO(HTTPTestCase):

    def test_output_file_reference(self):
        """ Test output file as reference
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testfiledestination&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=OUTPUT=my_file_output')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200


    def test_output_file_describeprocess(self):
        """ Test output file
        """
        uri = ('/ows/?service=WPS&request=DescribeProcess&Identifier=pyqgiswps_test:testoutputfile&Version=1.0.0')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200


    def test_output_file(self):
        """ Test output file
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testoutputfile&Version=1.0.0')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200

        output = rv.xpath('/wps:ExecuteResponse'
                          '/wps:ProcessOutputs'
                          '/wps:Output'
                          '/wps:Reference')

        assert len(output) == 1
        assert output[0].get('mimeType') == "application/json"

def test_file_destination_io():
    """
    """
    param = QgsProcessingParameterFileDestination("FILE", fileFilter="CSV Files (*.csv)")

    assert param.defaultFileExtension() == 'csv'

    inp = parse_input_definition(param)
    inp.data = "foobar"

    context = QgsProcessingContext()
    value = filesio.get_processing_value( param, [inp], context)

    assert value == 'foobar.csv'


def test_file_input( outputdir ):
    """ Test file parameter
    """
    param = QgsProcessingParameterFile("FILE", extension=".txt")

    inp = parse_input_definition(param)

    assert isinstance(inp,ComplexInput)
    assert inp.as_reference == False

    inp.data = "Hello world"

    context = QgsProcessingContext()
    context.workdir = str(outputdir)

    value = filesio.get_processing_value( param, [inp], context)

    outputpath = (Path(context.workdir)/param.name()).with_suffix(param.extension())
    assert value == outputpath.name
    assert outputpath.exists()
    
    with outputpath.open('r') as f:
        assert f.read() == inp.data

