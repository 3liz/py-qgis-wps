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


from io import StringIO, FileIO, BytesIO
from enum import Enum

import os
import logging
from pyqgiswps.inout.literaltypes import (LITERAL_DATA_TYPES, convert,
                                          make_allowedvalues, is_anyvalue, 
                                          to_json_serializable)
from pyqgiswps import OWS, OGCUNIT, NAMESPACES
from pyqgiswps.validator.mode import MODE
from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.validator import get_validator
from pyqgiswps.validator.literalvalidator import (validate_anyvalue,
                                                  validate_allowed_values)
from pyqgiswps.exceptions import InvalidParameterValue
from pyqgiswps.inout.formats import Format

import base64

LOGGER = logging.getLogger('SRVLOG')


class SOURCE_TYPE(Enum):
    FILE = 1
    STREAM = 2
    DATA = 3


class IOHandler:
    """Basic IO class. Provides functions, to accept input data in file,
       and stream object and give them out in all three types

    """

    def __init__(self, mode=MODE.NONE):
        self.source_type = None
        self.source = None
        self._tempfile = None
        self._stream = None

        self.valid_mode = mode

    def _check_valid(self):
        """Validate this input usig given validator
        """
        validate = self.validator
        _valid = validate(self, self.valid_mode)
        if not _valid:
            raise InvalidParameterValue('Input data not valid using '
                                        'mode %s' % (self.valid_mode))

    def set_file(self, filename):
        """Set source as file name"""
        self.source_type = SOURCE_TYPE.FILE
        self.source = os.path.abspath(filename)
        self._check_valid()

    def get_file(self):
        """ Get file if source is file type
        """
        if self.source_type == SOURCE_TYPE.FILE:
            return self.source

    def set_stream(self, stream):
        """Set source as stream object"""
        self.source_type = SOURCE_TYPE.STREAM
        self.source = stream
        self._check_valid()

    def get_stream(self):
        """Get source as stream object"""
        if self.source_type == SOURCE_TYPE.FILE:
            if self._stream and not self._stream.closed:
                self._stream.close()
            self._stream = FileIO(self.source, mode='r', closefd=True)
            return self._stream
        elif self.source_type == SOURCE_TYPE.STREAM:
            return self.source
        elif self.source_type == SOURCE_TYPE.DATA:
            if isinstance(self.source, bytes):
                return BytesIO(self.source)
            elif isinstance(self.source, str):
                return StringIO(self.source)
            else:
                LOGGER.warn("Converting %s to stream", type(self.source))
                return StringIO(str(self.source))

    def set_data(self, data):
        """Set source as simple datatype e.g. string, number"""
        self.source_type = SOURCE_TYPE.DATA
        self.source = data
        self._check_valid()

    def set_base64(self, data):
        """Set data encoded in base64"""

        self.data = base64.b64decode(data)
        self._check_valid()

    def get_data(self):
        """Get source as simple data object"""
        if self.source_type == SOURCE_TYPE.FILE:
            with open(self.source, mode='r') as fh:
                content = fh.read()
            return content
        elif self.source_type == SOURCE_TYPE.STREAM:
            return self.source.read()
        elif self.source_type == SOURCE_TYPE.DATA:
            return self.source

    @property
    def validator(self):
        """Return the function suitable for validation
        This method should be overridden by class children

        :return: validating function
        """

        return emptyvalidator

    def get_base64(self):
        return base64.b64encode(self.data)

    # Properties
    file    = property(fget=get_file, fset=set_file)
    stream  = property(fget=get_stream, fset=set_stream)
    data    = property(fget=get_data, fset=set_data)
    base64  = property(fget=get_base64, fset=set_base64)


class SimpleHandler(IOHandler):
    """Data handler for Literal In- and Outputs

    >>> class Int_type:
    ...     @staticmethod
    ...     def convert(value): return int(value)
    >>>
    >>> class MyValidator:
    ...     @staticmethod
    ...     def validate(inpt): return 0 < inpt.data < 3
    >>>
    >>> inpt = SimpleHandler(data_type = Int_type)
    >>> inpt.validator = MyValidator
    >>>
    >>> inpt.data = 1
    >>> inpt.validator.validate(inpt)
    True
    >>> inpt.data = 5
    >>> inpt.validator.validate(inpt)
    False
    """

    def __init__(self, data_type=None, mode=MODE.NONE):
        IOHandler.__init__(self, mode=mode)
        self.data_type = data_type

    def get_data(self):
        return IOHandler.get_data(self)

    def set_data(self, data):
        """Set data value. input data are converted into target format
        """
        if self.data_type:
            data = convert(self.data_type, data)

        IOHandler.set_data(self, data)

    data = property(fget=get_data, fset=set_data)


