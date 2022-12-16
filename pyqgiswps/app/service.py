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
from pyqgiswps.app.request import WPSRequest
from pyqgiswps.app.process import WPSProcess
from pyqgiswps.config import confservice
from pyqgiswps.exceptions import (
    MissingParameterValue,
    NoApplicableCode,
)
from pyqgiswps.inout.inputs import ComplexInput, LiteralInput, BoundingBoxInput
from pyqgiswps.executors.processingexecutor import ProcessingExecutor

import os
import copy

from typing import Iterable, Optional, Union, Any, TypeVar, Iterator

Json = TypeVar('Json')

# Define generic WPS Input
WPSInput = Union[ComplexInput, LiteralInput, BoundingBoxInput]

LOGGER = logging.getLogger('SRVLOG')


class Service():

    """ The top-level object that represents a WPS service.

    :param processes: A list of :class:`~Process` objects that are
                      provided by this service.

    """

    def __init__(self, processes: Iterable[WPSProcess] = []) -> None:
        # Get and start executor
        self.executor = ProcessingExecutor(processes)

    def terminate(self) -> None:
        self.executor.terminate()

    @property
    def processes(self) -> Iterable[WPSProcess]:
        return self.executor.list_processes()

    def get_process(self, ident: str, map_uri: Optional[str] = None) -> WPSProcess:
        return self.get_processes((ident,), map_uri=map_uri)[0]

    def get_processes(self, idents: Iterable[str], map_uri: Optional[str] = None) -> Iterable[WPSProcess]:
        return self.executor.get_processes(idents, map_uri=map_uri)

    def get_results(self, uuid: str) -> Any:
        doc = self.executor.get_results(uuid)
        if doc is None:
            raise NoApplicableCode(f"No results found for {uuid}", code=404)

        return doc

    def get_status(self, uuid: Optional[str] = None, **kwargs) -> Union[Json, Iterator]:
        """ Return the status of the stored processes
        """
        return self.executor.get_status(uuid, **kwargs)

    def delete_results(self, uuid: str, force: bool = False) -> bool:
        """ Delete process results and status
        """
        return self.executor.delete_results(uuid, force)

    def kill_job(self, uuid: str, pid: Optional[int] = None) -> bool:
        """ Kill process job
        """
        return self.executor.kill_job(uuid, pid)

    async def execute_process(self, process: WPSProcess, wps_request: WPSRequest, uuid: str) -> bytes:
        """Parse and perform Execute WPS request call
        """
        # make deep copy of the process instance
        # so that processes are not overriding each other
        # just for execute
        process = copy.deepcopy(process)

        self.validate_request_inputs(process, wps_request)

        workdir = os.path.abspath(confservice.get('server', 'workdir'))
        workdir = os.path.join(workdir, str(uuid))

        # Create working directory if it does not exists
        os.makedirs(workdir, exist_ok=True)

        process.set_workdir(workdir)

        # Create response object
        wps_response = wps_request.create_response(process, uuid)

        document = await self.executor.execute(wps_request, wps_response)

        return document

    def validate_request_inputs(self, process: WPSProcess, wps_request: WPSRequest):
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
                    raise MissingParameterValue(inpt.identifier, inpt.identifier)
                else:
                    # Do not add the input
                    pass
            else:
                inputs = wps_request.inputs[inpt.identifier]
                if len(inputs) < inpt.min_occurs:
                    raise MissingParameterValue(description='Missing input data', locator=inpt.identifier)

                data_inputs[inpt.identifier] = [inpt.clone().validate_input(inp) for inp in inputs]

        wps_request.inputs = data_inputs

        # Validate outputs
        for outpt in process.outputs:
            out = wps_request.outputs.get(outpt.identifier)
            if out:
                outpt.validate_output(out)
