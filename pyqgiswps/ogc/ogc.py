#
# Copyright 2018-2021 3liz
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
from enum import Enum


OGCTYPE = {
    'length': 'urn:ogc:def:dataType:OGC:1.1:length',
    'scale': 'urn:ogc:def:dataType:OGC:1.1:scale',
    'time': 'urn:ogc:def:dataType:OGC:1.1:time',
    'date': 'urn:ogc:def:dataType:OGC:1.1:date',
    'dateTime': 'urn:ogc:def:dataType:OGC:1.1:dateTime',
    'angle': 'urn:ogc:def:dataType:OGC:1.1:angle',
    'string': 'urn:ogc:def:dataType:OGC:1.1:string',
    'boolean': 'urn:ogc:def:dataType:OGC:1.1:boolean',
    'anyURI': 'urn:ogc:def:dataType:OGC:1.1:anyURI',
    'integer': 'urn:ogc:def:dataType:OGC:1.1:integer',
    'float': 'urn:ogc:def:dataType:OGC:1.1:float'
}

_NUMBER_SCHEMA = { 'type': 'number' }

OGCTYPE_SCHEMA = {
    'length': _NUMBER_SCHEMA,
    'scale': _NUMBER_SCHEMA,
    'time': { 'type': 'string', 'format': 'date' },
    'date': { 'type': 'string', 'format': 'date' },
    'dateTime': { 'type': 'string', 'format': 'date-time' },
    'gridLength': _NUMBER_SCHEMA,
    'angle': _NUMBER_SCHEMA,
    'string': { 'type': 'string' },
    'boolean': { 'type': 'boolean' },
    'anyURI': { 'type': 'string', 'format': 'uri' },
    'integer': { 'type': 'integer' },
    'float': _NUMBER_SCHEMA,
}


# For UCUM references, 
# see
# * https://ucum.org/ucum-essence.xml
# * https://ucum.org/trac

OGCUNIT = {
    'degree': 'urn:ogc:def:uom:UCUM:deg',
    'degrees': 'urn:ogc:def:uom:UCUM:deg',
    'meter': 'urn:ogc:def:uom:UCUM:m',
    'metre': 'urn:ogc:def:uom:UCUM:m',
    'metres': 'urn:ogc:def:uom:UCUM:m',
    'meters': 'urn:ogc:def:uom:UCUM:m',
    'm': 'urn:ogc:def:uom:UCUM:m',
    'unity': 'urn:ogc:def:uom:OGC:1.0:unity',
    'feet': 'urn:ogc:def:uom:OGC:1.0:feet',
    'gridspacing': 'urn:ogc:def:uom:OGC:1.0:gridspacing',
    'radians': 'urn:ogc:def:uom:UCUM:rad',
    'radian' : 'urn:ogc:def:uom:UCUM:rad',
    'rad' : 'urn:ogc:def:uom:UCUM:rad',
    'kilometer': 'urn:ogc:def:uom:UCUM:km',
    'kilometers': 'urn:ogc:def:uom:UCUM:km',
    'km': 'urn:ogc:def:uom:UCUM:km',
    'centimeter': 'urn:ogc:def:uom:UCUM:cm',
    'centimeters': 'urn:ogc:def:uom:UCUM:cm',
    'cm': 'urn:ogc:def:uom:UCUM:cm',
    'millimeter': 'urn:ogc:def:uom:UCUM:mm',
    'millimeters': 'urn:ogc:def:uom:UCUM:mm',
    'mm': 'urn:ogc:def:uom:UCUM:mm',
    'mile': 'urn:ogc:def:uom:UCUM:[mi_i]',
    'miles': 'urn:ogc:def:uom:UCUM:[mi_i]',
    'nautical mile': 'urn:ogc:def:uom:UCUM:[nmi_i]',
    'nautical miles': 'urn:ogc:def:uom:UCUM:[nmi_i]',
    'yard': 'urn:ogc:def:uom:UCUM:[yd_i]',
    'yards': 'urn:ogc:def:uom:UCUM:[yd_i]',
    'yd': 'urn:ogc:def:uom:UCUM:[yd_i]',
    'urn:ogc:def:uom:OGC:1.0:metre': 'urn:ogc:def:uom:UCUM:deg',
    'urn:ogc:def:uom:OGC:1.0:degree': 'urn:ogc:def:uom:UCUM:m',
    'urn:ogc:def:uom:OGC:1.0:radian': 'urn:ogc:def:uom:UCUM:rad',
    'urn:ogc:def:uom:OGC:1.0:feet': 'urn:ogc:def:uom:UCUM:foot',
}


class OGC_CONFORMANCE_NS(str, Enum):
    OAPI_PROCESSES = 'http://www.opengis.net/spec/ogcapi-processes-1/1.0'
    OWS_WPS = 'http://www.opengis.net/wps/1.0.0'