class BasicIO:
    """Basic Input or Output class
    """
    def __init__(self, identifier, title=None, abstract=None):
        self.identifier = identifier
        self.title = title
        self.abstract = abstract


class BasicLiteral:
    """Basic literal input/output class
    """

    def __init__(self, data_type="integer", uoms=None):
        assert data_type in LITERAL_DATA_TYPES
        self.data_type = data_type
        # list of uoms
        self.uoms = []
        # current uom
        self._uom = None

        # add all uoms (upcasting to UOM)
        if uoms is not None:
            for uom in uoms:
                if not isinstance(uom, UOM):
                    uom = UOM(uom)
                self.uoms.append(uom)

        if self.uoms:
            # default/current uom
            self.uom = self.uoms[0]

    @property
    def uom(self):
        return self._uom

    @uom.setter
    def uom(self, uom):
        self._uom = uom


class BasicComplex:
    """Basic complex input/output class

    """

    def __init__(self, data_format=None, supported_formats=None):
        self._data_format = None
        self._supported_formats = None
        if supported_formats:
            self.supported_formats = supported_formats
        if self.supported_formats:
            # not an empty list, set the default/current format to the first
            self.data_format = supported_formats[0]

    def get_format(self, mime_type):
        """
        :param mime_type: given mimetype
        :return: Format
        """

        for frmt in self.supported_formats:
            if frmt.mime_type == mime_type:
                return frmt
        else:
            return None

    @property
    def validator(self):
        """Return the proper validator for given data_format
        """

        return self.data_format.validate

    @property
    def supported_formats(self):
        return self._supported_formats

    @supported_formats.setter
    def supported_formats(self, supported_formats):
        """Setter of supported formats
        """

        def set_format_validator(supported_format):
            if not supported_format.validate or \
               supported_format.validate == emptyvalidator:
                supported_format.validate =\
                    get_validator(supported_format.mime_type)
            return supported_format

        self._supported_formats = list(map(set_format_validator, supported_formats))

    @property
    def data_format(self):
        return self._data_format

    @data_format.setter
    def data_format(self, data_format):
        """self data_format setter
        """
        if self._is_supported(data_format):
            self._data_format = data_format
            if not data_format.validate or data_format.validate == emptyvalidator:
                data_format.validate = get_validator(data_format.mime_type)
        else:
            raise InvalidParameterValue("Requested format "
                                        "%s, %s, %s not supported" %
                                        (data_format.mime_type,
                                         data_format.encoding,
                                         data_format.schema),
                                        'mimeType')

    def _is_supported(self, data_format):
        """ Always return True if 
            no supported formats are defined
        """
        if self.supported_formats:
            # Catch all format is defined
            if self.supported_formats[0].same_as(Format.ANY):
                return True
            for frmt in self.supported_formats:
                if frmt.same_as(data_format):
                    return True
            return False

        return True


class BasicBoundingBox:
    """Basic BoundingBox input/output class
    """

    def __init__(self, crss=None, dimensions=2):
        self.crss = crss or ['epsg:4326']
        self.crs = self.crss[0]
        self.dimensions = dimensions
        self.ll = []
        self.ur = []


