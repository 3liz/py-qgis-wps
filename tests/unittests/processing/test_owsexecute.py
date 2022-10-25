"""
    Test Processing executor
"""
import pytest
from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase
from pyqgiswps.executors.processfactory import get_process_factory

# XXX With EPSG:4326 axes *MUST* be inverted
INPUTGEOMETRY_EXECUTE_POST="""<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
    xmlns="http://www.opengis.net/wps/1.0.0" 
    xmlns:wfs="http://www.opengis.net/wfs" 
    xmlns:wps="http://www.opengis.net/wps/1.0.0" 
    xmlns:ows="http://www.opengis.net/ows/1.1" 
    xmlns:gml="http://www.opengis.net/gml" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:wcs="http://www.opengis.net/wcs/1.1.1" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>{PROVIDER}:testinputgeometry</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier>INPUT</ows:Identifier>
      <wps:Data>
        <wps:ComplexData mimeType="application/wkt" encoding="utf-8" schema=""><![CDATA[{DATA}]]></wps:ComplexData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
</wps:Execute>
"""


class TestsInputGeometry(HTTPTestCase):

    def get_processes(self):
        return get_process_factory()._create_qgis_processes()

    def test_input_geometry_execute_post(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&MAP=raster_layer')
        body = INPUTGEOMETRY_EXECUTE_POST.format(
                PROVIDER='pyqgiswps_test',
                DATA='CRS=4326;POINT(-4 48)'
        )
        rv = self.client.post(body, path=uri)
        assert rv.status_code == 200

