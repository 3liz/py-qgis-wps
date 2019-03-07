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
import lxml
import lxml.etree

import base64
from qywps import WPS
from qywps.app.basic import xpath_ns
from qywps.inout.basic import LiteralInput, ComplexInput, BBoxInput
from qywps.exceptions import (NoApplicableCode, 
                              OperationNotSupported, 
                              MissingParameterValue, 
                              VersionNegotiationFailed,
                              InvalidParameterValue, 
                              FileSizeExceeded)
from qywps import configuration
from qywps.validator.mode import MODE
from qywps.inout.literaltypes import AnyValue, NoValue, ValuesReference, AllowedValue

from qywps.inout.formats import Format
from qywps.owsutils.ows import BoundingBox

import json

from urllib.parse import urlparse

LOGGER = logging.getLogger("QYWPS")

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

        cfg = configuration.get_config('server')

        self.timeout    = cfg.getint('response_timeout')
        self.expiration = cfg.getint('response_expiration')

    @staticmethod
    def parse_get_request(handler):
        """ HTTP GET request parser

            :return: A WPSRequest instance
        """
        service = handler.get_query_argument('service')
        if service.lower() != 'wps':
            raise InvalidParameterValue('parameter SERVICE [%s] not supported' % service, 'service')

        operation = handler.get_query_argument('request').lower()

        wpsrequest = WPSRequest()

        _get_query_param = handler.get_query_argument

        def parse_get_getresults():
            """ Parse GET GetResults
            """
            wpsrequest.results_uuid = _get_query_param('uuid')

        def parse_get_getcapabilities():
            """Parse GET GetCapabilities request
            """
            acceptedversions =  _get_query_param('acceptversions', None)
            wpsrequest.check_accepted_versions(acceptedversions)

        def parse_get_describeprocess():
            """Parse GET DescribeProcess request
            """
            version = _get_query_param('version', None)
            wpsrequest.check_and_set_version(version)

            language = _get_query_param('language', None)
            wpsrequest.check_and_set_language(language)

            wpsrequest.identifiers = _get_query_param('identifier').split(',')

        def parse_get_execute():
            """Parse GET Execute request
            """
            version = _get_query_param('version', None)
            wpsrequest.check_and_set_version(version)

            language = _get_query_param('language', None)
            wpsrequest.check_and_set_language(language)

            wpsrequest.identifier = _get_query_param('identifier')
            
            timeout = _get_query_param('timeout', None)
            wpsrequest.check_and_set_timeout(timeout)

            expire = _get_query_param('expire', None)
            wpsrequest.check_and_set_expiration(expire)

            wpsrequest.store_execute = _get_query_param('storeExecuteResponse', 'false')
            # XXX If storeExecuteResponse is set to true then we enforce 
            # status supports
            wpsrequest.status = wpsrequest.store_execute
            wpsrequest.lineage = _get_query_param('lineage', 'false')

            wpsrequest.inputs = get_data_from_kvp(_get_query_param('datainputs', None), 'DataInputs')
            wpsrequest.outputs = {}

            # take responseDocument preferably
            resp_outputs = get_data_from_kvp(_get_query_param('responsedocument', None))
            raw_outputs  = get_data_from_kvp(_get_query_param('rawdataoutput', None))
            wpsrequest.raw = False
            if resp_outputs:
                wpsrequest.outputs = resp_outputs
            elif raw_outputs:
                wpsrequest.outputs = raw_outputs
                wpsrequest.raw = True
                # executeResponse XML will not be stored and no updating of
                # status
                wpsrequest.store_execute = 'false'
                wpsrequest.status = 'false'

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
    def parse_post_request(handler):
        """Factory function returing propper parsing function
        """
        try:
            doc = lxml.etree.fromstring(handler.request.body)
        except Exception as e:
            raise NoApplicableCode(e.msg)

        wpsrequest = WPSRequest()

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
            wpsrequest.lineage = 'false'
            wpsrequest.store_execute = 'false'
            wpsrequest.status = 'false'
            wpsrequest.inputs = get_inputs_from_xml(doc)
            wpsrequest.outputs = get_output_from_xml(doc)
            wpsrequest.raw = False
            if xpath_ns(doc, '/wps:Execute/wps:ResponseForm/wps:RawDataOutput'):
                wpsrequest.raw = True
                # executeResponse XML will not be stored
                wpsrequest.store_execute = 'false'

            # check if response document tag has been set then retrieve
            response_document = xpath_ns(
                doc, './wps:ResponseForm/wps:ResponseDocument')
            if len(response_document) > 0:
                wpsrequest.lineage = response_document[
                    0].attrib.get('lineage', 'false')
                wpsrequest.store_execute = response_document[
                    0].attrib.get('storeExecuteResponse', 'false')
                # XXX If storeExecuteResponse is set then we enforce
                # the status supports
                wpsrequest.status = wpsrequest.store_execute
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
            'inputs': dict((i, [inpt.json for inpt in self.inputs[i]]) for i in self.inputs),
            'outputs': self.outputs,
            'raw': self.raw
        }

        return json.dumps(obj, allow_nan=False)

    @json.setter
    def json(self, value):
        """init this request from json back again

        :param value: the json (not string) representation
        """

        self.operation = value['operation']
        self.version = value['version']
        self.language = value['language']
        self.identifiers = value['identifiers']
        self.store_execute = value['store_execute']
        self.status = value['store_execute']
        self.lineage = value['lineage']
        self.outputs = value['outputs']
        self.raw = value['raw']
        self.inputs = {}

        for identifier in value['inputs']:
            inpt = None
            inpt_defs = value['inputs'][identifier]

            for inpt_def in inpt_defs:

                if inpt_def['type'] == 'complex':
                    inpt = ComplexInput(
                        identifier=inpt_def['identifier'],
                        title=inpt_def.get('title'),
                        abstract=inpt_def.get('abstract'),
                        workdir=inpt_def.get('workdir'),
                        data_format=Format(
                            schema=inpt_def['data_format'].get('schema'),
                            extension=inpt_def['data_format'].get('extension'),
                            mime_type=inpt_def['data_format']['mime_type'],
                            encoding=inpt_def['data_format'].get('encoding')
                        ),
                        supported_formats=[
                            Format(
                                schema=infrmt.get('schema'),
                                extension=infrmt.get('extension'),
                                mime_type=infrmt['mime_type'],
                                encoding=infrmt.get('encoding')
                            ) for infrmt in inpt_def['supported_formats']
                        ],
                        mode=MODE.NONE
                    )
                    inpt.file = inpt_def['file']
                elif inpt_def['type'] == 'literal':

                    allowed_values = []
                    for allowed_value in inpt_def['allowed_values']:
                        if allowed_value['type'] == 'anyvalue':
                            allowed_values.append(AnyValue())
                        elif allowed_value['type'] == 'novalue':
                            allowed_values.append(NoValue())
                        elif allowed_value['type'] == 'valuesreference':
                            allowed_values.append(ValuesReference())
                        elif allowed_value['type'] == 'allowedvalue':
                            allowed_values.append(AllowedValue(
                                allowed_type=allowed_value['allowed_type'],
                                value=allowed_value['value'],
                                minval=allowed_value['minval'],
                                maxval=allowed_value['maxval'],
                                spacing=allowed_value['spacing'],
                                range_closure=allowed_value['range_closure']
                            ))

                    inpt = LiteralInput(
                        identifier=inpt_def['identifier'],
                        title=inpt_def.get('title'),
                        abstract=inpt_def.get('abstract'),
                        data_type=inpt_def.get('data_type'),
                        workdir=inpt_def.get('workdir'),
                        allowed_values=AnyValue,
                        uoms=inpt_def.get('uoms'),
                        mode=inpt_def.get('mode')
                    )
                    inpt.uom = inpt_def.get('uom')
                    inpt.data = inpt_def.get('data')

                elif inpt_def['type'] == 'bbox':
                    inpt = BBoxInput(
                        identifier=inpt_def['identifier'],
                        title=inpt_def['title'],
                        abstract=inpt_def['abstract'],
                        crss=inpt_def['crs'],
                        dimensions=inpt_def['dimensions'],
                        workdir=inpt_def['workdir'],
                        mode=inpt_def['mode']
                    )
                    inpt.ll = inpt_def['bbox'][0]
                    inpt.ur = inpt_def['bbox'][1]

            if identifier in self.inputs:
                self.inputs[identifier].append(inpt)
            else:
                self.inputs[identifier] = [inpt]


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
            header_element = xpath_ns(reference_data_el, './wps:Header')
            if header_element:
                inpt['header'] = _get_reference_header(header_element)
            body_element = xpath_ns(reference_data_el, './wps:Body')
            if body_element:
                inpt['body'] = _get_reference_body(body_element[0])
            bodyreference_element = xpath_ns(reference_data_el,
                                             './wps:BodyReference')
            if bodyreference_element:
                inpt['bodyreference'] = _get_reference_bodyreference(
                    bodyreference_element[0])
            the_inputs[identifier].append(inpt)
            continue

        bbox_datas = xpath_ns(input_el, './wps:Data/wps:BoundingBoxData')
        if bbox_datas:
            for bbox_data in bbox_datas:
                bbox_data_el = bbox_data
                bbox = BoundingBox(bbox_data_el)
                the_inputs[identifier].append(bbox)
    return the_inputs


