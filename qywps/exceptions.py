##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# Authors: Alex Morega & Calin Ciociu
#                                                                #  
# Copyrigth 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################


"""
OGC OWS and WPS Exceptions

Based on OGC OWS, WPS and

http://lists.opengeospatial.org/pipermail/wps-dev/2013-October/000335.html
"""

from tornado.escape import xhtml_escape as escape
from tornado.web import HTTPError

import logging

from qywps import __version__

HTTPException = HTTPError

LOGGER = logging.getLogger('QYWPS')


class NoApplicableCode(HTTPException):
    """No applicable code exception implementation

    also

    Base exception class
    """

    code = 400
    locator = ""

    def __init__(self, description, locator="", code=400, log_message=None, *args, **kwargs):
        self.code = code
        self.description = description
        self.locator = locator
        msg = 'Exception: code: %s, description: %s, locator: %s' % (self.code, self.description, self.locator)
        LOGGER.error(msg)
        super().__init__(status_code=code, log_message=log_message, *args, **kwargs)

    @property
    def name(self):
        """The status name."""
        return self.__class__.__name__

    def get_headers(self):
        """Get a list of headers."""
        return [('Content-Type', 'text/xml')]

    def get_description(self):
        """Get the description."""
        if self.description:
            return '''<ows:ExceptionText>%s</ows:ExceptionText>''' % escape(self.description)
        else:
            return ''

    def get_body(self):
        """Get the XML body."""
        return (
            '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/ows/1.1 http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd" version="1.0.0">\n'  # noqa
            '  <ows:Exception exceptionCode="%(name)s" locator="%(locator)s" >\n'
            '      %(description)s\n'
            '  </ows:Exception>\n'
            '</ows:ExceptionReport>'
        ) % {
            'version': __version__,
            'code': self.code,
            'locator': escape(self.locator),
            'name': escape(self.name),
            'description': self.get_description()
        }


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

