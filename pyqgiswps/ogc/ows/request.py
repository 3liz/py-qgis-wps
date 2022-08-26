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
import lxml
import lxml.etree
import base64
import traceback

from pyqgiswps.config import confservice
from pyqgiswps.app.request import WPSRequest
from pyqgiswps.exceptions import (NoApplicableCode,
                                  OperationNotSupported,
                                  MissingParameterValue,
                                  VersionNegotiationFailed,
                                  InvalidParameterValue,
                                  UnknownProcessError)

from .schema import OWS, WPS, BoundingBox, xpath_ns, XMLDocument
from .response import OWSResponse

from typing import TypeVar, Optional, Iterable

AccessPolicy = TypeVar('AccessPolicy')
Service      = TypeVar('Service')
WPSProcess   = TypeVar('WPSProcess')

LOGGER = logging.getLogger('SRVLOG')

DEFAULT_VERSION = '1.0.0'
SCHEMA_VERSIONS = ('1.0.0',)


def _check_version(version):
    """ check given version
    """
    return  version in SCHEMA_VERSIONS


class OWSRequest(WPSRequest):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lineage = False

    @staticmethod
    def parse_get_request(handler) -> WPSRequest:
        """ HTTP GET request parser

            :return: A WPSRequest instance
        """
        service = handler.get_argument('SERVICE')
        if service.lower() != 'wps':
            raise InvalidParameterValue('parameter SERVICE [%s] not supported' % service, 'SERVICE')

        operation = handler.get_argument('REQUEST').lower()

        wpsrequest = OWSRequest()

        _get_query_param = handler.get_argument

        def parse_get_getresults():
            """ Parse GET GetResults
            """
            wpsrequest.results_uuid = _get_query_param('UUID')

        def parse_get_getcapabilities():
            """Parse GET GetCapabilities request
            """
            acceptedversions =  _get_query_param('ACCEPTVERSIONS', None)
            wpsrequest.check_accepted_versions(acceptedversions)

        def parse_get_describeprocess():
            """Parse GET DescribeProcess request
            """
            version = _get_query_param('VERSION', None)
            wpsrequest.check_and_set_version(version)

            language = _get_query_param('LANGUAGE', None)
            wpsrequest.check_and_set_language(language)

            wpsrequest.identifiers = _get_query_param('IDENTIFIER').split(',')

        def parse_get_execute():
            """Parse GET Execute request
            """
            version = _get_query_param('VERSION', None)
            wpsrequest.check_and_set_version(version)

            language = _get_query_param('LANGUAGE', None)
            wpsrequest.check_and_set_language(language)

            wpsrequest.identifier = _get_query_param('IDENTIFIER')
            
            timeout = _get_query_param('TIMEOUT', None)
            wpsrequest.check_and_set_timeout(timeout)

            expire = _get_query_param('EXPIRE', None)
            wpsrequest.check_and_set_expiration(expire)

            # Trigger async response
            wpsrequest.execute_async = _get_query_param('STOREEXECUTERESPONSE', 'false').lower() == 'true'
            wpsrequest.lineage = _get_query_param('LINEAGE', 'false').lower() == 'true'

            wpsrequest.inputs = get_data_from_kvp(_get_query_param('DATAINPUTS', None), 'DataInputs')

            # take responseDocument preferably
            wpsrequest.outputs = get_data_from_kvp(_get_query_param('RESPONSEDOCUMENT', None))

        wpsrequest.operation = operation

        if operation == 'getresults':
            parse_get_getresults()
        elif operation == 'getcapabilities':
            parse_get_getcapabilities()
        elif operation == 'describeprocess':
            parse_get_describeprocess()
        elif operation == 'execute':
            parse_get_execute()
        else:
            raise OperationNotSupported('Unknown request %r' % operation, operation)

        # Return the created WPSRequest object
        return wpsrequest

    @staticmethod
    def parse_post_request(handler) -> WPSRequest:
        """Factory function returing propper parsing function
        """
        try:
            doc = lxml.etree.fromstring(handler.request.body)
        except Exception as e:
            raise NoApplicableCode("%s" % e)

        wpsrequest = OWSRequest()

        tagname = doc.tag

        def parse_post_getcapabilities():
            """Parse POST GetCapabilities request
            """
            acceptedversions = xpath_ns(
                doc, '/wps:GetCapabilities/ows:AcceptVersions/ows:Version')
            acceptedversions = ','.join(
                map(lambda v: v.text, acceptedversions))
            wpsrequest.check_accepted_versions(acceptedversions)

        def parse_post_describeprocess():
            """Parse POST DescribeProcess request
            """

            version = doc.attrib.get('version')
            wpsrequest.check_and_set_version(version)

            language = doc.attrib.get('language')
            wpsrequest.check_and_set_language(language)

            wpsrequest.operation = 'describeprocess'
            wpsrequest.identifiers = [identifier_el.text for identifier_el in
                                      xpath_ns(doc, './ows:Identifier')]

        def parse_post_execute():
            """Parse POST Execute request
            """

            version = doc.attrib.get('version')
            wpsrequest.check_and_set_version(version)

            language = doc.attrib.get('language')
            wpsrequest.check_and_set_language(language)

            wpsrequest.operation = 'execute'

            identifier = xpath_ns(doc, './ows:Identifier')

            if not identifier:
                raise MissingParameterValue(
                    'Process identifier not set', 'Identifier')

            wpsrequest.identifier = identifier[0].text
            wpsrequest.lineage = False
            wpsrequest.execute_async = False
            wpsrequest.inputs = get_inputs_from_xml(doc)
            wpsrequest.outputs = get_output_from_xml(doc)

            # check if response document tag has been set then retrieve
            response_document = xpath_ns(
                doc, './wps:ResponseForm/wps:ResponseDocument')
            if len(response_document) > 0:
                wpsrequest.lineage = response_document[
                    0].attrib.get('lineage', 'false').lower() == 'true'
                wpsrequest.execute_async = response_document[
                    0].attrib.get('storeExecuteResponse', 'false').lower() == 'true'
                # Set timeout
                timeout = response_document[0].attrib.get('timeout')
                wpsrequest.check_and_set_timeout(timeout)
                # Set expiration
                expire = response_document[0].attrib.get('expire')
                wpsrequest.check_and_set_expiration(expire)

        if tagname == WPS.GetCapabilities().tag:
            wpsrequest.operation = 'getcapabilities'
            parse_post_getcapabilities()
        elif tagname == WPS.DescribeProcess().tag:
            wpsrequest.operation = 'describeprocess'
            parse_post_describeprocess()
        elif tagname == WPS.Execute().tag:
            wpsrequest.operation = 'execute'
            parse_post_execute()
        else:
            raise InvalidParameterValue('Unknown request %r' % tagname, 'request')

        # Return the created WPSRequest object
        return wpsrequest

    def check_accepted_versions(self, acceptedversions):
        """
        :param acceptedversions: string
        """

        version = None

        if acceptedversions:
            acceptedversions_array = acceptedversions.split(',')
            for aversion in acceptedversions_array:
                if _check_version(aversion):
                    version = aversion
        else:
            version = '1.0.0'

        if version:
            self.check_and_set_version(version)
        else:
            raise VersionNegotiationFailed(
                'The requested version "%s" is not supported by this server' % acceptedversions, 'version')

    def check_and_set_version(self, version):
        """set this.version
        """

        if not version:
            raise MissingParameterValue('Missing version', 'version')
        elif not _check_version(version):
            raise VersionNegotiationFailed(
                'The requested version "%s" is not supported by this server' % version, 'version')
        else:
            self.version = version

    def check_and_set_language(self, language):
        """set this.language
        """

        if not language:
            language = 'None'
        elif language != 'en-US':
            raise InvalidParameterValue(
                'The requested language "%s" is not supported by this server' % language, 'language')
        else:
            self.language = language

    def check_and_set_timeout(self, timeout):
        try:
            if timeout is not None:
                _timeout = int(timeout)
                if _timeout <= 0:
                    raise ValueError()
                self.timeout = min(self.timeout, _timeout)
        except ValueError:
            raise InvalidParameterValue('TIMEOUT param must be an integer > 0 value, not "%s"', timeout)

    def check_and_set_expiration(self, expire):
        try:
            if expire is not None:
                _expire = int(expire)
                if _expire <= 0:
                    raise ValueError()
                self.expiration = _expire
        except ValueError:
            raise InvalidParameterValue('EXPIRE param must be an integer > 0 value, not "%s"', expire)

    #
    # GetCapabilities
    #
    def get_capabilities(self, service: Service, accesspolicy: AccessPolicy) -> XMLDocument:
        """ Handle getcapbabilities request
        """
        process_elements = [p.capabilities_xml()
                            for p in service.processes if accesspolicy.allow(p.identifier)]

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

        server_href = {'{http://www.w3.org/1999/xlink}href': confservice.get('server','url').format(host_url=self.host_url)}

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

    def get_processes_for_request(self, service: Service,  idents: Iterable[str], 
                                  map_uri: Optional[str]=None) -> Iterable[WPSProcess]:
        try:
            return service.get_processes(idents, map_uri)
        except UnknownProcessError as exc:
            raise InvalidParameterValue("Unknown process %s" % exc, "identifier") from None
        except Exception as e:
            LOGGER.critical("Exception:\n%s",traceback.format_exc())
            raise NoApplicableCode(str(e), code=500) from None

    #
    # Describe
    #
    def describe(self, service: Service, map_uri: Optional[str]=None) -> XMLDocument:
        """ Return process description
        """
        identifiers = self.identifiers

        if not identifiers:
            raise MissingParameterValue('', 'identifier')

        # 'all' keyword means all processes
        if 'all' in (ident.lower() for ident in identifiers):
            identifiers = [p.identifier for p in service.processes]

        identifier_elements = []
        identifier_elements.extend(p.describe_xml() for p in self.get_processes_for_request(service, identifiers, map_uri=map_uri))

        doc = WPS.ProcessDescriptions(*identifier_elements)
        doc.attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] = \
            'http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsDescribeProcess_response.xsd'
        doc.attrib['service'] = 'WPS'
        doc.attrib['version'] = '1.0.0'
        doc.attrib['{http://www.w3.org/XML/1998/namespace}lang'] = 'en-US'
        return doc

        
    # Create response
    def create_response( self, process, uuid, status_url=None) -> OWSResponse:
        """ Create the response for execute request for
            handling OWS Response
        """
        return OWSResponse(process, self, uuid, status_url)

