"""
    Test Processing executor
"""
from pyqgiswps.app import WPSProcess, Service
from pyqgiswps.tests import HTTPTestCase
from pyqgiswps.executors.processingexecutor import ProcessingExecutor


class TestsClipRaster(HTTPTestCase):

    def test_execute_request_get(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcliprasterlayer&Version=1.0.0'
                               '&MAP=raster_layer&DATAINPUTS=INPUT=raster_layer%3BEXTENT=-112,20,-87,45%3BOUTPUT=clipped_layer')
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.get(uri, path='')
        # TODO FIXME error in parsing BoundingBox
        assert rv.status_code == 200

    def test_execute_request_post(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&MAP=raster_layer')
        body = """<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>pyqgiswps_test:testcliprasterlayer</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
    <wps:Input>
      <ows:Identifier>INPUT</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>raster_layer</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>EXTENT</ows:Identifier>
      <wps:Data>
        <wps:BoundingBoxData crs="EPSG:4326" dimenstions="2">
            <ows:LowerCorner>-112 20</ows:LowerCorner>
            <ows:UpperCorner>-87 45</ows:UpperCorner>
        </wps:BoundingBoxData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>OUTPUT</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>clipped_layer</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
</wps:Execute>
        """
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.post(body, path=uri)
        # TODO FIXME error in parsing BoundingBox
        assert rv.status_code == 200


    def test_script_execute_request_get(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=script:testcliprasterlayer&Version=1.0.0'
                               '&MAP=raster_layer&DATAINPUTS=INPUT=raster_layer%3BEXTENT=-112,20,-87,45%3BOUTPUT=clipped_layer')
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.get(uri, path='')
        # TODO FIXME error in parsing BoundingBox
        assert rv.status_code == 200

    def test_script_execute_request_post(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&MAP=raster_layer')
        body = """<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>script:testcliprasterlayer</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
    <wps:Input>
      <ows:Identifier>INPUT</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>raster_layer</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>EXTENT</ows:Identifier>
      <wps:Data>
        <wps:BoundingBoxData crs="EPSG:4326" dimenstions="2">
            <ows:LowerCorner>-112 20</ows:LowerCorner>
            <ows:UpperCorner>-87 45</ows:UpperCorner>
        </wps:BoundingBoxData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>OUTPUT</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>clipped_layer</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
</wps:Execute>
        """
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.post(body, path=uri)
        # TODO FIXME error in parsing BoundingBox
        assert rv.status_code == 200


    def test_model_execute_request_get(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=model:testcliprasterlayer&Version=1.0.0'
                               '&MAP=raster_layer&DATAINPUTS=INPUT=raster_layer%3BEXTENT=-112,20,-87,45%3BOUTPUT=clipped_layer')
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.get(uri, path='')
        # TODO FIXME error in parsing BoundingBox
        assert rv.status_code == 200

