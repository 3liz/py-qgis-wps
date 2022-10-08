#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import logging
import uuid

from tornado.escape import xhtml_escape as escape

from .basehandler import HTTPError, BaseHandler

from pyqgiswps.exceptions import (NoApplicableCode, 
                                  InvalidParameterValue, 
                                  OperationNotSupported)

from pyqgiswps.ogc.ows.request import OWSRequest

from typing import Optional

LOGGER = logging.getLogger('SRVLOG')


class OWSHandler(BaseHandler):
    """ Handle WPS requests
    """
    def initialize(self, access_policy, service_url):
        super().initialize()

        self.service_url = service_url
        self.accesspolicy = access_policy

    def get_job_realm(self):
        """ Get or create a job realm token
        """
        realm = self.request.headers.get('X-Job-Realm')
        # Generate new token
        if realm is None:
            realm = uuid.uuid4().hex
        return realm

    async def handle_wps_request(self, method_parser):
        """ Handle a wps request
        """
        wpsrequest = method_parser(self)

        wpsrequest.map_uri  = self.get_argument('MAP', default=None)
        wpsrequest.host_url = self.proxy_url()

        # Check for service url
        wpsrequest.service_url = self.service_url \
            or self.request.headers.get('X-Qgis-Wps-Service-Url', default=None) \
            or self.request.headers.get('X-Qgis-Service-Url', default=None) \
            or f"{wpsrequest.host_url}ows/"

        service = self.application.wpsservice
        LOGGER.debug('Request: %s', wpsrequest.operation)

        if wpsrequest.operation == 'getresults':
            response = service.get_results(wpsrequest.results_uuid)

        elif wpsrequest.operation == 'getcapabilities':
            response = wpsrequest.get_capabilities(service, self.accesspolicy)

        elif wpsrequest.operation == 'describeprocess':
            if any( not self.accesspolicy.allow(ident) for ident in wpsrequest.identifiers ):
                raise HTTPError(403,reason="Unauthorized operation")
            response = wpsrequest.describe(service, map_uri=wpsrequest.map_uri)

        elif wpsrequest.operation == 'execute':
            if not self.accesspolicy.allow(wpsrequest.identifier):
                raise HTTPError(403,reason="Unauthorized operation")

            job_id = uuid.uuid1()

            # Assign job realm
            wpsrequest.realm = self.get_job_realm()
            wpsrequest.status_uuid = job_id

            # Canonical status link
            wpsrequest.status_link = f"/ows/?service=WPS&request=GetResults&uuid={job_id}"

            response = await wpsrequest.execute(service, job_id, map_uri=wpsrequest.map_uri)

            # Return job realm
            self.set_header('X-Job-Realm', wpsrequest.realm)
        else:
            raise OperationNotSupported("Unknown operation %r" % wpsrequest.operation)

        return response

    async def get(self):
        """ Handle Get Method
        """
        service = self.get_argument('SERVICE')
        if service.lower() != 'wps':
            raise InvalidParameterValue('parameter SERVICE [%s] not supported' % service, 'service')

        document = await self.handle_wps_request(OWSRequest.parse_get_request)

        self.write_xml(document)

    async def post(self):
        """ Handle POST method

            XXX Do not forget to set the max_buffer_size in HTTPServer arguments
            see http://www.tornadoweb.org/en/stable/tcpserver.html?highlight=max_buffer_size
        """
        document = await self.handle_wps_request(OWSRequest.parse_post_request)
        
        self.write_xml(document)

    def options(self, endpoint: Optional[str]=None) -> None:
        """ Implement OPTION for validating CORS
        """
        self.set_option_headers('GET, POST, OPTIONS')

    def format_exception(self, exc: NoApplicableCode) -> None:
        """ Override
            Format exception  as XML response
        """
        if exc.description:
            description = f'<ows:ExceptionText>{escape(exc.description)}</ows:ExceptionText>'
        else:
            description = ''
        
        body = (  # noqa
            '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/ows/1.1 http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd" version="1.0.0">\n'
            '  <ows:Exception exceptionCode="%(name)s" locator="%(locator)s" >\n'
            '      %(description)s\n'
            '  </ows:Exception>\n'
            '</ows:ExceptionReport>'
        ) % {
            'code': exc.code,
            'locator': escape(exc.locator),
            'name': escape(exc.name),
            'description': description
        }

        self.write_xml(body)
