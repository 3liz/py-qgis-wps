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
"""List of know mimetypes"""

# List of known complex data formats
# you can use any other, but thise are widly known and supported by popular
# software packages
# based on Web Processing Service Best Practices Discussion Paper, OGC 12-029
# http://opengeospatial.org/standards/wps

from lxml.builder import ElementMaker
from collections import namedtuple
import mimetypes
from pyqgiswps.validator.mode import MODE
from pyqgiswps.validator.base import emptyvalidator

_FORMAT = namedtuple('FormatDefinition', 'mime_type,'
                     'extension, schema')
_FORMATS = namedtuple('FORMATS', 'GEOJSON, JSON, SHP, GML, GEOTIFF, WCS,'
                                 'WCS100, WCS110, WCS20, WFS, WFS100,'
                                 'WFS110, WFS20, WMS, WMS130, WMS110,'
                                 'WMS100,'
                                 'TEXT, NETCDF,')

FORMATS = _FORMATS(
    GEOJSON = _FORMAT('application/vnd.geo+json', '.geojson', None),
    JSON    = _FORMAT('application/json', '.json', None),
    SHP     = _FORMAT('application/x-zipped-shp', '.zip', None),
    GML     = _FORMAT('application/gml+xml', '.gml', None),
    GEOTIFF = _FORMAT('image/tiff; subtype=geotiff', '.tiff', None),
    WCS     = _FORMAT('application/xogc-wcs', '.xml', None),
    WCS100  = _FORMAT('application/x-ogc-wcs; version=1.0.0', '.xml', None),
    WCS110  = _FORMAT('application/x-ogc-wcs; version=1.1.0', '.xml', None),
    WCS20   = _FORMAT('application/x-ogc-wcs; version=2.0', '.xml', None),
    WFS     = _FORMAT('application/x-ogc-wfs', '.xml', None),
    WFS100  = _FORMAT('application/x-ogc-wfs; version=1.0.0', '.xml', None),
    WFS110  = _FORMAT('application/x-ogc-wfs; version=1.1.0', '.xml', None),
    WFS20   = _FORMAT('application/x-ogc-wfs; version=2.0', '.xml', None),
    WMS     = _FORMAT('application/x-ogc-wms', '.xml', None),
    WMS130  = _FORMAT('application/x-ogc-wms; version=1.3.0', '.xml', None),
    WMS110  = _FORMAT('application/x-ogc-wms; version=1.1.0', '.xml', None),
    WMS100  = _FORMAT('application/x-ogc-wms; version=1.0.0', '.xml', None),
    TEXT    = _FORMAT('text/plain', '.txt', None),
    NETCDF  = _FORMAT('application/x-netcdf', '.nc', None),
)


def _get_mimetypes():
    """Add FORMATS to system wide mimetypes
    """
    mimetypes.init()
    for wps_format in FORMATS:
        mimetypes.add_type(wps_format.mime_type, wps_format.extension, True)


_get_mimetypes()


class Format:
    """Input/output format specification

    Predefined Formats are stored in :class:`pyqgiswps.inout.formats.FORMATS`

    :param str mime_type: mimetype definition
    :param str schema: xml schema definition
    :param str encoding: base64 or not
    :param function validate: function, which will perform validation. e.g.
    :param number mode: validation mode
    :param str extension: file extension
    """

    @staticmethod
    def from_definition(formatdef):          
        return Format(**formatdef._asdict())


    def __init__(self, mime_type,
                 schema=None, encoding=None,
                 validate=emptyvalidator, mode=MODE.SIMPLE,
                 extension=None):
        """Constructor
        """

        self._mime_type = None
        self._encoding = None
        self._schema = None

        self.mime_type = mime_type
        self.encoding = encoding
        self.schema = schema
        self.validate = validate
        self.extension = extension

    @property
    def mime_type(self):
        """Get format mime type
        :rtype: String
        """

        return self._mime_type

    @mime_type.setter
    def mime_type(self, mime_type):
        """Set format mime type
        """
        try:
            # support Format('GML')
            formatdef = getattr(FORMATS, mime_type)
            self._mime_type = formatdef.mime_type
        except AttributeError:
            # if we don't have this as a shortcut, assume it's a real mime type
            self._mime_type = mime_type

    @property
    def encoding(self):
        """Get format encoding
        :rtype: String
        """

        if self._encoding:
            return self._encoding
        else:
            return ''

    @encoding.setter
    def encoding(self, encoding):
        """Set format encoding
        """

        self._encoding = encoding

    @property
    def schema(self):
        """Get format schema
        :rtype: String
        """
        if self._schema:
            return self._schema
        else:
            return ''

    @schema.setter
    def schema(self, schema):
        """Set format schema
        """
        self._schema = schema

    def same_as(self, frmt):
        """Check input frmt, if it seems to be the same as self
        """
        return all([frmt.mime_type == self.mime_type,
                    frmt.encoding == self.encoding,
                    frmt.schema == self.schema])

    def describe_xml(self):
        """Return describe process response element
        """

        elmar = ElementMaker()
        doc = elmar.Format(
            elmar.MimeType(self.mime_type)
        )

        if self.encoding:
            doc.append(elmar.Encoding(self.encoding))

        if self.schema:
            doc.append(elmar.Schema(self.schema))

        return doc

    @property
    def json(self):
        """Get format as json
        :rtype: dict
        """
        return {
            'mime_type': self.mime_type,
            'encoding': self.encoding,
            'schema': self.schema,
            'extension': self.extension
        }

    @json.setter
    def json(self, jsonin):
        """Set format from json
        :param jsonin:
        """

        self.mime_type = jsonin['mime_type']
        self.encoding = jsonin['encoding']
        self.schema = jsonin['schema']
        self.extension = jsonin['extension']


def get_format(frmt, validator=None):
    """Return Format instance based on given pyqgiswps.inout.FORMATS keyword
    """
    # TODO this should be probably removed, it's used only in tests

    outfrmt = None

    if frmt in FORMATS._asdict():
        formatdef = FORMATS._asdict()[frmt]
        outfrmt = Format(**formatdef._asdict())
        outfrmt.validate = validator
        return outfrmt
    else:
        return Format('None', validate=validator)
