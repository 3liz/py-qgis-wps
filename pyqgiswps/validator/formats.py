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


from typing import NamedTuple, Optional


class _FORMAT(NamedTuple):
    mime_type: str
    extension: str
    schema: Optional[str] = None


class _FORMATS(NamedTuple):
    WKT: _FORMAT = _FORMAT('application/wkt', '.wkt')
    GEOJSON: _FORMAT = _FORMAT('application/vnd.geo+json', '.geojson')
    JSON: _FORMAT = _FORMAT('application/json', '.json')
    SHP: _FORMAT = _FORMAT('application/x-zipped-shp', '.zip')
    GML: _FORMAT = _FORMAT('application/gml+xml', '.gml')
    GEOTIFF: _FORMAT = _FORMAT('image/tiff; subtype=geotiff', '.tiff')
    WCS: _FORMAT = _FORMAT('application/xogc-wcs', '.xml')
    WCS100: _FORMAT = _FORMAT('application/x-ogc-wcs; version=1.0.0', '.xml')
    WCS110: _FORMAT = _FORMAT('application/x-ogc-wcs; version=1.1.0', '.xml')
    WCS20: _FORMAT = _FORMAT('application/x-ogc-wcs; version=2.0', '.xml')
    WFS: _FORMAT = _FORMAT('application/x-ogc-wfs', '.xml')
    WFS100: _FORMAT = _FORMAT('application/x-ogc-wfs; version=1.0.0', '.xml')
    WFS110: _FORMAT = _FORMAT('application/x-ogc-wfs; version=1.1.0', '.xml')
    WFS20: _FORMAT = _FORMAT('application/x-ogc-wfs; version=2.0', '.xml')
    WMS: _FORMAT = _FORMAT('application/x-ogc-wms', '.xml')
    WMS130: _FORMAT = _FORMAT('application/x-ogc-wms; version=1.3.0', '.xml')
    WMS110: _FORMAT = _FORMAT('application/x-ogc-wms; version=1.1.0', '.xml')
    WMS100: _FORMAT = _FORMAT('application/x-ogc-wms; version=1.0.0', '.xml')
    TEXT: _FORMAT = _FORMAT('text/plain', '.txt')
    NETCDF: _FORMAT = _FORMAT('application/x-netcdf', '.nc')
    ANY: _FORMAT = _FORMAT('application/octet-stream', '.nc')


FORMATS = _FORMATS()
