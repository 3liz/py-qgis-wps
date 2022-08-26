#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
"""List of know mimetypes"""

# List of known complex data formats
# you can use any other, but thise are widly known and supported by popular
# software packages
# based on Web Processing Service Best Practices Discussion Paper, OGC 12-029
# http://opengeospatial.org/standards/wps


from collections import namedtuple

_FORMAT = namedtuple('FormatDefinition', 'mime_type,'
                     'extension, schema')
_FORMATS = namedtuple('FORMATS', 'WKT, GEOJSON, JSON, SHP, GML, GEOTIFF, WCS,'
                                 'WCS100, WCS110, WCS20, WFS, WFS100,'
                                 'WFS110, WFS20, WMS, WMS130, WMS110,'
                                 'WMS100,'
                                 'TEXT, NETCDF, ANY')

FORMATS = _FORMATS(
    WKT     = _FORMAT('application/wkt', '.wkt', None),
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
    ANY     = _FORMAT('application/octet-stream', '.nc', None),
)


