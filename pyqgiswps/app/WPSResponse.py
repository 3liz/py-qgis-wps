#
# Copyright 2018 3liz
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

import os
import logging

from lxml import etree
import time
from pyqgiswps import WPS, OWS
from pyqgiswps.exceptions import NoApplicableCode
from pyqgiswps.executors.logstore import STATUS, logstore
from pyqgiswps import config


LOGGER = logging.getLogger('SRVLOG')


class WPSResponse():

    def __init__(self, process, wps_request, uuid, status_url=None):
        """constructor

        :param pyqgiswps.app.Process.Process process:
        :param pyqgiswps.app.WPSRequest.WPSRequest wps_request:
        :param uuid: string this request uuid
        :param status_url: url to retrieve the status from
        """

        self.process = process
        self.wps_request = wps_request
        self.outputs = {o.identifier: o for o in process.outputs}
        self.message = ''
        self.status = STATUS.NO_STATUS
        self.status_percentage = -1
        self.status_url = status_url
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
        if self.status >= STATUS.STORE_AND_UPDATE_STATUS:
            # rebuild the doc and update the status xml file
            self.document = self._construct_doc()
            # check if storing of the status is requested
            if self.store:
                self._write_response_doc(self.uuid, self.document)
            if self.status >= STATUS.DONE_STATUS:
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

    def _process_accepted(self):
        return WPS.Status(
            WPS.ProcessAccepted(self.message),
            creationTime=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        )

    def _process_started(self):
        return WPS.Status(
            WPS.ProcessStarted(
                self.message,
                percentCompleted=str(max(self.status_percentage,0))
            ),
            creationTime=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        )

    def _process_paused(self):
        return WPS.Status(
            WPS.ProcessPaused(
                self.message,
                percentCompleted=str(self.status_percentage)
            ),
            creationTime=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        )

    def _process_succeeded(self):
        return WPS.Status(
            WPS.ProcessSucceeded(self.message),
            creationTime=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        )

    def _process_failed(self):
        return WPS.Status(
            WPS.ProcessFailed(
                WPS.ExceptionReport(
                    OWS.Exception(
                        OWS.ExceptionText(self.message),
                        exceptionCode='NoApplicableCode',
                        locater='None'
                    )
                )
            ),
            creationTime=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        )

    def _construct_doc(self):
        doc = WPS.ExecuteResponse()
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsExecute_response.xsd'
        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        doc.attrib['serviceInstance'] = '%s%s' % (
            config.get_config('server').get('url').format(host_url=self.wps_request.host_url),
            '?service=WPS&request=GetCapabilities'
        )

        if self.status >= STATUS.STORE_STATUS:
            doc.attrib['statusLocation'] = self.status_url

        # Process XML
        process_doc = WPS.Process(
            OWS.Identifier(self.process.identifier),
            OWS.Title(self.process.title)
        )
        if self.process.abstract:
            process_doc.append(OWS.Abstract(self.process.abstract))
        # TODO: See Table 32 Metadata in OGC 06-121r3
        # for m in self.process.metadata:
        #    process_doc.append(OWS.Metadata(m))
        if self.process.profile:
            process_doc.append(OWS.Profile(self.process.profile))
        process_doc.attrib['{http://www.opengis.net/wps/1.0.0}processVersion'] = self.process.version

        doc.append(process_doc)

        # Status XML
        # return the correct response depending on the progress of the process
        if self.status == STATUS.STORE_AND_UPDATE_STATUS:
            if self.status_percentage == -1:
                status_doc = self._process_accepted()
                doc.append(status_doc)
                return doc
            elif self.status_percentage >= 0:
                status_doc = self._process_started()
                doc.append(status_doc)
                return doc

        # check if process failed and display fail message
        if self.status == STATUS.ERROR_STATUS:
            status_doc = self._process_failed()
            doc.append(status_doc)
            return doc

        # TODO: add paused status

        if self.status == STATUS.DONE_STATUS:
            status_doc = self._process_succeeded()
            doc.append(status_doc)

            # DataInputs and DataOutputs definition XML if lineage=true
            if self.wps_request.lineage == 'true':
                data_inputs = [self.wps_request.inputs[i][0].execute_xml() for i in self.wps_request.inputs]
                doc.append(WPS.DataInputs(*data_inputs))

                output_definitions = [self.outputs[o].execute_xml_lineage() for o in self.outputs]
                doc.append(WPS.OutputDefinitions(*output_definitions))

            # Process outputs XML
            output_elements = [self.outputs[o].execute_xml() for o in self.outputs]
            doc.append(WPS.ProcessOutputs(*output_elements))
        return doc

