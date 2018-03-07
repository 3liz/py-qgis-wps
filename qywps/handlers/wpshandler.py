##################################################################
# Copyright 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import os
import asyncio
import mimetypes
import logging
import uuid

from urllib.parse import urljoin

from .basehandler import BaseHandler
from ..exceptions import NoApplicableCode, InvalidParameterValue, OperationNotSupported

from ..app.WPSRequest import WPSRequest

LOGGER = logging.getLogger("QYWPS")


class WPSHandler(BaseHandler):
    """ Handle WPS requests
    """
    async def handle_wps_request(self, method_parser):
        """ Handle a wps request
        """
        http_request = self.request
        wpsrequest   = method_parser(self)

        wpsrequest.map_uri = self.get_query_argument('map', default=None)
        host_url = http_request.headers.get('X-Proxy-Location')
        if not host_url:
            host_url = urljoin(http_request.protocol + "://" + http_request.host,  http_request.path)
        
        wpsrequest.host_url = host_url

        service = self.application.wpsservice
        LOGGER.debug('Request: %s', wpsrequest.operation)

        if wpsrequest.operation == 'getresults':
            response = service.get_results(wpsrequest.results_uuid)

        elif wpsrequest.operation == 'getcapabilities':
            response = service.get_capabilities(wpsrequest)

        elif wpsrequest.operation == 'describeprocess':
            response = service.describe(wpsrequest.identifiers)

        elif wpsrequest.operation == 'execute':
            request_uuid = uuid.uuid1()
            response = await service.execute(
                wpsrequest.identifier,
                wpsrequest,
                request_uuid
            )
        else:
            raise OperationNotSupported("Unknown operation %r" % wpsrequest.operation)

        return response
 
    async def get(self):
        """ Handle Get Method
        """
        service = self.get_query_argument('service')
        if service.lower() != 'wps':
            raise InvalidParameterValue('parameter SERVICE [%s] not supported' % service, 'service')

        document = await self.handle_wps_request(WPSRequest.parse_get_request)

        self.write_xml(document)

    async def post(self):
        """ Handle POST method

            XXX Do not forget to set the max_buffer_size in HTTPServer arguments
            see http://www.tornadoweb.org/en/stable/tcpserver.html?highlight=max_buffer_size
        """
        document = await self.handle_wps_request(WPSRequest.parse_post_request)
        
        self.write_xml(document)



class StoreHandler(BaseHandler):
    """ Handle WPS requests
    """
    def initialize(self, workdir, chunk_size=65536):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir    = workdir

    def get_full_path(uuid, filename):
        return os.path.join

    def prepare(self):
        service = self.get_query_argument('service')
        if service.lower() != 'wps':
            raise InvalidParameterValue('parameter SERVICE [%s] not supported' % service, 'service')

    async def get(self, uuid, filename):
        """ Return output file from process working dir
        """
        full_path  = os.path.join(self._workdir, uuid, filename)
        if not os.path.isfile(full_path):
            LOGGER.error("File '%s' not found", full_path)
            raise NoApplicableCode("The resource does not exists", code=404)

        # The resource is asked again, just tell that it is
        # not modified
        if self.request.headers.get("If-Modified-Since"):
            self.set_status(304)
            return

        if self.request.headers.get('If-None-Match') == uuid:
            self.set_header('Etag', uuid)
            self.set_status(304)
            return

        # Set headers
        content_type = mimetypes.types_map.get(os.path.splitext(full_path)[1]) or "application/octet-stream"
        self.set_header("Content-Type", content_type)       
        self.set_header("Etag", uuid)

        # Set aggresive browser caching since the resource
        # is not going to change
        self.set_header("Cache-Control", "max-age=" + str(86400*365*10))

        # Push data
        chunk_size = self._chunk_size
        with open(full_path,'rb') as fp:
            while True:
                chunk = fp.read(chunk_size)
                if chunk:
                    self.write(chunk)
                    await self.flush()
                else:
                    break


class StatusHandler(BaseHandler):

    def get( self, uuid=None):
        """ Return the status of the processes
        """
        wps_status = self.application.wpsservice.get_status(uuid)
        if uuid is not None and wps_status is None:
            self.set_status(404)
            data = { 'error': 'process %s not found' % uuid } 
        else:
            data = { 'status': wps_status }

        self.write_json(data) 

    def delete( self, uuid=None ):
        """ Delete results
        """
        data = None
        if uuid is None:
            self.set_status(400)
            self.write_json({ 'error': 'Missing uuid' })
            return
        try:
            success = self.application.wpsservice.delete_results(uuid)
            if not success:
                self.set_status(409) # 409 == Conflict
        except FileNotFoundError:
             self.set_status(404)

        

