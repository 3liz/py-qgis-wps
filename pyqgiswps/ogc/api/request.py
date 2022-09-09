#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# 
# Original parts are Copyright 2016 OSGeo Foundation,            
# represented by PyWPS Project Steering Committee,               
# and released under MIT license.                                
# Please consult PYWPS_LICENCE.txt for details
#
import logging
import base64

from datetime import datetime

from pyqgiswps.app.request import WPSRequest, WPSResponse
from pyqgiswps.exceptions import (
    InvalidParameterValue,
)
from typing import TypeVar, Optional

from .response import OgcApiResponse, JOBSTATUS

from pyqgiswps.inout import (
    BoundingBoxOutput, 
    BoundingBoxInput, 
    ComplexInput, 
    ComplexOutput, 
    LiteralOutput,
    LiteralInput
)

AccessPolicy = TypeVar('AccessPolicy')
Service      = TypeVar('Service')
UUID         = TypeVar('UUID')
Json         = TypeVar('Json')

LOGGER = logging.getLogger('SRVLOG')

DEFAULT_VERSION = '1.0.0'
SCHEMA_VERSIONS = ('1.0.0',)


class OgcApiRequest(WPSRequest):
   
    # Create response
    def create_response( self, process, uuid, status_url=None) -> OgcApiResponse:
        """ Create the response for execute request for
            handling OGC api Response
        """
        return OgcApiResponse(process, self, uuid, status_url)

    #
    # /processes
    #
    def get_process_list(self, service: Service, accesspolicy: AccessPolicy) -> Json:
        """ Handle getcapbabilities request
        """
        def make_links(js: Json) -> Json:
            js['links'] = [
                {
                    'href': f"{self.host_url}processes/{js['id']}",
                    'rel': "self",
                    'type': "application/json",
                    'title': "Process description",
                },
            ]
            return js

        processes = [make_links(p.ogcapi_process_summary())
                     for p in service.processes if accesspolicy.allow(p.identifier)]

        content = {
            'processes': processes,
            'links': [
                {
                    'href': f"{self.host_url}processes",
                    'rel': "self",
                    'type': "application/json",
                },
            ]
        }
        return content

    #
    # /processes/{id}
    #
    def get_process_description(self, ident: str, service: Service) -> Json:
        
        self.identifiers = [ident]
        process = service.get_processes(self.identifiers, map_uri=self.map_uri)[0]

        content = process.ogcapi_process()
        content['links'] = [
            {
                'href': f"{self.host_url}processes/{ident}/execution",
                'rel': "http://www.opengis.net/def/rel/ogc/1.0/execute",
                'type': "application/json",
                'title': "Execute endpoint",
            },
            {
                'href': f"{self.host_url}processes/{ident}",
                'rel': "self",
                'type': "application/json",
                'title': "Process description"
            },
        ]        
        return content

    #
    # /processes/{id}/execution
    #
    async def execute(self, ident: str, job_id: UUID, doc: Json, service: Service,
                      timeout: Optional[int] = None, 
                      expire: Optional[int] = None,
                      execute_async: bool = True) -> Json:

        # Raise if process is not found
        process = service.get_process(ident, map_uri=self.map_uri)
        
        self.identifier = ident
        self.execute_async = execute_async

        self.check_and_set_timeout(timeout)
        self.check_and_set_expiration(expire)

        def _typeclasses(items):
            return { i.identifier: type(i) for i in items }

        self.inputs = get_inputs_from_document(doc,   _typeclasses(process.inputs))
        self.outputs = get_outputs_from_document(doc, _typeclasses(process.outputs))

        return await service.execute_process(process, self, job_id)

    # Validation

    def check_and_set_timeout(self, timeout: Optional[int]):
        """ Validate timeout parameter
        """
        try:
            if timeout is not None:
                _timeout = int(timeout)
                if _timeout <= 0:
                    raise ValueError()
                self.timeout = min(self.timeout, _timeout)
        except ValueError:
            raise InvalidParameterValue(
                'TIMEOUT param must be an integer > 0 value, not "%s"', 
                timeout) from None

    def check_and_set_expiration(self, expire: Optional[int]):
        """ Validate expiration parameter
        """
        try:
            if expire is not None:
                _expire = int(expire)
                if _expire <= 0:
                    raise ValueError()
                self.expiration = _expire
        except ValueError:
            raise InvalidParameterValue(
                'EXPIRE param must be an integer > 0 value, not "%s"', 
                expire) from None

    # Jobs


    def _create_job_document(self, store) -> Json:
        """ Return job status  
        """
        ident = store['uuid']

        links = [{
            'href': f"{self.host_url}jobs/{ident}",
            'rel': 'self',
            'type': 'application/json',
            'title': "This document"
        }]

        percent_done = store['percent_done']

        # Return creation status
        doc = {
            'jobID': ident,
            'processID': store['identifier'],
            'message': store['message'],
            'created': store['time_start'],
            'type' : 'process',
            'progress': max(0, percent_done),
            'links': links,
        }

        status = WPSResponse.STATUS[store['status']]

        # Must be utc timestamp
        timestamp = store.get('timestamp')
        if timestamp:
            updated = datetime.fromtimestamp(timestamp).isoformat()+'Z'
            doc.update(updated=updated)

        jobstart = store.get('job_start')
        if jobstart:
            doc.update(started=jobstart)

        if status >= WPSResponse.STATUS.DONE_STATUS:
            time_end = store['time_end']
            doc.update(finished=time_end)

        if status == WPSResponse.STATUS.ACCEPTED_STATUS:
            doc.update(status=JOBSTATUS.ACCEPTED.value)
        elif status == WPSResponse.STATUS.STARTED_STATUS:
            doc.update(status=JOBSTATUS.RUNNING.value)

        elif status == WPSResponse.STATUS.DONE_STATUS:
            doc.update(status=JOBSTATUS.SUCCESS.value)
            # Append link to results
            links.append({
                'href': f"{self.host_url}jobs/{ident}/results",
                'rel': "http://www.opengis.net/def/rel/ogc/1.0/results",
                'type': 'application/json',
                'title': "Job results"
            })

        elif status == WPSResponse.STATUS.ERROR_STATUS:
            doc.update(status=JOBSTATUS.FAILED.value)
        
        elif status == WPSResponse.STATUS.DISMISS_STATUS:
            doc.update(
                status=JOBSTATUS.DISMISSED.value,
                links=[{
                    'href': f"{self.host_url}jobs",
                    'rel': "up",
                    'type': "application/json",
                    'title': "Job list"
                }]
            )
    
        return doc

    def get_ogcapi_job_status(self, ident: str, service: Service) -> Json:
        """ Return job status  
        """
        store = service.get_status(ident)
        if store is None:
            return None

        return self._create_job_document(store)

    def get_ogcapi_job_list(self, service: Service) -> Json:
        """ Return job list
        """
        jobs = service.get_status()
       
        links = [{
            'href': f"{self.host_url}jobs",
            'rel': "self",
            'type': "application/json",
        }]

        doc = {
            'jobs': list(map(self._create_job_document, jobs)),
            'links': links,
        }

        return doc

    def get_ogcapi_job_dismiss(self, ident: str, service: Service) -> Json:
        """ Return job status  
        """
        store = service.get_status(ident)
        if store is None:
            # Non-existent job
            return None

        status = WPSResponse.STATUS[store['status']]
        if status < WPSResponse.STATUS.DONE_STATUS:
            pid = store.get('pid')
            if pid:
                # Job may still be busy
                service.kill_job(ident, pid)
            else:
                LOGGER.error("No pid for job with running status !")

        # Delete resources
        service.delete_results(ident, force=True)

        # Create response status
        links = [{
            'href': f"{self.host_url}jobs/",
            'rel': "up",
            'type': "application/json",
            'title': "Job list"
        }]

        # Return creation status
        doc = {
            'jobID': ident,
            'status': JOBSTATUS.DISMISSED.value,
            'processID': store['identifier'],
            'message': "Job dismissed",
            'progress': max(0, store.get('percent_done',-1)),
            'links': links,
        }

        return doc        


