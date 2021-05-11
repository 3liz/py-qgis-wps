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

import logging
import traceback
from pyqgiswps import WPS, OWS
from pyqgiswps.app.WPSResponse import WPSResponse
from pyqgiswps.app.WPSRequest import WPSRequest
from pyqgiswps.app.Process import WPSProcess
from pyqgiswps.config import confservice
from pyqgiswps.exceptions import (MissingParameterValue, NoApplicableCode, InvalidParameterValue)
from pyqgiswps.inout.literaltypes import JsonValue
from pyqgiswps.inout.inputs import ComplexInput, LiteralInput, BoundingBoxInput
from pyqgiswps.executors.logstore import STATUS
from pyqgiswps.executors.processingexecutor import ProcessingExecutor, UnknownProcessError
from pyqgiswps.accesspolicy import AccessPolicy
from pyqgiswps.owsutils.ows import BoundingBox

from collections import deque
import os
import copy

from typing import Iterable, TypeVar, Optional, Union

# Define generic WPS Input
WPSInput = Union[ComplexInput, LiteralInput, BoundingBoxInput]

XMLDocument = TypeVar('XMLDocument')
XMLElement  = TypeVar('XMLElement')

LOGGER = logging.getLogger('SRVLOG')


class Service():

    """ The top-level object that represents a WPS service.

    :param processes: A list of :class:`~Process` objects that are
                      provided by this service.

    """

    def __init__(self, processes: Iterable[WPSProcess]=[] ) -> None:
        # Get and start executor
        self.executor = ProcessingExecutor(processes)

    def terminate(self) -> None:
        self.executor.terminate()

    @property
    def processes(self) -> Iterable[WPSProcess]:
        return self.executor.list_processes()

    def get_process(self, ident: str, map_uri: Optional[str]=None) -> WPSProcess:
        return self.get_processes((ident,), map_uri=map_uri)[0]

    def get_processes(self, idents: Iterable[str], map_uri: Optional[str]=None) -> Iterable[WPSProcess]:
        return self.executor.get_processes(idents, map_uri=map_uri)

    def get_results(self, uuid: str) -> XMLDocument:
        doc = self.executor.get_results(uuid)
        if doc is None:
            raise NoApplicableCode('No results found for %s' % uuid, code=404)

        return doc

    def get_status(self, uuid: Optional[str]=None, **kwargs) -> JsonValue:
        """ Return the status of the stored processes
        """
        return self.executor.get_status(uuid, **kwargs)

    def delete_results(self, uuid: str ) -> bool:
        """ Delete process results and status 
        """
        return self.executor.delete_results(uuid)

    def get_capabilities(self, wps_request: WPSRequest, accesspolicy: AccessPolicy=None) -> XMLDocument:
        """ Handle getcapbabilities request
        """
        process_elements = [p.capabilities_xml()
                            for p in self.processes if accesspolicy.allow(p.identifier)]

        doc = WPS.Capabilities()

        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsGetCapabilities_response.xsd'
        # TODO: check Table 7 in OGC 05-007r7
        doc.attrib['updateSequence'] = '1'

        metadata = confservice['metadata:main']

        # Service Identification
        service_ident_doc = OWS.ServiceIdentification(
            OWS.Title(metadata.get('identification_title'))
        )

        if metadata.get('identification_abstract'):
            service_ident_doc.append(
                OWS.Abstract(metadata.get('identification_abstract')))

        if metadata.get('identification_keywords'):
            keywords_doc = OWS.Keywords()
            for k in metadata.get('identification_keywords').split(','):
                if k:
                    keywords_doc.append(OWS.Keyword(k))
            service_ident_doc.append(keywords_doc)

        if metadata.get('identification_keywords_type'):
            keywords_type = OWS.Type(metadata.get('identification_keywords_type'))
            keywords_type.attrib['codeSpace'] = 'ISOTC211/19115'
            keywords_doc.append(keywords_type)

        service_ident_doc.append(OWS.ServiceType('WPS'))

        # TODO: set proper version support
        service_ident_doc.append(OWS.ServiceTypeVersion('1.0.0'))

        service_ident_doc.append(
            OWS.Fees(metadata.get('identification_fees')))

        for con in metadata.get('identification_accessconstraints').split(','):
            service_ident_doc.append(OWS.AccessConstraints(con))

        if metadata.get('identification_profile'):
            service_ident_doc.append(
                OWS.Profile(metadata.get('identification_profile')))

        doc.append(service_ident_doc)

        # Service Provider
        service_prov_doc = OWS.ServiceProvider(
            OWS.ProviderName(metadata.get('provider_name')))

        if metadata.get('provider_url'):
            service_prov_doc.append(OWS.ProviderSite(
                {'{http://www.w3.org/1999/xlink}href': metadata.get('provider_url')})
            )

        # Service Contact
        service_contact_doc = OWS.ServiceContact()

        # Add Contact information only if a name is set
        if metadata.get('contact_name'):
            service_contact_doc.append(OWS.IndividualName(metadata.get('contact_name')))
            if metadata.get('contact_position'):
                service_contact_doc.append(OWS.PositionName(metadata.get('contact_position')))

            contact_info_doc = OWS.ContactInfo()

            phone_doc = OWS.Phone()
            if metadata.get('contact_phone'):
                phone_doc.append(OWS.Voice(metadata.get('contact_phone')))
            # Add Phone if not empty
            if len(phone_doc):
                contact_info_doc.append(phone_doc)

            address_doc = OWS.Address()
            if metadata.get('deliveryPoint'):
                address_doc.append(OWS.DeliveryPoint(metadata.get('contact_address')))
            if metadata.get('city'):
                address_doc.append(OWS.City(metadata.get('contact_city')))
            if metadata.get('contact_stateorprovince'):
                address_doc.append(OWS.AdministrativeArea(metadata.get('contact_stateorprovince')))
            if metadata.get('contact_postalcode'):
                address_doc.append(OWS.PostalCode(metadata.get('contact_postalcode')))
            if metadata.get('contact_country'):
                address_doc.append(OWS.Country(metadata.get('contact_country')))
            if metadata.get('contact_email'):
                address_doc.append(OWS.ElectronicMailAddress(metadata.get('contact_email')))
            # Add Address if not empty
            if len(address_doc):
                contact_info_doc.append(address_doc)

            if metadata.get('contact_url'):
                contact_info_doc.append(OWS.OnlineResource({'{http://www.w3.org/1999/xlink}href': metadata.get('contact_url')}))
            if metadata.get('contact_hours'):
                contact_info_doc.append(OWS.HoursOfService(metadata.get('contact_hours')))
            if metadata.get('contact_instructions'):
                contact_info_doc.append(OWS.ContactInstructions(metadata.get('contact_instructions')))

            # Add Contact information if not empty
            if len(contact_info_doc):
                service_contact_doc.append(contact_info_doc)

            if metadata.get('contact_role'):
                service_contact_doc.append(OWS.Role(metadata.get('contact_role')))

        # Add Service Contact only if ProviderName and PositionName are set
        if len(service_contact_doc):
            service_prov_doc.append(service_contact_doc)

        doc.append(service_prov_doc)

        server_href = {'{http://www.w3.org/1999/xlink}href': confservice.get('server','url').format(host_url=wps_request.host_url)}

        # Operations Metadata
        operations_metadata_doc = OWS.OperationsMetadata(
            OWS.Operation(
                OWS.DCP(
                    OWS.HTTP(
                        OWS.Get(server_href),
                        OWS.Post(server_href)
                    )
                ),
                name="GetCapabilities"
            ),
            OWS.Operation(
                OWS.DCP(
                    OWS.HTTP(
                        OWS.Get(server_href),
                        OWS.Post(server_href)
                    )
                ),
                name="DescribeProcess"
            ),
            OWS.Operation(
                OWS.DCP(
                    OWS.HTTP(
                        OWS.Get(server_href),
                        OWS.Post(server_href)
                    )
                ),
                name="Execute"
            )
        )
        doc.append(operations_metadata_doc)

        doc.append(WPS.ProcessOfferings(*process_elements))

        languages = confservice.get('server','language').split(',')
        languages_doc = WPS.Languages(
            WPS.Default(
                OWS.Language(languages[0])
            )
        )
        lang_supported_doc = WPS.Supported()
        for lang in languages:
            lang_supported_doc.append(OWS.Language(lang))
        languages_doc.append(lang_supported_doc)

        doc.append(languages_doc)

        return doc

    def describe(self, identifiers: Iterable[str], map_uri: Optional[str]=None) -> XMLDocument:
        """ Return process description
        """
        if not identifiers:
            raise MissingParameterValue('', 'identifier')

        # 'all' keyword means all processes
        if 'all' in (ident.lower() for ident in identifiers):
            identifiers = [p.identifier for p in self.processes]

        identifier_elements = []
        try:
            identifier_elements.extend(p.describe_xml() for p in self.get_processes(identifiers,map_uri=map_uri))
        except UnknownProcessError as exc:
            raise InvalidParameterValue("Unknown process %s" % exc, "identifier")
        except Exception as e:
            LOGGER.critical("Exception:\n%s",traceback.format_exc())
            raise NoApplicableCode(str(e), code=500)

        doc = WPS.ProcessDescriptions(*identifier_elements)
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsDescribeProcess_response.xsd'
        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        return doc

    def _status_url(self, uuid: str, request: WPSRequest):
        """ Return the status_url for the process <uuid>
        """
        cfg = confservice['server']
        status_url = cfg['status_url']
        proxy_host = cfg['host_proxy'] 
        if not proxy_host:
            # Need to return the 'real' host
            proxy_host = request.host_url if request else '{host_url}'

        return status_url.format(host_url=proxy_host,uuid=uuid)

    async def execute(self, identifier: str, wps_request: WPSRequest, uuid: str, 
                      map_uri: Optional[str]=None) -> XMLDocument:
        """Parse and perform Execute WPS request call
        
        :param identifier: process identifier string
        :param wps_request: pyqgiswps.WPSRequest structure with parsed inputs, still in memory
        :param uuid: string identifier of the request
        """
        try:
            process = self.get_process(identifier, map_uri=map_uri)
        except UnknownProcessError:
            raise InvalidParameterValue("Unknown process '%r'" % identifier, 'Identifier')

        # make deep copy of the process instance
        # so that processes are not overriding each other
        # just for execute
        process = copy.deepcopy(process)

        self._parse( process, wps_request )

        workdir = os.path.abspath(confservice.get('server','workdir'))
        workdir = os.path.join(workdir, str(uuid))

        # Create working directory if it does not exists
        os.makedirs(workdir, exist_ok=True)
        
        process.set_workdir(workdir)
   
        # Get status url
        status_url = self._status_url(uuid, wps_request)

        # Create response object
        wps_response = WPSResponse( process, wps_request, uuid, status_url=status_url)

        if wps_request.store_execute == 'true':
            # Setting STORE_AND_UPDATE_STATUS will trigger
            # asynchronous requests
            wps_response.status = STATUS.STORE_AND_UPDATE_STATUS
            LOGGER.debug("Update status enabled")

        if wps_request.raw:
            raise NotImplementedError("Raw output is not implemented")
 
        document = await self.executor.execute(wps_request, wps_response)

        return document

    def _parse(self, process: WPSProcess, wps_request: WPSRequest):
        """Parse request
        """
        LOGGER.debug('Checking if datainputs is required and has been passed')
        if process.inputs:
            if wps_request.inputs is None:
                raise MissingParameterValue('Missing "datainputs" parameter', 'datainputs')

        LOGGER.debug('Checking if all mandatory inputs have been passed')
        data_inputs = {}
        for inpt in process.inputs:
            LOGGER.debug('Checking input: %s', inpt.identifier)
            if inpt.identifier not in wps_request.inputs:
                if inpt.min_occurs > 0:
                    LOGGER.error('Missing parameter value: %s', inpt.identifier)
                    raise MissingParameterValue(
                        inpt.identifier, inpt.identifier)
                else:
                    # Do not add the input 
                    pass
            else:
                # Replace the dicts with the dict of Literal/Complex inputs
                # set the input to the type defined in the process.
                if isinstance(inpt, ComplexInput):
                    data_inputs[inpt.identifier] = self.create_complex_inputs(
                        inpt, wps_request.inputs[inpt.identifier])
                elif isinstance(inpt, LiteralInput):
                    data_inputs[inpt.identifier] = self.create_literal_inputs(
                        inpt, wps_request.inputs[inpt.identifier])
                elif isinstance(inpt, BoundingBoxInput):
                    data_inputs[inpt.identifier] = self.create_bbox_inputs(
                        inpt, wps_request.inputs[inpt.identifier])

        wps_request.inputs = data_inputs

        # set as_reference to True for all the outputs specified as reference
        # if the output is not required to be raw
        if not wps_request.raw:
            for wps_outpt in wps_request.outputs:

                is_reference = wps_request.outputs[
                    wps_outpt].get('asReference', 'false').lower() == 'true'

                for outpt in process.outputs:
                    if outpt.identifier == wps_outpt:
                        outpt.as_reference = is_reference


    def create_complex_inputs(self, source: ComplexInput, 
                              inputs: Iterable[JsonValue]) -> Iterable[ComplexInput]:
        """ Create new ComplexInput as clone of original ComplexInput

            because of inputs can be more then one, take it just as Prototype
            :return collections.deque:
        """
        outinputs = deque(maxlen=source.max_occurs)

        for inpt in inputs:
            data_input = source.clone()
            frmt = data_input.supported_formats[0]
            if 'mimeType' in inpt:
                if inpt['mimeType']:
                    frmt = data_input.get_format(inpt['mimeType'])
                else:
                    frmt = data_input.data_format

            if frmt:
                data_input.data_format = frmt
            else:
                raise InvalidParameterValue(
                    'Invalid mimeType value %s for input %s' %
                    (inpt.get('mimeType'), source.identifier),
                    'mimeType')

            # get the referenced input otherwise get the value of the field
            href = inpt.get('href', None)
            if href:
                data_input.method = inpt.get('method', 'GET')
                data_input.url = href
                data_input.as_reference = True
                data_input.body = inpt.get('body',None)
            else:
                data_input.data = inpt.get('data')

            outinputs.append(data_input)
        if len(outinputs) < source.min_occurs:
            raise MissingParameterValue(description="Given data input is missing", locator=source.identifier)
        return outinputs

    def create_literal_inputs(self, source: LiteralInput, 
                              inputs: Iterable[JsonValue]) -> Iterable[LiteralInput]:
        """ Takes the http_request and parses the input to objects
        :return collections.deque:
        """

        outinputs = deque(maxlen=source.max_occurs)

        for inpt in inputs:
            newinpt = source.clone()
            # set the input to the type defined in the process
            newinpt.uom = inpt.get('uom')
            data_type = inpt.get('datatype')
            if data_type:
                newinpt.data_type = data_type

            # get the value of the field
            newinpt.data = inpt.get('data')

            outinputs.append(newinpt)

        if len(outinputs) < source.min_occurs:
            raise MissingParameterValue(description="Missing literal input data value for %s" % source.identifier, locator=source.identifier)

        return outinputs

    def create_bbox_inputs(self, source: BoundingBoxInput, 
                           inputs: Iterable[JsonValue]) -> Iterable[BoundingBoxInput]:
        """ Takes the http_request and parses the input to objects
        :return collections.deque:
        """

        outinputs = deque(maxlen=source.max_occurs)

        for datainput in inputs:

            if not isinstance(datainput, BoundingBox):
                raise InvalidParameterValue("Invalid value for parameter '{source.identifier}'")

            newinpt = source.clone()
            newinpt.data = [datainput.minx, datainput.miny,
                            datainput.maxx, datainput.maxy]
            outinputs.append(newinpt)

        if len(outinputs) < source.min_occurs:
            raise MissingParameterValue(
                description='Number of inputs is lower than minium required number of inputs',
                locator=source.identifier)

        return outinputs