def get_output_from_xml(doc):
    the_output = {}

    if xpath_ns(doc, '/wps:Execute/wps:ResponseForm/wps:ResponseDocument'):
        for output_el in xpath_ns(doc, '/wps:Execute/wps:ResponseForm/wps:ResponseDocument/wps:Output'):
            [identifier_el] = xpath_ns(output_el, './ows:Identifier')
            outpt = {}
            outpt[identifier_el.text] = ''
            outpt['asReference'] = output_el.attrib.get('asReference', 'false')
            the_output[identifier_el.text] = outpt

    elif xpath_ns(doc, '/wps:Execute/wps:ResponseForm/wps:RawDataOutput'):
        for output_el in xpath_ns(doc, '/wps:Execute/wps:ResponseForm/wps:RawDataOutput'):
            [identifier_el] = xpath_ns(output_el, './ows:Identifier')
            outpt = {}
            outpt[identifier_el.text] = ''
            outpt['mimetype'] = output_el.attrib.get('mimeType', '')
            outpt['encoding'] = output_el.attrib.get('encoding', '')
            outpt['schema'] = output_el.attrib.get('schema', '')
            outpt['uom'] = output_el.attrib.get('uom', '')
            the_output[identifier_el.text] = outpt

    return the_output


def get_data_from_kvp(data, part=None):
    """Get execute DataInputs and ResponseDocument from URL (key-value-pairs) encoding
    :param data: key:value pair list of the datainputs and responseDocument parameter
    :param part: DataInputs or similar part of input url
    """

    the_data = {}

    if data is None:
        return None

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


def _check_version(version):
    """ check given version
    """
    if version != '1.0.0':
        return False
    else:
        return True


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
    except:
        return data


def _get_reference_header(header_element):
    """Parses ReferenceInput Header element
    """
    header = {}
    header['key'] = header_element.attrib('key')
    header['value'] = header_element.attrib('value')
    return header


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


def _get_reference_bodyreference(referencebody_element):
    """Parse ReferenceInput BodyReference element
    """
    return referencebody_element.attrib.get(
        '{http://www.w3.org/1999/xlink}href', '')

