#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import os
import asyncio
import mimetypes
import logging
import uuid

from urllib.parse import urljoin

from .basehandler import BaseHandler
from ..exceptions import NoApplicableCode, InvalidParameterValue, OperationNotSupported

from ..app.WPSRequest import WPSRequest

LOGGER = logging.getLogger('SRVLOG')


class WPSHandler(BaseHandler):
    """ Handle WPS requests
    """
    def initialize(self, filters=None):
        super().initialize()
    
        self._filters = filters or []

    async def prepare(self):
        # Handle filters
        super().prepare()
        for filt in self._filters:
            await filt.apply( self )

    async def handle_wps_request(self, method_parser):
        """ Handle a wps request
        """
        http_request = self.request
        wpsrequest   = method_parser(self)

        wpsrequest.map_uri  = self.get_argument('MAP', default=None)
        wpsrequest.host_url = self.proxy_url()

        service = self.application.wpsservice
        LOGGER.debug('Request: %s', wpsrequest.operation)

        if wpsrequest.operation == 'getresults':
            response = service.get_results(wpsrequest.results_uuid)

        elif wpsrequest.operation == 'getcapabilities':
            response = service.get_capabilities(wpsrequest)

        elif wpsrequest.operation == 'describeprocess':
            response = service.describe(wpsrequest.identifiers, map_uri=wpsrequest.map_uri)

        elif wpsrequest.operation == 'execute':
            request_uuid = uuid.uuid1()
            response = await service.execute(
                wpsrequest.identifier,
                wpsrequest,
                request_uuid,
                # Context
                map_uri=wpsrequest.map_uri,
            )
        else:
            raise OperationNotSupported("Unknown operation %r" % wpsrequest.operation)

        return response
 
    async def get(self):
        """ Handle Get Method
        """
        service = self.get_argument('SERVICE')
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


class StatusHandler(BaseHandler):

    def get_wps_status( self, uuid=None):
        """ Return the status of the processes
        """ 
        wps_status = self.application.wpsservice.get_status(uuid)
        if uuid is not None and wps_status is None:
            self.set_status(404)
            self.write_json({ 'error': 'process %s not found' % uuid })
            return

        # Replace the status url with the proxy_url if any
        proxy_url = self.proxy_url()

        # Add additional informations
        cfg = self.application.config
        def repl( s ):
            s['status_url'] = cfg['status_url'].format(host_url=proxy_url, uuid=s['uuid'])
            s['store_url']  = cfg['store_url'].format(host_url=proxy_url, uuid=s['uuid'], file="")
            s['request']    = "{host_url}status/{uuid}?key=request".format(host_url=proxy_url, uuid=s['uuid'])
            return s

        if uuid is not None:
            wps_status = repl(wps_status)
        else:
            wps_status = list(map(repl, wps_status))
        
        self.write_json({ 'status': wps_status })

    def get_wps_request( self, uuid ):
        """ Return request infos
        """
        if uuid is None:
            self.set_status(400)
            self.write_json({ 'error': 'Missing uuid' })
            return

        wps_request = self.application.wpsservice.get_status(uuid, key='request')
        if uuid is not None and wps_request is None:
            self.set_status(404)
            self.write_json({ 'error': 'request %s not found' % uuid })
            return

        self.write_json({'request': wps_request})        

    def get( self, uuid=None):
        """ Return status infos
        """
        key = self.get_argument('KEY', default=None)
        if key == 'request':
            self.get_wps_request(uuid)
        else:
            self.get_wps_status(uuid)

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

        

