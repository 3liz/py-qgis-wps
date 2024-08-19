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

from typing import (
    Any,
    Callable,
    Mapping,
    Sequence,
)

import pyqgiswps.ogc as ogc

from pyqgiswps.app.common import Metadata
from pyqgiswps.app.request import WPSRequest, WPSResponse
from pyqgiswps.inout import WPSInput, WPSOutput

LOGGER = logging.getLogger('SRVLOG')

WPSHandler = Callable[
    [WPSRequest, WPSResponse, Mapping[str, Any]],
    WPSResponse,
]


class WPSProcess(*ogc.exports.WPSProcess):
    """ Define a process descriptor
    """

    def __init__(
        self,
        handler: WPSHandler,
        identifier: str,
        title: str,
        *,
        abstract: str = '',
        metadata: Sequence[Metadata] = (),
        inputs: Sequence[WPSInput] = (),
        outputs: Sequence[WPSOutput] = (),
        version: str = 'None',
        keywords: Sequence[str] = (),
        **kwargs,
    ):

        self.handler = handler
        self.identifier = identifier
        self.title = title
        self.abstract = abstract
        self.metadata = metadata
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.workdir = None
        self.keywords = keywords

    def clean(self):
        """ Clean the process working dir and other temporary files
        """
        pass

        # LOGGER.info("Removing temporary working directory: %s" % self.workdir)
        # try:
        #    if os.path.isdir(self.workdir):
        #        shutil.rmtree(self.workdir)
        # except Exception as err:
        #    LOGGER.error('Unable to remove directory: %s', err)

    def set_workdir(self, workdir):
        """Set working dir for all inputs and outputs

        this is the directory, where all the data are being stored to
        """

        self.workdir = workdir
        for inpt in self.inputs:
            inpt.workdir = workdir

        for outpt in self.outputs:
            outpt.workdir = workdir
