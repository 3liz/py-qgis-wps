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

from pyqgiswps.inout.literaltypes import (LITERAL_DATA_TYPES,
                                          convert,
                                          is_anyvalue,
                                          to_json_serializable)
from pyqgiswps.validator.mode import MODE
from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.validator import get_validator
from pyqgiswps.validator.literalvalidator import (validate_anyvalue,
                                                  validate_allowed_values)
from pyqgiswps.exceptions import InvalidParameterValue
from pyqgiswps.inout.formats import Format
from pyqgiswps.inout.uoms import UOM

import base64

from typing import List, Optional

LOGGER = logging.getLogger('SRVLOG')


class SOURCE_TYPE(Enum):
    FILE = 1
    STREAM = 2
    DATA = 3


class BasicHandler:
    """ Basic validator handler
    """

    def __init__(self, mode=MODE.NONE):
        self.valid_mode = mode

    def check_valid(self):
        """Validate this input usig given validator
        """
        validate = self.validator
        _valid = validate(self, self.valid_mode)
        if not _valid:
            raise InvalidParameterValue(
                f"Input data not valid using mode '{self.valid_mode}'"
            )

    @property
    def validator(self):
        """Return the function suitable for validation
        This method should be overridden by class children

        :return: validating function
        """

        return emptyvalidator


class IOHandler(BasicHandler):
    """Basic IO class. Provides functions, to accept input data in file,
       and stream object and give them out in all three types
    """

    def __init__(self, mode=MODE.NONE):
        BasicHandler.__init__(self, mode=mode)
        self.source_type = None
        self.source = None
        self._tempfile = None
        self._stream = None

    def set_file(self, filename):
        """Set source as file name"""
        self.source_type = SOURCE_TYPE.FILE
        self.source = os.path.abspath(filename)
        self.check_valid()

    def get_file(self):
        """ Get file if source is file type
        """
        if self.source_type == SOURCE_TYPE.FILE:
            return self.source

    def set_stream(self, stream):
        """Set source as stream object"""
        self.source_type = SOURCE_TYPE.STREAM
        self.source = stream
        self.check_valid()

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
        self.check_valid()

    def set_base64(self, data):
        """Set data encoded in base64"""

        self.data = base64.b64decode(data)
        self.check_valid()

    def get_data(self):
        """Get source as simple data object"""
        if self.source_type == SOURCE_TYPE.FILE:
            with open(self.source) as fh:
                content = fh.read()
            return content
        elif self.source_type == SOURCE_TYPE.STREAM:
            return self.source.read()
        elif self.source_type == SOURCE_TYPE.DATA:
            return self.source

    def get_base64(self):
        return base64.b64encode(self.data)

    # Properties
    file = property(fget=get_file, fset=set_file)
    stream = property(fget=get_stream, fset=set_stream)
    data = property(fget=get_data, fset=set_data)
    base64 = property(fget=get_base64, fset=set_base64)


class SimpleHandler(BasicHandler):
    """Data handler for Literal In- and Outputs
    """

    def __init__(self, data_type=None, mode=MODE.NONE):
        BasicHandler.__init__(self, mode=mode)
        self.data_type = data_type
        self._data = None

    def get_data(self):
        return self._data

    def set_data(self, data):
        """Set data value. input data are converted into target format
        """
        if self.data_type:
            data = convert(self.data_type, data)

        self._data = data
        self.check_valid()

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

    def __init__(self, data_type, uoms=None):
        assert data_type in LITERAL_DATA_TYPES, f"data type {data_type} no supported"
        self.data_type = data_type
        # current uom
        self.supported_uoms = uoms

    def get_supported_uom(self, code_or_ref: str) -> UOM:
        """ Get the uom code either from a code a from
            reference
        """
        for uom in self._supported_uoms:
            if uom.code == code_or_ref or uom.ref() == code_or_ref:
                return uom
        else:
            return None

    @property
    def supported_uoms(self):
        return self._supported_uoms

    @supported_uoms.setter
    def supported_uoms(self, uoms):
        """Setter of supported uoms
        """
        if uoms:
            self._supported_uoms = list(map(lambda uom: uom if isinstance(uom, UOM) else UOM(uom), uoms))
        else:
            self._supported_uoms = []
        self.set_default_uom()

    @property
    def uom(self):
        return self._uom

    @uom.setter
    def uom(self, uom: Optional[str]):
        """ Set and check uom
        """
        if uom is not None:
            if isinstance(uom, UOM):
                uom = uom.code
            uom = self.get_supported_uom(uom)
            if uom is None:
                raise InvalidParameterValue(
                    f"Requested unit '{uom}' not supported"
                )
        self._uom = uom

    def set_default_uom(self):
        if self._supported_uoms:
            self._uom = self._supported_uoms[0]
        else:
            self._uom = None


class BasicComplex:
    """Basic complex input/output class

    """

    def __init__(self, data_format=None, supported_formats: List[Format] = None):
        self._data_format = None
        self._supported_formats = []
        if supported_formats:
            self.supported_formats = supported_formats
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
        self._data = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if isinstance(value, list):
            self._data = [float(number) for number in value]
        elif isinstance(value, str):
            self._data = [float(number) for number in value.split(',')[:4]]
        else:
            self._data = None


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
        if not self.any_value:
            self.allowed_values = allowed_values
        else:
            self.allowed_values = None

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
            'allowed_values': self.allowed_values.json if self.allowed_values else None,
            'uoms': [uom.json for uom in self._supported_uoms],
            'uom': self._uom.json if self._uom is not None else None,
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


class BBoxInput(BasicIO, BasicBoundingBox):
    """Basic Bounding box input abstract class
    """

    def __init__(self, identifier, title=None, abstract=None, crss=None,
                 dimensions=None):
        BasicIO.__init__(self, identifier, title, abstract)
        BasicBoundingBox.__init__(self, crss, dimensions)

    @property
    def json(self):
        """ Get JSON representation of the input. It returns following keys in
        """
        return {
            'identifier': self.identifier,
            'title': self.title,
            'abstract': self.abstract,
            'type': 'bbox',
            'crss': self.crss,
            'bbox': self.data,
            'dimensions': self.dimensions,
        }


class BBoxOutput(BasicIO, BasicBoundingBox):
    """Basic BoundingBox output class
    """

    def __init__(self, identifier, title=None, abstract=None, crss=None,
                 dimensions=None):
        BasicIO.__init__(self, identifier, title, abstract)
        BasicBoundingBox.__init__(self, crss, dimensions)


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
            'data_format': self.data_format.json if self.data_format else None,
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
