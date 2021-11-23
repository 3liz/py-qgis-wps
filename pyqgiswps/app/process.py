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
import pyqgiswps.ogc as ogc

LOGGER = logging.getLogger('SRVLOG')

class WPSProcess( *ogc.exports.WPSProcess ):
    """ Define a process descriptor
    """
    def __init__(self, handler, identifier, title, abstract='',
                 profile=[],
                 metadata=[],
                 inputs=[],
                 outputs=[],
                 version='None',
                 **kwargs):

        self.handler = handler
        self.identifier = identifier
        self.title = title
        self.abstract = abstract
        self.metadata = metadata
        self.profile = profile
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.workdir = None

        # Keep this for test compatibility
        self.store_supported = True
        self.status_supported = True

    def clean(self):
        """ Clean the process working dir and other temporary files
        """
        pass

        #LOGGER.info("Removing temporary working directory: %s" % self.workdir)
        #try:
        #    if os.path.isdir(self.workdir):
        #        shutil.rmtree(self.workdir)
        #except Exception as err:
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


