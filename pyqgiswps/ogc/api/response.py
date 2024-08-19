#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import json
import logging

from datetime import datetime
from enum import Enum

from pyqgiswps.app.request import WPSResponse
from pyqgiswps.protos import JsonValue

LOGGER = logging.getLogger('SRVLOG')


class JOBSTATUS(str, Enum):
    ACCEPTED = 'accepted'
    RUNNING = 'running'
    SUCCESS = 'successful'
    FAILED = 'failed'
    DISMISSED = 'dismissed'


def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'


class OgcApiResponse(WPSResponse):

    JOBSTATUS = JOBSTATUS

    def encode_response(self, doc: JsonValue) -> bytes:
        """ Return response a bytes
        """
        return json.dumps(doc, ensure_ascii=False).encode()

    def get_status_links(self) -> JsonValue:
        host_url = self.wps_request.host_url
        return [{
            'href': f"{host_url}/jobs/{self.uuid}",
            'rel': 'http://www.opengis.net/def/rel/iana/1.0/status',
            'type': 'application/json',
            'title': 'job status',
        }]

    def get_execute_response(self) -> JsonValue:
        """ Construct the execute Json response

            The method return None until job completion
        """
        # Return synchronous results
        # Create response document
        if self.status == WPSResponse.STATUS.DONE_STATUS:
            # Process outputs
            doc = {o.identifier: o.ogcapi_output_result(self) for o in self.outputs.values()}
            return doc

        # Return creation status
        doc = {
            'jobID': str(self.uuid),
            'processID': self.process.identifier,
            'type': 'process',
            'created': utcnow_iso(),
            'progress': self.status_percentage,
        }

        if self.status == WPSResponse.STATUS.ACCEPTED_STATUS:
            doc.update(
                status=JOBSTATUS.ACCEPTED.value,
                message=self.message,
                progress=0,
                links=self.get_status_links(),
            )
        elif self.status == WPSResponse.STATUS.STARTED_STATUS:
            doc.update(
                status=JOBSTATUS.RUNNING.value,
                message=self.message,
                links=self.get_status_links(),
            )
        # Failure
        elif self.status == WPSResponse.STATUS.ERROR_STATUS:
            doc.update(
                status=JOBSTATUS.FAILED.value,
                message=self.message,
                links=self.get_status_links(),
            )
        # Dismiss
        elif self.status == WPSResponse.STATUS.DISMISS_STATUS:
            doc.update(
                status=JOBSTATUS.DISMISSED.value,
                message=self.message,
                links=self.get_status_links(),
            )

        return doc