class LiteralInput(BasicIO, BasicLiteral, SimpleHandler):
    """LiteralInput input abstract class
    """

    def __init__(self, identifier, title=None, abstract=None,
                 data_type="integer", allowed_values=None,
                 uoms=None, mode=MODE.NONE):
        BasicIO.__init__(self, identifier, title, abstract)
        BasicLiteral.__init__(self, data_type, uoms)
        SimpleHandler.__init__(self, data_type, mode=mode)

        self.any_value = is_anyvalue(allowed_values)
        self.allowed_values = []
        if not self.any_value:
            self.allowed_values = make_allowedvalues(allowed_values)

    @property
    def validator(self):
        """Get validator for any value as well as allowed_values
        :rtype: function
        """

        if self.any_value:
            return validate_anyvalue
        else:
            return validate_allowed_values

    @property
    def json(self):
        """Get JSON representation of the input
        """
        return {
            'identifier': self.identifier,
            'title': self.title,
            'abstract': self.abstract,
            'type': 'literal',
            'data_type': self.data_type,
            'allowed_values': [value.json for value in self.allowed_values],
            'uoms': self.uoms,
            'uom': self.uom,
            'mode': self.valid_mode,
            'data': to_json_serializable(self.data)
        }


class LiteralOutput(BasicIO, BasicLiteral, SimpleHandler):
    """Basic LiteralOutput class
    """

    def __init__(self, identifier, title=None, abstract=None,
                 data_type=None, uoms=None, validate=None,
                 mode=MODE.NONE):
        BasicIO.__init__(self, identifier, title, abstract)
        BasicLiteral.__init__(self, data_type, uoms)
        SimpleHandler.__init__(self, data_type=data_type,
                               mode=mode)

    @property
    def validator(self):
        """Get validator for any value as well as allowed_values
        """

        return validate_anyvalue


class BBoxInput(BasicIO, BasicBoundingBox, IOHandler):
    """Basic Bounding box input abstract class
    """

    def __init__(self, identifier, title=None, abstract=None, crss=None,
                 dimensions=None, mode=MODE.NONE):
        BasicIO.__init__(self, identifier, title, abstract)
        BasicBoundingBox.__init__(self, crss, dimensions)
        IOHandler.__init__(self, mode=mode)

    @property
    def json(self):
        """Get JSON representation of the input. It returns following keys in
        the JSON object:

            * identifier
            * title
            * abstract
            * type
            * crs
            * bbox
            * dimensions
            * mode
        """
        return {
            'identifier': self.identifier,
            'title': self.title,
            'abstract': self.abstract,
            'type': 'bbox',
            'crs': self.crss,
            'bbox': (self.ll, self.ur),
            'dimensions': self.dimensions,
            'mode': self.valid_mode
        }


class BBoxOutput(BasicIO, BasicBoundingBox, SimpleHandler):
    """Basic BoundingBox output class
    """

    def __init__(self, identifier, title=None, abstract=None, crss=None,
                 dimensions=None, mode=MODE.NONE):
        BasicIO.__init__(self, identifier, title, abstract)
        BasicBoundingBox.__init__(self, crss, dimensions)
        SimpleHandler.__init__(self, mode=mode)



class ComplexInput(BasicIO, BasicComplex, IOHandler):
    """Complex input abstract class
    """

    def __init__(self, identifier, title=None, abstract=None,
                 data_format=None, supported_formats=None,
                 mode=MODE.NONE):
        BasicIO.__init__(self, identifier, title, abstract)
        IOHandler.__init__(self, mode=mode)
        BasicComplex.__init__(self, data_format, supported_formats)

    @property
    def json(self):
        """Get JSON representation of the input
        """
        return {
            'identifier': self.identifier,
            'title': self.title,
            'abstract': self.abstract,
            'type': 'complex',
            'data_format': self.data_format.json,
            'supported_formats': [frmt.json for frmt in self.supported_formats],
            'file': self.file,
            'mode': self.valid_mode
        }


class ComplexOutput(BasicIO, BasicComplex, IOHandler):
    """Complex output abstract class
    """

    def __init__(self, identifier, title=None, abstract=None,
                 data_format=None, supported_formats=None,
                 mode=MODE.NONE):
        BasicIO.__init__(self, identifier, title, abstract)
        IOHandler.__init__(self, mode=mode)
        BasicComplex.__init__(self, data_format, supported_formats)


class UOM:
    """
    :param uom: unit of measure
    """

    def __init__(self, uom=''):
        self.uom = uom

    def describe_xml(self):
        elem = OWS.UOM(
            self.uom
        )

        elem.attrib['{%s}reference' % NAMESPACES['ows']] = OGCUNIT[self.uom]

        return elem

    def execute_attribute(self):
        return OGCUNIT[self.uom]


