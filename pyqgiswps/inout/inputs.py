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


import os

import pyqgiswps.ogc as ogc

from pyqgiswps.config import confservice, get_size_bytes
from pyqgiswps.inout import basic
from copy import deepcopy
from pyqgiswps.validator.mode import MODE
from pyqgiswps.inout.literaltypes import AnyValue
from pyqgiswps.inout.httpclient import openurl

from pyqgiswps.exceptions import InvalidParameterValue

from typing import TypeVar

Json = TypeVar('Json')
Self = TypeVar('Self')

class BoundingBoxInput(basic.BBoxInput, *ogc.exports.BoundingBoxInput):

    """
    :param string identifier: The name of this input.
    :param string title: Human readable title
    :param string abstract: Longer text description
    :param crss: List of supported coordinate reference system (e.g. ['EPSG:4326'])
    :param int dimensions: 2 or 3
    :param int min_occurs: how many times this input occurs
    :param int max_occurs: how many times this input occurs
    :param metadata: List of metadata advertised by this process. They
                     should be :class:`pyqgiswps.app.common.Metadata` objects.
    """

    def __init__(self, identifier, title, crss, abstract='',
                 dimensions=2, metadata=[], min_occurs=1,
                 max_occurs=1,
                 default=None):
        basic.BBoxInput.__init__(self, identifier, title=title,
                                 abstract=abstract, crss=crss,
                                 dimensions=dimensions)

        self.metadata = metadata
        self.min_occurs = int(min_occurs)
        self.max_occurs = int(max_occurs)

    def clone(self):
        """Create copy of yourself
        """
        return deepcopy(self)

    def validate_input(self, inpt: Json) -> Self:
        """  Set parameter from json definition
        """
        self.data = inpt.get('data')
        if not self.data or len(self.data) < self.dimensions:
            raise InvalidParameterValue(f"Invalid bbox data for input '{self.identifier}')")

        self.crs = inpt.get('crs')
        if not self.crs:
            self.crs = self.crss[0]
        elif self.crs not in self.crss:
            raise InvalidParameterValue(f"Invalid crs for input '{self.identifier}')")

        self.dimensions = inpt.get('dimensions', self.dimensions)
        return self


class ComplexInput(basic.ComplexInput, *ogc.exports.ComplexInput):
    """
    Complex data input

    :param str identifier: The name of this input.
    :param str title: Title of the input
    :param pyqgiswps.inout.formats.Format supported_formats: List of supported formats
    :param pyqgiswps.inout.formats.Format data_format: default data format
    :param str abstract: Input abstract
    :param list metada: TODO
    :param int min_occurs: minimum occurence
    :param int max_occurs: maximum occurence
    :param pyqgiswps.validator.mode.MODE mode: validation mode (none to strict)
    """

    def __init__(self, identifier, title, supported_formats=None,
                 data_format=None, abstract='', metadata=[], min_occurs=1,
                 max_occurs=1, mode=MODE.NONE, default=None):
        """constructor"""

        basic.ComplexInput.__init__(self, identifier=identifier, title=title,
                                    abstract=abstract,
                                    supported_formats=supported_formats,
                                    mode=mode)
        self.metadata = metadata
        self.min_occurs = int(min_occurs)
        self.max_occurs = int(max_occurs)
        self.as_reference = False
        self.url  = None
        self.body = None
        self.method = ''
        self.max_size = int(0)

    def download_ref( self, filename: os.PathLike ) -> None: 
        """ Download reference/data as filename
        """
        if self.source_type is basic.SOURCE_TYPE.FILE:
            return
        
        if self.as_reference:
            openurl(self.url, filename=filename,  method=self.method, body=self.body)
        else:
            with open(filename,'wb') as fh:
                data = self.data
                if isinstance(data, str):
                    data = data.encode()
                fh.write(data)

        self.file = filename

    def calculate_max_input_size(self) -> int:
        """Calculates maximal size for input file based on configuration
        and units

        :return: maximum file size bytes
        """
        max_size = confservice.get('server','maxinputsize')
        self.max_size = get_size_bytes(max_size)
        return self.max_size

    def clone(self):
        """Create copy of yourself
        """
        return deepcopy(self)

    def validate_input(self, inpt: Json) -> Self:
        """  Set parameter from json definition
        """
        if self.supported_formats:
            frmt = self.supported_formats[0]
        else:
            frmt: None

        mimetype = inpt.get('mimeType')
        if mimetype:
            frmt = self.get_format(mimetype)
            if not frmt:
                raise InvalidParameterValue(
                    f"Invalid mimeType value '{mimetype}' for input {self.identifier}")

        self.data_format = frmt

        # get the referenced input otherwise get the value of the field
        href = inpt.get('href', None)
        if href:
            self.method = inpt.get('method', 'GET')
            self.url = href
            self.as_reference = True
            self.body = inpt.get('body')
        else:
            self.data = inpt.get('data')
        return self


class LiteralInput(basic.LiteralInput, *ogc.exports.LiteralInput):
    """
    :param str identifier: The name of this input.
    :param str title: Title of the input
    :param pyqgiswps.inout.literaltypes.LITERAL_DATA_TYPES data_type: data type
    :param str abstract: Input abstract
    :param list metadata: TODO
    :param str uoms: units
    :param int min_occurs: minimum occurence
    :param int max_occurs: maximum occurence
    :param pyqgiswps.validator.mode.MODE mode: validation mode (none to strict)
    :param pyqgiswps.inout.literaltypes.AnyValue allowed_values: or :py:class:`pyqgiswps.inout.literaltypes.AllowedValue` object
    :param metadata: List of metadata advertised by this process. They
                     should be :class:`pyqgiswps.app.common.Metadata` objects.
    """

    def __init__(self, identifier, title, data_type, abstract='',
                 metadata=[], uoms=None, default=None,
                 min_occurs=1, max_occurs=1,
                 mode=MODE.SIMPLE, allowed_values=AnyValue):
        """Constructor
        """

        basic.LiteralInput.__init__(self, identifier=identifier, title=title,
                                    abstract=abstract, data_type=data_type,
                                    uoms=uoms, mode=mode,
                                    allowed_values=allowed_values)
        self.metadata = metadata
        self.default = default
        self.min_occurs = int(min_occurs)
        self.max_occurs = int(max_occurs)

    def clone(self):
        """Create copy of yourself
        """
        return deepcopy(self)

    def validate_input(self, inpt: Json) -> Self:
        """  Set parameter from json definition
        """
        code = inpt.get('uom')
        if code:
            code = self.get_uom(code)
            if not code:
                raise InvalidParameterValue(
                    f"Invalid uom value '{code}' for input {self.identifier}")
        elif self.uoms:
            self.uom = self.uoms[0]

        self.data = inpt.get('data')
        return self

 
