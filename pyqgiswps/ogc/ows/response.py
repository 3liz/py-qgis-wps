#
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
from datetime import datetime

from lxml import etree

from pyqgiswps.app.request import WPSResponse
from pyqgiswps.config import confservice

from .schema import WPS, OWS, XMLDocument

from typing import TypeVar

UUID = TypeVar('UUID')

LOGGER = logging.getLogger('SRVLOG')


def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()+'Z'


class OWSResponse(WPSResponse):

    def get_process_accepted(self) -> XMLDocument:
        return WPS.Status(
            WPS.ProcessAccepted(self.message),
            creationTime=utcnow_iso()
        )

    def get_process_started(self) -> XMLDocument:
        return WPS.Status(
            WPS.ProcessStarted(
                self.message,
                percentCompleted=str(max(self.status_percentage,0))
            ),
            creationTime=utcnow_iso()
        )

    def get_process_paused(self) -> XMLDocument:
        return WPS.Status(
            WPS.ProcessPaused(
                self.message,
                percentCompleted=str(self.status_percentage)
            ),
            creationTime=utcnow_iso()
        )

    def get_process_succeeded(self) -> XMLDocument:
        return WPS.Status(
            WPS.ProcessSucceeded(self.message),
            creationTime=utcnow_iso()
        )

    def get_process_failed(self) -> XMLDocument:
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
            creationTime=utcnow_iso()
        )

    def encode_response(self, doc: XMLDocument) -> bytes:
        """ Return response a bytes 
        """
        return etree.tostring(doc, pretty_print=True, encoding='utf-8')

    def get_execute_response(self) -> XMLDocument:
        """ Construct the execute XML response
        """
        doc = WPS.ExecuteResponse()
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsExecute_response.xsd'
        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        doc.attrib['serviceInstance'] = '%s%s' % (
            confservice.get('server','url').format(host_url=self.wps_request.host_url),
            '?service=WPS&request=GetCapabilities'
        )

        doc.attrib['statusLocation'] = self.wps_request.status_url

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
        if self.status == WPSResponse.STATUS.ACCEPTED_STATUS:
            status_doc = self.get_process_accepted()
            doc.append(status_doc)
            return doc

        if self.status == WPSResponse.STATUS.STARTED_STATUS:
            status_doc = self.get_process_started()
            doc.append(status_doc)
            return doc

        # check if process failed and display fail message
        if self.status == WPSResponse.STATUS.ERROR_STATUS:
            status_doc = self.get_process_failed()
            doc.append(status_doc)
            return doc

        if self.status == WPSResponse.STATUS.DONE_STATUS:
            status_doc = self.get_process_succeeded()
            doc.append(status_doc)

            # DataInputs and DataOutputs definition XML if lineage is true
            if self.wps_request.lineage:
                data_inputs = [self.wps_request.inputs[i][0].execute_xml() for i in self.wps_request.inputs]
                doc.append(WPS.DataInputs(*data_inputs))

                output_definitions = [self.outputs[o].execute_xml_lineage() for o in self.outputs]
                doc.append(WPS.OutputDefinitions(*output_definitions))

            # Process outputs XML
            output_elements = [self.outputs[o].execute_xml(self) for o in self.outputs]
            doc.append(WPS.ProcessOutputs(*output_elements))
        return doc
