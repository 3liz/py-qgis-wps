#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ..ogc import OGCTYPE_SCHEMA
from ..traits import register_trait

from pyqgiswps.validator.allowed_value import RANGECLOSURETYPE
from pyqgiswps.validator.base import to_json_serializable

from typing import TypeVar
from enum import Enum

Json = TypeVar('Json')


class TypeHint(str, Enum):
    #
    # Not part of api spec.
    #
    # Used for helping client to deal
    # with schema
    #
    LiteralData = 'literalData'
    ComplexData = 'complexData'
    BoundingBoxData = 'boundingboxData'


class BasicInputDescription:

    def ogcapi_description(self) -> Json:
        doc = {
            'title': self.title,
            'keywords': [],
            'metadata': [ m.ogcapi_description() for m in self.metadata ],
            'minOccurs': self.min_occurs,
            'maxOccurs': self.max_occurs,
        }

        if self.abstract:
            doc.update(description=self.abstract)

        return doc



@register_trait
class Metadata:

    def ogcapi_description(self) -> Json:
        return {
            'title': self.title,
            'href': self.href,
            'role': self.role,
        }

@register_trait
class AllowedValues:
   
    def ogcapi_schema(self) -> Json:
        """Return describe OAPI json
        """
        doc = {}
        if self.is_range:
            # NOTE: this is Draft4 json schema validation
            if self.minval is not None:
                doc.update(minimum=to_json_serializable(self.minval))
                if self.range_closure in (RANGECLOSURETYPE.OPEN, RANGECLOSURETYPE.OPENCLOSED):
                    doc.update(exclusiveMinimum=True)
            if self.maxval is not None:
                doc.update(maximum=to_json_serializable(self.maxval))
                if self.range_closure in (RANGECLOSURETYPE.OPEN, RANGECLOSURETYPE.CLOSEDOPEN):
                    doc.update(exclusiveMaximum=True)

            if self.spacing:
                doc.update(multipleOf=self.spacing)
        else:
            doc.update(enum=[to_json_serializable(v) for v in self.values])

        return doc


@register_trait
class LiteralInput(BasicInputDescription):

    def ogcapi_input_description(self) -> Json:
        """ Return OAPI input description
        """
        doc = self.ogcapi_description()
        
        schema = OGCTYPE_SCHEMA[self.data_type]

        # Modify schema according to allowed values
        if self.allowed_values:
            schema.update(self.allowed_values.ogcapi_schema())
 
        if self.default is not None:
            schema.update(default=to_json_serializable(self.default))
        
        uoms = self.supported_uoms
        if uoms:
            schema.update(uom={
                'oneOf': [uom.ogcapi_description() for uom in uoms],
            })
        doc.update(schema=schema, typeHint=TypeHint.LiteralData.value)
        return doc


@register_trait
class Format:

    def ogcapi_description(self) -> Json:
        """ Return oapi format description
        """
        doc = { 'contentMediaType': self.mime_type }

        if self.encoding:
            doc.update(contentEncoding=self.encoding)

        if self.schema:
            doc.update(contentSchema=self.schema)

        return doc


@register_trait
class UOM:

    def ogcapi_description(self) -> Json:
        """ Return ogc api uom description (unspecified)
        """
        return {
            'uom': self.code,
            'reference': self.ref,
        }


@register_trait
class BoundingBoxInput(BasicInputDescription):

    def ogcapi_input_description(self) -> Json:
        """  Ogc api bbox input description
        """
        doc = self.ogcapi_description()
        
        if self.crss:
            crss = self.crss
        else:
            crss = ['http://www.opengis.net/def/crs/OGC/1.3/CRS84']

        num_items = self.dimensions * 2

        schema = {
            'type': 'object',
            'required': ['bbox'],
            'format': 'ogc-bbox',
            'dimensions': self.dimensions,
            'properties': {
                'bbox': {
                    'type': 'array',
                    'minItems': num_items, 
                    'maxItems': num_items,
                    'items': { 'type': 'number' },
                },
                'crs': {
                    'type': 'string',
                    'default': crss[0],
                    'enum': [crs for crs in crss],
                },
            },
        }
        
        doc.update(schema=schema, typeHint=TypeHint.BoundingBoxData.value)
        return doc


@register_trait
class ComplexInput(BasicInputDescription):

    def ogcapi_input_description(self) -> Json:
        """Return input json schema
        """
        doc = self.ogcapi_description()
        if self.supported_formats:
            if len(self.supported_formats) > 1:
                def schemas():
                    for fmt in self.supported_formats:
                        schema = fmt.ogcapi_description()
                        schema['type'] = 'string'
                        yield schema
                schema={'oneOf': list(schemas())}
            else:
                schema = self.supported_formats[0].ogcapi_description()
                schema['type'] = 'string'
        else:
            schema = { 'type': 'string' }
        doc.update(schema=schema, typeHint=TypeHint.ComplexData.value)
        return doc

