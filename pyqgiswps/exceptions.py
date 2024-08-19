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
# Original Author: Alex Morega & Calin Ciociu


"""
OGC OWS and WPS Exceptions

Based on OGC OWS, WPS and

http://lists.opengeospatial.org/pipermail/wps-dev/2013-October/000335.html
"""

import logging

from tornado.web import HTTPError

HTTPException = HTTPError

LOGGER = logging.getLogger('SRVLOG')


class NoApplicableCode(HTTPException):
    """No applicable code exception implementation

    also

    Base exception class
    """

    code = 400
    locator = ""

    def __init__(self, description="", locator="", code=400, log_message=None, *args, **kwargs):
        self.code = code
        self.description = description
        self.locator = locator
        msg = f'Exception: code: {self.code}, description: {self.description}, locator: {self.locator}'
        LOGGER.error(msg)
        super().__init__(status_code=code, log_message=log_message, *args, **kwargs)

    @property
    def name(self) -> str:
        """The status name."""
        return self.__class__.__name__


class InvalidParameterValue(NoApplicableCode):
    """Invalid parameter value exception implementation
    """
    code = 400


class MissingParameterValue(NoApplicableCode):
    """Missing parameter value exception implementation
    """
    code = 400


class FileSizeExceeded(NoApplicableCode):
    """File size exceeded exception implementation
    """
    code = 400


class VersionNegotiationFailed(NoApplicableCode):
    """Version negotiation exception implementation
    """
    code = 400


class OperationNotSupported(NoApplicableCode):
    """Operation not supported exception implementation
    """
    code = 501


class StorageNotSupported(NoApplicableCode):
    """Storage not supported exception implementation
    """
    code = 400


class ProcessException(Exception):
    """ Exception occured in handler
    """
    pass


class ExecutorError(Exception):
    """ Exception occured in executor
    """
    pass


class UnknownProcessError(ExecutorError):
    pass


class StorageNotFound(ExecutorError):
    pass
