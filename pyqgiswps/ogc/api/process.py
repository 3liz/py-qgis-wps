#
# Copyright 2022 3liz
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

from pyqgiswps.protos import JsonValue

from ..traits import register_trait_for


@register_trait_for('WPSProcess')
class Process:
    """ Api traits for WPSProcess
    """

    def ogcapi_description(self) -> JsonValue:
        """ Json OAPI process description
        """
        return {
            'title': self.title,
            'description': self.abstract,
            'keywords': self.keywords,
            'metadata': [m.ogcapi_description() for m in self.metadata],
        }

    def ogcapi_process_summary(self) -> JsonValue:
        """ Json OAPI process summary
        """
        doc = self.ogcapi_description()
        doc.update(
            id=self.identifier,
            version=self.version,
            jobControlOptions=[
                'sync-execute',
                'async-execute',
                'dismiss',
            ],

            # outputTransmission=[
            #     'value',
            #     'reference',
            # ],
        )
        return doc

    def ogcapi_process(self) -> JsonValue:
        """ Json OAPI description for process
        """
        inputs = {i.identifier: i.ogcapi_input_description() for i in self.inputs}
        outputs = {i.identifier: i.ogcapi_output_description() for i in self.outputs}

        doc = self.ogcapi_process_summary()
        doc.update(
            inputs=inputs,
            outputs=outputs,
        )
        return doc
