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
"""Validatating functions for various inputs
"""


import logging

from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.validator.complexvalidator import validategeojson, validategeotiff, validategml, validateshapefile

LOGGER = logging.getLogger('SRVLOG')

_VALIDATORS = {
    'application/vnd.geo+json': validategeojson,
    'application/json': validategeojson,
    'application/x-zipped-shp': validateshapefile,
    'application/gml+xml': validategml,
    'image/tiff; subtype=geotiff': validategeotiff,
    'application/xogc-wcs': emptyvalidator,
    'application/x-ogc-wcs; version=1.0.0': emptyvalidator,
    'application/x-ogc-wcs; version=1.1.0': emptyvalidator,
    'application/x-ogc-wcs; version=2.0': emptyvalidator,
    'application/x-ogc-wfs': emptyvalidator,
    'application/x-ogc-wfs; version=1.0.0': emptyvalidator,
    'application/x-ogc-wfs; version=1.1.0': emptyvalidator,
    'application/x-ogc-wfs; version=2.0': emptyvalidator,
    'application/x-ogc-wms': emptyvalidator,
    'application/x-ogc-wms; version=1.3.0': emptyvalidator,
    'application/x-ogc-wms; version=1.1.0': emptyvalidator,
    'application/x-ogc-wms; version=1.0.0': emptyvalidator,
}


def get_validator(identifier):
    """Return validator function for given mime_type

    identifier can be either full mime_type or data type identifier
    """

    if identifier in _VALIDATORS:
        LOGGER.debug('validator: %s', _VALIDATORS[identifier])
        return _VALIDATORS[identifier]
    else:
        LOGGER.debug('empty validator')
        return emptyvalidator
