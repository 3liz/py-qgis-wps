# Copyright 2021 3liz
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
import json

from urllib.parse import (
    urlparse,
    urlunparse,
    urljoin,
)

from pyqgiswps.executors.logstore import STATUS, logstore
from pyqgiswps.exceptions import NoApplicableCode
from pyqgiswps.config import confservice

from typing import TypeVar, Optional

LOGGER = logging.getLogger('SRVLOG')


Service = TypeVar('Service')
UUID    = TypeVar('UUID')


class WPSRequest:

    def __init__(self):

        self.operation = None
        self.version = None
        self.language = None
        self.identifiers = None
        self.identifier = None
        self.execute_async = False
        self.inputs = None
        self.outputs = None
        self.map_uri = None
        self.host_url = None

        self.realm = None

        # The url path + query used
        # for retrieving the job status
        self.status_link = None

        cfg = confservice['server']

        self.timeout    = cfg.getint('response_timeout')
        self.expiration = cfg.getint('response_expiration')
    
    @property
    def status_url(self) -> Optional[str]:
        if self.status_link:
            return f"{self.host_url.rstrip('/')}{self.status_link}"
        else:
            return None

    @staticmethod
    def must_check_realm(realm: str) -> bool:
        """ Return True if realm must be validated
            against ressource realm
        """
        cfg = confservice['server']
        if cfg.getboolean('enable_job_realm'):
            admin_realm =  cfg['admin_realm']
            if not admin_realm:
                LOGGER.warning("Admin realm token not set !")
                return True
            else:
                # Ok, realm is admin realm
                return realm != admin_realm
        else:
            return realm is not None
 
    def realm_enabled(self) -> bool:
        return self.must_check_realm(self.realm)
            
    @property
    def json(self):
        """Return JSON encoded representation of the request
        """

        obj = {
            'operation': self.operation,
            'version': self.version,
            'language': self.language,
            'identifiers': self.identifiers,
            'identifier' : self.identifier,
            'execute_async': self.execute_async,
            'inputs': { i:[inpt.json for inpt in self.inputs[i]] for i in self.inputs },
            'outputs': self.outputs,
            'timeout': self.timeout,
        }

        return obj

    def __repr__(self) -> str:
        return f"AllowedValue(values={self.values}, minval={self.minval}, maxval={self.maxval}, range_closure={self.range_closure})"

    def dumps( self ):
        return json.dumps(self.json, allow_nan=False)

    #
    # Execute
    #
    async def execute(self, service: Service, uuid: UUID, 
                      map_uri: Optional[str]=None) -> bytes:
        
        return await service.execute(self.identifier, self, uuid, map_uri)


class WPSResponse:

    STATUS = STATUS

    def __init__(self, process, wps_request, uuid):
        """constructor

        :param pyqgiswps.app.process.Process process:
        :param pyqgiswps.app.request.WPSRequest wps_request:
        :param uuid: string this request uuid
        """
        
        store_url = f"{wps_request.host_url}jobs/{uuid}/files/"

        self.process = process
        self.wps_request = wps_request
        self.outputs = {o.identifier: o for o in process.outputs}
        self.message = ''
        self.status = WPSResponse.STATUS.NO_STATUS
        self.status_percentage = 0
        self.store_url  = store_url
        self.uuid = uuid
        self.document = None
        self.output_files = []

    def resolve_store_url(self, url: str, as_output: bool=False) -> str:
        """ Resolve 'store:' uri
        """
        if not url.startswith('store:'):
            return url
        path = url[6:]
        # Save as legitimate output
        if as_output and path not in self.output_files:
            self.output_files.append(path)

        url = urlparse(self.store_url)
        url = url._replace(path=urljoin(url.path, path))
        return urlunparse(url)

    def get_document_bytes(self) -> Optional[bytes]:
        """ Return bytes encoded document
            Raises exception if no document is availabe 
        """
        if self.document is None:
            raise NoApplicableCode('No document available', code=500)
        return self.encode_response(self.document)
    
    def update_status(self, message=None, status_percentage=None, status=None):
        """
        Update status report of currently running process instance

        :param str message: Message you need to share with the client
        :param int status_percentage: Percent done (number betwen <0-100>)
        :param pyqgiswps.app.WPSResponse.STATUS status: process status - user should usually
            ommit this parameter
        """
        if message is not None:
            self.message = message

        if status is not None:
            self.status = status

        if status_percentage is not None:
            self.status_percentage = status_percentage

        # Write response
        # rebuild the doc and update the status xml file
        self.document = self.get_execute_response()
        # check if storing of the status is requested
        if self.document:
            self._write_response_doc(self.uuid, self.document)
        if self.status >= WPSResponse.STATUS.DONE_STATUS:
            self.process.clean()

        self._update_response(self.uuid)

    def _write_response_doc(self, request_uuid, doc):
        """ Write response document
        """
        try:
            logstore.write_response(request_uuid, self.encode_response(doc))
        except IOError as e:
            raise NoApplicableCode('Writing Response Document failed with : %s' % e, code=500)

    def _update_response(self, request_uuid):
        """ Log input request
        """
        logstore.update_response(request_uuid, self)





