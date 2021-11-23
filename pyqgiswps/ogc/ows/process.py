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

from .schema import E, OWS, WPS, XMLElement
from ..traits import register_trait_for


@register_trait_for('WPSProcess')
class Process: 
    """ OWS traits for wPSProcess
    """

    def capabilities_xml(self) -> XMLElement:
        """ Return capabilities XML
        """
        doc = WPS.Process(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )
        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))
        for m in self.metadata:
            doc.append(m.describe_xml())
        if self.profile:
            doc.append(OWS.Profile(self.profile))
        if self.version != 'None':
            doc.attrib['{http://www.opengis.net/wps/1.0.0}processVersion'] = self.version
        else:
            doc.attrib['{http://www.opengis.net/wps/1.0.0}processVersion'] = 'undefined'

        return doc


    def describe_xml(self) -> XMLElement:
        """ Return describe XML
        """
        input_elements  = [i.describe_xml() for i in self.inputs]
        output_elements = [i.describe_xml() for i in self.outputs]

        doc = E.ProcessDescription(
            OWS.Identifier(self.identifier),
            OWS.Title(self.title)
        )
        doc.attrib['{http://www.opengis.net/wps/1.0.0}processVersion'] = self.version
        doc.attrib['storeSupported'] = 'true'
        doc.attrib['statusSupported'] = 'true'

        if self.abstract:
            doc.append(OWS.Abstract(self.abstract))

        for m in self.metadata:
            doc.append(m.describe_xml())

        for p in self.profile:
            doc.append(WPS.Profile(p))

        if input_elements:
            doc.append(E.DataInputs(*input_elements))

        doc.append(E.ProcessOutputs(*output_elements))

        return doc


