"""
    Test Processing executor
"""
import pytest
from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase
from pyqgiswps.executors.processfactory import get_process_factory

# XXX With EPSG:4326 axes *MUST* be inverted
CLIPRASTER_EXECUTE_POST="""<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>{PROVIDER}:testcliprasterlayer</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier>{INPUT}</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>raster_layer</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>{EXTENT}</ows:Identifier>
      <wps:Data>
        <wps:BoundingBoxData crs="EPSG:4326" dimenstions="2">
            <ows:LowerCorner>20 -112</ows:LowerCorner>
            <ows:UpperCorner>45 -87</ows:UpperCorner>
        </wps:BoundingBoxData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>{OUTPUT}</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>clipped_layer</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
</wps:Execute>
"""


class TestsClipRaster(HTTPTestCase):

    def get_processes(self):
        return get_process_factory()._create_qgis_processes()

    #XXX Bounding box not supported as kvp
    def test_clipbyextent_get( self ):
        """  Test execute process """

        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcliprasterlayer&Version=1.0.0'
                               '&MAP=raster_layer&DATAINPUTS='
                               'INPUT=raster_layer%3B'
                               'EXTENT=-112,20,-87,45%3B'
                               'OUTPUT=clipped_layer')

        rv = self.client.get(uri, path='')
        assert rv.status_code == 400

    def test_execute_request_post(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&MAP=raster_layer')
        body = CLIPRASTER_EXECUTE_POST.format(PROVIDER='pyqgiswps_test',INPUT='INPUT',EXTENT='EXTENT',OUTPUT='OUTPUT')
        rv = self.client.post(body, path=uri)
        assert rv.status_code == 200

    def test_script_execute_request_post(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&MAP=raster_layer')
        body = CLIPRASTER_EXECUTE_POST.format(PROVIDER='script',INPUT='INPUT',EXTENT='EXTENT',OUTPUT='OUTPUT')
        rv = self.client.post(body, path=uri)
        assert rv.status_code == 200

    def test_model_execute_request_post(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&MAP=raster_layer')
        body = CLIPRASTER_EXECUTE_POST.format(PROVIDER='model',INPUT='input',EXTENT='extent',OUTPUT='gdal:cliprasterbyextent_1:OUTPUT')
        rv = self.client.post(body, path=uri)
        assert rv.status_code == 200