def get_inputs_from_document(doc, typeclasses):
    """  Parse inputs data
    """
    def _input(ident, data, typeclass):

        inpt = { 'identifier': ident }

        if typeclass == LiteralInput:
            if isinstance(data, dict):
                # Get qualified value
                inpt['data'] = data['value']
                inpt['uom'] = data.get('uom')
            else:
                # Get raw value
                inpt['data'] = data
        elif typeclass == ComplexInput:
            value = data.get('value')
            if value is not None:
                # Check format
                inpt['mimeType'] = data.get('mediaType')
                inpt['schema'] = data.get('schema')
                # Get raw value
                encoding = data.get('encoding')
                if encoding == 'base64':
                    value = base64.b64decode(value)
                else:
                    inpt['encoding'] = encoding
                inpt['data'] = value
            else:
                # Check reference data
                inpt['href'] = data['href']
                inpt['method'] = data.get('method', 'GET').upper()
                inpt['body'] = data.get('body')
                inpt['mimeType'] = data.get('type')
        elif typeclass == BoundingBoxInput:
            # Check bounding box
            inpt['data'] = data['bbox']
            inpt['crs'] = data.get('crs')

        return inpt

    def _inputs():
        for ident, inpts in doc.get('inputs', {}).items():
            typeclass = typeclasses.get(ident)
            if typeclass is None:
                continue
            try:
                if isinstance(inpts, list):
                    inpts = [_input(ident, data, typeclass) for data in inpts]
                else:
                    inpts = [_input(ident, inpts, typeclass)]
                yield ident, inpts
            except KeyError as err:
                raise InvalidParameterValue(
                    f"Missing property '{err}' for input '{ident}'"
                ) from None

    return dict(_inputs())


def get_outputs_from_document(doc, typeclasses): 
    """ Parse outputs specs

        Note that we ignore 'transmissionMode' since we 
        do not allow client to change it.
    """
    def _outputs():

        for ident, outp in doc.get('outputs', {}).items():

            typeclass = typeclasses.get(ident)
            if typeclass is None:
                continue
 
            output = { 'identifier' : ident }

            if typeclass == LiteralOutput:
                # UOM may be an output choice
                output_uom = outp.get('uom')
                if output_uom:
                    output['uom'] = output_uom
            elif typeclass == ComplexOutput:            
                # Formats may be an output choice
                output_format = outp.get('format')
                if output_format:
                    output['format'] = output_format
                return output
            elif typeclass == BoundingBoxOutput:
                pass

            yield  ident, output

    return dict(_outputs())
