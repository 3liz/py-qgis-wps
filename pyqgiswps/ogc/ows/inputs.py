#
# Copyright 2021 3liz
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

from .schema import E, OWS, WPS, NAMESPACES, XMLElement
from ..ogc import OGCUNIT, OGCTYPE
from ..traits import register_trait

from pyqgiswps.validator.base import to_json_serializable

@register_trait
class Metadata:

    def describe_xml(self) -> XMLElement:
        attrs = (('{http://www.w3.org/1999/xlink}title', self.title),
                 ('{http://www.w3.org/1999/xlink}href', self.href),
                 ('{http://www.w3.org/1999/xlink}type', self.type),)
        return OWS.Metadata({ns:val for ns,val in attrs if val is not None})
        

@register_trait
class Format:

    def describe_xml(self) -> XMLElement:
        """Return in describe process response element
        """

        doc = E.Format(
            E.MimeType(self.mime_type)
        )

        if self.encoding:
            doc.append(E.Encoding(self.encoding))

        if self.schema:
            doc.append(E.Schema(self.schema))

        return doc


@register_trait
class UOM:

    def describe_xml(self) -> XMLElement:
        elem = OWS.UOM(
            self.uom
        )
        elem.attrib['{%s}reference' % NAMESPACES['ows']] = OGCUNIT[self.uom]
        return elem


@register_trait
class BoundingBoxInput:

    def describe_xml(self) -> XMLElement:
        """
        :return: describeprocess response xml element
        """
        doc = E.Input(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )

        doc.attrib['minOccurs'] = str(self.min_occurs)
        doc.attrib['maxOccurs'] = str(self.max_occurs)

        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))

        for m in self.metadata:
            doc.append(m.describe_xml())

        bbox_data_doc = E.BoundingBoxData()
        doc.append(bbox_data_doc)

        default_doc = E.Default()
        default_doc.append(E.CRS(self.crss[0]))

        supported_doc = E.Supported()
        for c in self.crss:
            supported_doc.append(E.CRS(c))

        bbox_data_doc.append(default_doc)
        bbox_data_doc.append(supported_doc)

        return doc

    def execute_xml(self) -> XMLElement:
        """
        :return: execute response element
        """
        doc = WPS.Input(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )

        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))

        bbox_data_doc = OWS.BoundingBox()

        bbox_data_doc.attrib['crs'] = self.crs
        bbox_data_doc.attrib['dimensions'] = str(self.dimensions)

        bbox_data_doc.append(
            OWS.LowerCorner('{0[0]} {0[1]}'.format(self.data)))
        bbox_data_doc.append(
            OWS.UpperCorner('{0[2]} {0[3]}'.format(self.data)))

        doc.append(bbox_data_doc)

        return doc


@register_trait
class ComplexInput:

    def describe_xml(self) -> XMLElement:
        """Return Describe process element
        """

        doc = E.Input(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )

        doc.attrib['minOccurs'] = str(self.min_occurs)
        doc.attrib['maxOccurs'] = str(self.max_occurs)

        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))

        for m in self.metadata:
            doc.append(m.describe_xml())

        if self.supported_formats is not None:
            default_format_el = self.supported_formats[0].describe_xml()
            supported_format_elements = [f.describe_xml() for f in self.supported_formats]
            doc.append(
                E.ComplexData(
                    E.Default(default_format_el),
                    E.Supported(*supported_format_elements)
                )
            )

        return doc

    def execute_xml(self) -> XMLElement:
        """Render Execute response XML node

        :return: node
        :rtype: ElementMaker
        """
        node = None
        if self.as_reference:
            node = self._execute_xml_reference()
        else:
            node = self._execute_xml_data()

        doc = WPS.Input(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )
        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))
        doc.append(node)

        return doc

    def _execute_xml_reference(self) -> XMLElement:
        """Return Reference node
        """
        doc = WPS.Reference()
        doc.attrib['{http://www.w3.org/1999/xlink}href'] = self.url
        if self.data_format:
            if self.data_format.mime_type:
                doc.attrib['mimeType'] = self.data_format.mime_type
            if self.data_format.encoding:
                doc.attrib['encoding'] = self.data_format.encoding
            if self.data_format.schema:
                doc.attrib['schema'] = self.data_format.schema
        if self.method.upper() == 'POST' or self.method.upper() == 'GET':
            doc.attrib['method'] = self.method.upper()
        return doc

    def _execute_xml_data(self) -> XMLElement:
        """Return Data node
        """
        doc = WPS.Data()
        complex_doc = WPS.ComplexData(self.data)

        if self.data_format:
            if self.data_format.mime_type:
                complex_doc.attrib['mimeType'] = self.data_format.mime_type
            if self.data_format.encoding:
                complex_doc.attrib['encoding'] = self.data_format.encoding
            if self.data_format.schema:
                complex_doc.attrib['schema'] = self.data_format.schema
        doc.append(complex_doc)
        return doc


@register_trait
class LiteralInput:

    def describe_xml(self) -> XMLElement:
        """Return DescribeProcess Output element
        """
        doc = E.Input(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )

        doc.attrib['minOccurs'] = str(self.min_occurs)
        doc.attrib['maxOccurs'] = str(self.max_occurs)

        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))

        for m in self.metadata:
            doc.append(m.describe_xml())

        literal_data_doc = E.LiteralData()

        if self.data_type:
            data_type = OWS.DataType(self.data_type)
            data_type.attrib['{%s}reference' %
                             NAMESPACES['ows']] = OGCTYPE[self.data_type]
            literal_data_doc.append(data_type)

        if self.uoms:
            default_uom_element = self.uoms[0].describe_xml()
            supported_uom_elements = [u.describe_xml() for u in self.uoms]

            literal_data_doc.append(
                E.UOMs(
                    E.Default(default_uom_element),
                    E.Supported(*supported_uom_elements)
                )
            )

        doc.append(literal_data_doc)

        if self.any_value:
            literal_data_doc.append(OWS.AnyValue())
        else:
            literal_data_doc.append(self.allowed_values.describe_xml())

        if self.default is not None:
            literal_data_doc.append(E.DefaultValue(str(self.default)))

        return doc

    def execute_xml(self) -> XMLElement:
        """Render Execute response XML node

        :return: node
        :rtype: ElementMaker
        """
        node = self._execute_xml_data()

        doc = WPS.Input(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )
        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))
        doc.append(node)

        return doc

    def _execute_xml_data(self) -> XMLElement:
        """Return Data node
        """
        doc = WPS.Data()
        literal_doc = WPS.LiteralData(str(self.data))

        if self.data_type:
            literal_doc.attrib['dataType'] = self.data_type
        if self.uom:
            literal_doc.attrib['uom'] = self.uom
        doc.append(literal_doc)
        return doc


@register_trait
class AllowedValues:
    
    def _describe_range_xml(self) -> XMLElement:
        doc = OWS.Range()
        doc.set('{%s}rangeClosure' % NAMESPACES['ows'], self.range_closure)
        if self.minval is not None:
            doc.append(OWS.MinimumValue(str(to_json_serializable(self.minval))))
        if self.maxval is not None:
            doc.append(OWS.MaximumValue(str(to_json_serializable(self.maxval))))
        if self.spacing:
            doc.append(OWS.Spacing(str(self.spacing)))
        return doc

    def describe_xml(self) -> XMLElement:
        """ Return back Element for DescribeProcess response
        """
        doc = OWS.AllowedValues()
        if self.is_range:
            doc.append(self._describe_range_xml())
        else:
            for value in self.values:
                doc.append(OWS.Value(str(to_json_serializable(value))))
        return doc