#
# Utilities
#

def _get_dataelement_value(value_el):
    """Return real value of XML Element (e.g. convert Element.FeatureCollection
    to String
    """

    if isinstance(value_el, lxml.etree._Element):
        return lxml.etree.tostring(value_el, encoding=str)
    else:
        return value_el


def _get_rawvalue_value(data, encoding=None):
    """Return real value of CDATA section"""

    try:
        if encoding is None or encoding == "":
            return data
        elif encoding == 'base64':
            return base64.b64decode(data)
        return base64.b64decode(data)
    except Exception:
        return data


def _get_reference_body(body_element):
    """Parses ReferenceInput Body element
    """

    body = None
    if len(body_element.getchildren()) > 0:
        value_el = body_element[0]
        body = _get_dataelement_value(value_el)
    else:
        body = _get_rawvalue_value(body_element.text)

    return body


def get_inputs_from_xml(doc):
    the_inputs = {}
    for input_el in xpath_ns(doc, '/wps:Execute/wps:DataInputs/wps:Input'):
        [identifier_el] = xpath_ns(input_el, './ows:Identifier')
        identifier = identifier_el.text

        if identifier not in the_inputs:
            the_inputs[identifier] = []

        literal_data = xpath_ns(input_el, './wps:Data/wps:LiteralData')
        if literal_data:
            value_el = literal_data[0]
            inpt = {}
            inpt['identifier'] = identifier_el.text
            inpt['data'] = str(value_el.text)
            inpt['uom'] = value_el.attrib.get('uom', '')
            inpt['datatype'] = value_el.attrib.get('datatype', '')
            the_inputs[identifier].append(inpt)
            continue

        complex_data = xpath_ns(input_el, './wps:Data/wps:ComplexData')
        if complex_data:
            complex_data_el = complex_data[0]
            inpt = {}
            inpt['identifier'] = identifier_el.text
            inpt['mimeType'] = complex_data_el.attrib.get('mimeType', '')
            inpt['encoding'] = complex_data_el.attrib.get(
                'encoding', '').lower()
            inpt['schema'] = complex_data_el.attrib.get('schema', '')
            inpt['method'] = complex_data_el.attrib.get('method', 'GET')
            if len(complex_data_el.getchildren()) > 0:
                value_el = complex_data_el[0]
                inpt['data'] = _get_dataelement_value(value_el)
            else:
                inpt['data'] = _get_rawvalue_value(
                    complex_data_el.text, inpt['encoding'])
            the_inputs[identifier].append(inpt)
            continue

        reference_data = xpath_ns(input_el, './wps:Reference')
        if reference_data:
            reference_data_el = reference_data[0]
            inpt = {}
            inpt['identifier'] = identifier_el.text
            inpt[identifier_el.text] = reference_data_el.text
            inpt['href'] = reference_data_el.attrib.get(
                '{http://www.w3.org/1999/xlink}href', '')
            inpt['mimeType'] = reference_data_el.attrib.get('mimeType', '')
            inpt['method'] = reference_data_el.attrib.get('method', 'GET')
            body_element = xpath_ns(reference_data_el, './wps:Body')
            if body_element:
                inpt['body'] = _get_reference_body(body_element[0])
            the_inputs[identifier].append(inpt)
            continue

        bbox_datas = xpath_ns(input_el, './wps:Data/wps:BoundingBoxData')
        if bbox_datas:
            for bbox_data in bbox_datas:
                bbox_data_el = bbox_data
                bbox = BoundingBox(bbox_data_el)
                inpt = {}
                inpt['identifier'] = identifier_el.text
                inpt['data'] = [bbox.minx, bbox.miny, bbox.maxx, bbox.maxy]
                inpt['dimensions'] = bbox.dimensions
                if bbox.crs:
                    inpt['crs'] = bbox.crs.id
                the_inputs[identifier].append(inpt)
    return the_inputs


def get_output_from_xml(doc):
    """
        Note that we ignore 'transmissionMode' since we 
        do not allow client to change it.
    """
    return {}


def get_data_from_kvp(data, part=None):
    """Get execute DataInputs and ResponseDocument from URL (key-value-pairs) encoding
    :param data: key:value pair list of the datainputs and responseDocument parameter
    :param part: DataInputs or similar part of input url
    """

    the_data = {}

    if data is None:
        return the_data

    for d in data.split(";"):
        try:
            io = {}
            fields = d.split('@')

            # First field is identifier and its value
            (identifier, val) = fields[0].split("=")
            io['identifier'] = identifier
            io['data'] = val

            # Get the attributes of the data
            for attr in fields[1:]:
                (attribute, attr_val) = attr.split('=')
                if attribute == 'xlink:href':
                    io['href'] = attr_val
                else:
                    io[attribute] = attr_val

            # Add the input/output with all its attributes and values to the
            # dictionary
            if part == 'DataInputs':
                if identifier not in the_data:
                    the_data[identifier] = []
                the_data[identifier].append(io)
            else:
                the_data[identifier] = io
        except Exception as e:
            LOGGER.warning(e)
            the_data[d] = {'identifier': d, 'data': ''}

    return the_data



