##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
#                                                                #
# Copyright 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################


import logging
import tempfile
import traceback
from qywps import WPS, OWS
from urllib.request import urlopen
from qywps.app.WPSRequest import WPSRequest
from qywps.app.WPSResponse import WPSResponse
from qywps.app.WPSResponse import STATUS
import qywps.configuration as config
from qywps.exceptions import (MissingParameterValue, NoApplicableCode, InvalidParameterValue, 
                              FileSizeExceeded, StorageNotSupported, OperationNotSupported)
from qywps.inout.inputs import ComplexInput, LiteralInput, BoundingBoxInput
from qywps.executors import PoolExecutor, UnknownProcessError

from io import StringIO

from collections import deque
import os
import sys
import copy


LOGGER = logging.getLogger("QYWPS")


class Service():

    """ The top-level object that represents a WPS service. It's a WSGI
    application.

    :param processes: A list of :class:`~Process` objects that are
                      provided by this service.

    """

    def __init__(self, processes=[], executor=None):
        # Get and start executor
        self.executor = executor or PoolExecutor()
        self.executor.initialize( processes )

    def terminate(self):
        """ Clean ressource 
        """
        self.executor.terminate()

    @property
    def processes(self):
        return self.executor.list_processes()

    def get_process(self, ident):
        return self.executor.get_process(ident)

    def get_results(self, uuid):
        doc = self.executor.get_results(uuid)
        if doc is None:
            raise NoApplicableCode('No results found for %s' % uuid, code=404)

        return doc

    def get_status(self, uuid=None):
        """ Return the status of the stored processes
        """
        return self.executor.get_status(uuid)


    def get_capabilities(self, wps_request):
        process_elements = [p.capabilities_xml()
                            for p in self.processes]

        doc = WPS.Capabilities()

        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsGetCapabilities_response.xsd'
        # TODO: check Table 7 in OGC 05-007r7
        doc.attrib['updateSequence'] = '1'

        metadata = config.get_config('metadata:main')

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
            service_contact_doc.append(
                OWS.IndividualName(metadata.get('contact_name')))
            if metadata.get('contact_position'):
                service_contact_doc.append(
                    OWS.PositionName(metadata.get('contact_position')))

            contact_info_doc = OWS.ContactInfo()

            phone_doc = OWS.Phone()
            if metadata.get('contact_phone'):
                phone_doc.append(
                    OWS.Voice(metadata.get('contact_phone')))
           # Add Phone if not empty
            if len(phone_doc):
                contact_info_doc.append(phone_doc)

            address_doc = OWS.Address()
            if metadata.get('deliveryPoint'):
                address_doc.append(
                    OWS.DeliveryPoint(metadata.get('contact_address')))
            if metadata.get('city'):
                address_doc.append(
                    OWS.City(metadata.get('contact_city')))
            if metadata.get('contact_stateorprovince'):
                address_doc.append(
                    OWS.AdministrativeArea(metadata.get('contact_stateorprovince')))
            if metadata.get('contact_postalcode'):
                address_doc.append(
                    OWS.PostalCode(metadata.get('contact_postalcode')))
            if metadata.get('contact_country'):
                address_doc.append(
                    OWS.Country(metadata.get('contact_country')))
            if metadata.get('contact_email'):
                address_doc.append(
                    OWS.ElectronicMailAddress(
                        metadata.get('contact_email'))
                )
            # Add Address if not empty
            if len(address_doc):
                contact_info_doc.append(address_doc)

            if metadata.get('contact_url'):
                contact_info_doc.append(OWS.OnlineResource(
                    {'{http://www.w3.org/1999/xlink}href': metadata.get('contact_url')})
                )
            if metadata.get('contact_hours'):
                contact_info_doc.append(
                    OWS.HoursOfService(metadata.get('contact_hours')))
            if metadata.get('contact_instructions'):
                contact_info_doc.append(OWS.ContactInstructions(
                    metadata.get('contact_instructions')))

            # Add Contact information if not empty
            if len(contact_info_doc):
                service_contact_doc.append(contact_info_doc)

            if metadata.get('contact_role'):
                service_contact_doc.append(
                    OWS.Role(metadata.get('contact_role')))

        # Add Service Contact only if ProviderName and PositionName are set
        if len(service_contact_doc):
            service_prov_doc.append(service_contact_doc)

        doc.append(service_prov_doc)

        server_href = {'{http://www.w3.org/1999/xlink}href': config.get_config('server').get('url').format(host_url=wps_request.host_url)}

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

        languages = config.get_config('server').get('language').split(',')
        languages_doc = WPS.Languages(
            WPS.Default(
                OWS.Language(languages[0])
            )
        )
        lang_supported_doc = WPS.Supported()
        for l in languages:
            lang_supported_doc.append(OWS.Language(l))
        languages_doc.append(lang_supported_doc)

        doc.append(languages_doc)

        return doc

    def describe(self, identifiers):
        if not identifiers:
            raise MissingParameterValue('', 'identifier')

        identifier_elements = []
        # 'all' keyword means all processes
        if 'all' in (ident.lower() for ident in identifiers):
            for process in self.processes:
                try:
                    identifier_elements.append(process.describe_xml())
                except Exception as e:
                    traceback.print_exc()
                    raise NoApplicableCode(e, code=500)
        else:
            for identifier in identifiers:
                try:
                    process = self.get_process(identifier)
                except UnknownProcessError:
                    raise InvalidParameterValue(
                        "Unknown process %r" % identifier, "identifier")
                try:
                    identifier_elements.append(process.describe_xml())
                except Exception as e:
                    traceback.print_exc()
                    raise NoApplicableCode(e, code=500)

        doc = WPS.ProcessDescriptions(
            *identifier_elements
        )
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsDescribeProcess_response.xsd'
        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        return doc

    async def execute(self, identifier, wps_request, uuid):
        """Parse and perform Execute WPS request call
        
        :param identifier: process identifier string
        :param wps_request: qywps.WPSRequest structure with parsed inputs, still in memory
        :param uuid: string identifier of the request
        """
        try:
            process = self.get_process(identifier)
        except UnknownProcessError:
            raise InvalidParameterValue("Unknown process '%r'" % identifier, 'Identifier')

        # make deep copy of the process instance
        # so that processes are not overriding each other
        # just for execute
        process = copy.deepcopy(process)

        self._parse( process, wps_request )

        workdir = os.path.abspath(config.get_config('server').get('workdir'))
        workdir = os.path.join(workdir, str(uuid))
        process.set_workdir(workdir)
   
        # Get status url
        status_url = self.executor.status_url(uuid, wps_request)

        # Create response object
        wps_response = WPSResponse( process, wps_request, uuid, status_url=status_url)

        if wps_request.store_execute == 'true':
            wps_response.status = STATUS.STORE_AND_UPDATE_STATUS
            LOGGER.debug("Update status enabled")

        if wps_request.raw:
            raise NotImplementedError("Raw output is not implemented")
 
        wps_response = await self.executor.execute(wps_request, wps_response)

        # get the specified output as raw
        # FIXME Raw output
        #if wps_request.raw:
        #    for outpt in wps_request.outputs:
        #        for proc_outpt in process.outputs:
        #            if outpt == proc_outpt.identifier:
        #                resp = Response(proc_outpt.data)
        #                return resp
        #
        #    # if the specified identifier was not found raise error
        #    raise InvalidParameterValue('')

        return wps_response.document

    def _parse(self, process, wps_request):
        """Parse request
        """

        process.check(wps_request);

        LOGGER.debug('Checking if datainputs is required and has been passed')
        if process.inputs:
            if wps_request.inputs is None:
                raise MissingParameterValue('Missing "datainputs" parameter', 'datainputs')

        LOGGER.debug('Checking if all mandatory inputs have been passed')
        data_inputs = {}
        for inpt in process.inputs:
            if inpt.identifier not in wps_request.inputs:
                if inpt.min_occurs > 0:
                    LOGGER.error('Missing parameter value: %s', inpt.identifier)
                    raise MissingParameterValue(
                        inpt.identifier, inpt.identifier)
                else:
                    # inputs = deque(maxlen=inpt.max_occurs)
                    # inputs.append(inpt.clone())
                    # data_inputs[inpt.identifier] = inputs
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

    # FIXME Use async stream reader for computing size
    def _get_complex_input_handler(self, href):
        """Return function for parsing and storing complexdata
        :param href: href object yes or not
 
        """
        def href_handler(complexinput, datain):
            """<wps:Reference /> handler"""
            # save the reference input in workdir
            tmp_file = tempfile.mkstemp(dir=complexinput.workdir)[1]

            try:
                (reference_file, reference_file_data) = _openurl(datain)
                data_size = reference_file.headers.get('Content-Length', 0)
            except Exception as e:
                raise NoApplicableCode('File reference error: %s' % e)

            # if the response did not return a 'Content-Length' header then
            # calculate the size
            if data_size == 0:
                LOGGER.debug('no Content-Length, calculating size')
                data_size = _get_datasize(reference_file_data)

            # check if input file size was not exceeded
            complexinput.calculate_max_input_size()
            byte_size = complexinput.max_size * 1024 * 1024
            if int(data_size) > int(byte_size):
                raise FileSizeExceeded('File size for input exceeded.'
                                       ' Maximum allowed: %i megabytes' %
                                       complexinput.max_size, complexinput.get('identifier'))

            try:
                with open(tmp_file, 'w') as f:
                    f.write(reference_file_data)
            except Exception as e:
                raise NoApplicableCode(e)

            complexinput.file = tmp_file
            complexinput.url = datain.get('href')
            complexinput.as_reference = True

        def data_handler(complexinput, datain):
            """<wps:Data> ... </wps:Data> handler"""

            complexinput.data = datain.get('data')

        if href:
            return href_handler
        else:
            return data_handler

    def create_complex_inputs(self, source, inputs):
        """Create new ComplexInput as clone of original ComplexInput
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

            data_input.method = inpt.get('method', 'GET')

            # get the referenced input otherwise get the value of the field
            href = inpt.get('href', None)

            complex_data_handler = self._get_complex_input_handler(href)
            complex_data_handler(data_input, inpt)

            outinputs.append(data_input)
        if len(outinputs) < source.min_occurs:
            raise MissingParameterValue(description="Given data input is missing", locator=source.identifier)
        return outinputs

    def create_literal_inputs(self, source, inputs):
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

    def create_bbox_inputs(self, source, inputs):
        """ Takes the http_request and parses the input to objects
        :return collections.deque:
        """

        outinputs = deque(maxlen=source.max_occurs)

        for datainput in inputs:
            newinpt = source.clone()
            newinpt.data = [datainput.minx, datainput.miny,
                            datainput.maxx, datainput.maxy]
            outinputs.append(newinpt)

        if len(outinputs) < source.min_occurs:
            raise MissingParameterValue(
                description='Number of inputs is lower than minium required number of inputs',
                locator=source.identifier)

        return outinputs


def _openurl(inpt):
    """use urllib to open given href
    """
    data = None
    reference_file = None
    href = inpt.get('href')

    LOGGER.debug('Fetching URL %s', href)
    if inpt.get('method') == 'POST':
        if 'body' in inpt:
            data = inpt.get('body')
        elif 'bodyreference' in inpt:
            data = urlopen(url=inpt.get('bodyreference')).read()

        reference_file = urlopen(url=href, data=data)
    else:
        reference_file = urlopen(url=href)

    reference_file_data = reference_file.read().decode('utf-8')

    return (reference_file, reference_file_data)


def _get_datasize(reference_file_data):

    tmp_sio = None
    data_size = 0

    tmp_sio = StringIO()
    data_size = tmp_sio.write(reference_file_data)
    tmp_sio.close()

    return data_size
