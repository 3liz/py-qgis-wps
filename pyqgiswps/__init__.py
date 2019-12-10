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

import os

from lxml.builder import ElementMaker
from .version import __version__ 

NAMESPACES = {
    'xlink': "http://www.w3.org/1999/xlink",
    'wps': "http://www.opengis.net/wps/1.0.0",
    'ows': "http://www.opengis.net/ows/1.1",
    'gml': "http://www.opengis.net/gml",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance"
}

E = ElementMaker()
WPS = ElementMaker(namespace=NAMESPACES['wps'], nsmap=NAMESPACES)
OWS = ElementMaker(namespace=NAMESPACES['ows'], nsmap=NAMESPACES)

OGCTYPE = {
    'measure': 'urn:ogc:def:dataType:OGC:1.1:measure',
    'length': 'urn:ogc:def:dataType:OGC:1.1:length',
    'scale': 'urn:ogc:def:dataType:OGC:1.1:scale',
    'time': 'urn:ogc:def:dataType:OGC:1.1:time',
    'gridLength': 'urn:ogc:def:dataType:OGC:1.1:gridLength',
    'angle': 'urn:ogc:def:dataType:OGC:1.1:angle',
    'lengthOrAngle': 'urn:ogc:def:dataType:OGC:1.1:lengthOrAngle',
    'string': 'urn:ogc:def:dataType:OGC:1.1:string',
    'positiveInteger': 'urn:ogc:def:dataType:OGC:1.1:positiveInteger',
    'nonNegativeInteger': 'urn:ogc:def:dataType:OGC:1.1:nonNegativeInteger',
    'boolean': 'urn:ogc:def:dataType:OGC:1.1:boolean',
    'measureList': 'urn:ogc:def:dataType:OGC:1.1:measureList',
    'lengthList': 'urn:ogc:def:dataType:OGC:1.1:lengthList',
    'scaleList': 'urn:ogc:def:dataType:OGC:1.1:scaleList',
    'angleList': 'urn:ogc:def:dataType:OGC:1.1:angleList',
    'timeList': 'urn:ogc:def:dataType:OGC:1.1:timeList',
    'gridLengthList': 'urn:ogc:def:dataType:OGC:1.1:gridLengthList',
    'integerList': 'urn:ogc:def:dataType:OGC:1.1:integerList',
    'positiveIntegerList': 'urn:ogc:def:dataType:OGC:1.1:positiveIntegerList',
    'anyURI': 'urn:ogc:def:dataType:OGC:1.1:anyURI',
    'integer': 'urn:ogc:def:dataType:OGC:1.1:integer',
    'float': 'urn:ogc:def:dataType:OGC:1.1:float'
}

OGCUNIT = {
    'degree': 'urn:ogc:def:uom:OGC:1.0:degree',
    'metre': 'urn:ogc:def:uom:OGC:1.0:metre',
    'unity': 'urn:ogc:def:uom:OGC:1.0:unity'
}

from pyqgiswps.app import WPSProcess, Service, WPSRequest
from pyqgiswps.app.WPSRequest import get_inputs_from_xml, get_output_from_xml
from pyqgiswps.inout.inputs import LiteralInput, ComplexInput, BoundingBoxInput
from pyqgiswps.inout.outputs import LiteralOutput, ComplexOutput, BoundingBoxOutput
from pyqgiswps.inout.formats import Format, FORMATS, get_format
from pyqgiswps.inout import UOM

if __name__ == "__main__":
    pass
