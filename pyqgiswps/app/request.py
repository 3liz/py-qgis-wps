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

from pyqgiswps.executors.logstore import STATUS, logstore
from pyqgiswps.exceptions import NoApplicableCode
from pyqgiswps.config import confservice

LOGGER = logging.getLogger('SRVLOG')


class WPSRequest:

    def __init__(self):

        self.operation = None
        self.version = None
        self.language = None
        self.identifiers = None
        self.identifier = None
        self.store_execute = None
        self.status = None
        self.lineage = None
        self.inputs = None
        self.outputs = None
        self.raw = None
        self.map_uri = None
        self.host_url = None

        cfg = confservice['server']

        self.timeout    = cfg.getint('response_timeout')
        self.expiration = cfg.getint('response_expiration')


    @property
    def json(self):
        """Return JSON encoded representation of the request
        """

        obj = {
            'operation': self.operation,
            'version': self.version,
            'language': self.language,
            'identifiers': self.identifiers,
            'store_execute': self.store_execute,
            'status': self.store_execute,
            'lineage': self.lineage,
            'inputs': { i:[inpt.json for inpt in self.inputs[i]] for i in self.inputs },
            'outputs': self.outputs,
            'raw': self.raw
        }

        return obj

    def dumps( self ):
        return json.dumps(self.json, allow_nan=False)


class WPSResponse:

    STATUS = STATUS

    def __init__(self, process, wps_request, uuid, status_url=None):
        """constructor

        :param pyqgiswps.app.process.Process process:
        :param pyqgiswps.app.request.WPSRequest wps_request:
        :param uuid: string this request uuid
        :param status_url: url to retrieve the status from
        """

        store_url = confservice.get('server','store_url')
        store_url = store_url.format(host_url = wps_request.host_url, uuid = uuid,
                                     file = '{file}')

        self.process = process
        self.wps_request = wps_request
        self.outputs = {o.identifier: o for o in process.outputs}
        self.message = ''
        self.status = WPSResponse.STATUS.NO_STATUS
        self.status_percentage = -1
        self.status_url = status_url
        self.store_url  = store_url
        self.uuid = uuid
        self.document = None
        self.store = False

    def update_status(self, message=None, status_percentage=None, status=None):
        """
        Update status report of currently running process instance

        :param str message: Message you need to share with the client
        :param int status_percentage: Percent done (number betwen <0-100>)
        :param pyqgiswps.app.WPSResponse.STATUS status: process status - user should usually
            ommit this parameter
        """
        LOGGER.debug("*** Updating status: %s, %s, %s, %s", status, message, status_percentage, self.uuid)

        if message is not None:
            self.message = message

        if status is not None:
            self.status = status

        if status_percentage is not None:
            self.status_percentage = status_percentage

        # Write response
        if self.status >= WPSResponse.STATUS.STORE_AND_UPDATE_STATUS:
            # rebuild the doc and update the status xml file
            self.document = self.get_execute_response()
            # check if storing of the status is requested
            if self.store:
                self._write_response_doc(self.uuid, self.document)
            if self.status >= WPSResponse.STATUS.DONE_STATUS:
                self.process.clean()

        self._update_response(self.uuid)

    def _write_response_doc(self, request_uuid, doc):
        """ Write response document
        """
        try:
            logstore.write_response( request_uuid, doc)
        except IOError as e:
            raise NoApplicableCode('Writing Response Document failed with : %s' % e, code=500)

    def _update_response( self, request_uuid ):
        """ Log input request
        """
        logstore.update_response( request_uuid, self )





