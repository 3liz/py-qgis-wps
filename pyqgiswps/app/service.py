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
from pyqgiswps.app.request import WPSRequest
from pyqgiswps.app.process import WPSProcess
from pyqgiswps.config import confservice
from pyqgiswps.exceptions import (MissingParameterValue, NoApplicableCode, InvalidParameterValue)
from pyqgiswps.inout.literaltypes import JsonValue
from pyqgiswps.inout.inputs import ComplexInput, LiteralInput, BoundingBoxInput
from pyqgiswps.executors.logstore import STATUS
from pyqgiswps.executors.processingexecutor import ProcessingExecutor, UnknownProcessError
from pyqgiswps.owsutils.ows import BoundingBox

from collections import deque
import os
import copy

from typing import TypeVar, Iterable, Optional, Union, Any

# Define generic WPS Input
WPSInput = Union[ComplexInput, LiteralInput, BoundingBoxInput]

LOGGER = logging.getLogger('SRVLOG')


ResponseDocument = TypeVar('ResponseDocument')


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

    def get_processes_for_request(self, idents: Iterable[str], 
                                  map_uri: Optional[str]=None) -> Iterable[WPSProcess]:
        try:
            return self.get_processes(idents, map_uri)
        except UnknownProcessError as exc:
            raise InvalidParameterValue("Unknown process %s" % exc, "identifier") from None
        except Exception as e:
            LOGGER.critical("Exception:\n%s",traceback.format_exc())
            raise NoApplicableCode(str(e), code=500) from None


    def get_results(self, uuid: str) -> Any:
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
                      map_uri: Optional[str]=None) -> ResponseDocument:
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

        self._check_request( process, wps_request )

        workdir = os.path.abspath(confservice.get('server','workdir'))
        workdir = os.path.join(workdir, str(uuid))

        # Create working directory if it does not exists
        os.makedirs(workdir, exist_ok=True)
        
        process.set_workdir(workdir)
   
        # Get status url
        status_url = self._status_url(uuid, wps_request)

        # Create response object
        wps_response = wps_request.create_response( process, uuid, status_url=status_url)

        if wps_request.store_execute == 'true':
            # Setting STORE_AND_UPDATE_STATUS will trigger
            # asynchronous requests
            wps_response.status = STATUS.STORE_AND_UPDATE_STATUS
            LOGGER.debug("Update status enabled")

        if wps_request.raw:
            raise NotImplementedError("Raw output is not implemented")
 
        document = await self.executor.execute(wps_request, wps_response)

        return document

    def _check_request(self, process: WPSProcess, wps_request: WPSRequest):
        """ Check request
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


