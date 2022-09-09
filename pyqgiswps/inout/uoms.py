#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import pyqgiswps.ogc as ogc

class UOM(*ogc.exports.UOM):
    """
    :param uom: unit of measure
    """

    def __init__(self, code: str=None):
        self.code = code
   
    @property
    def ref(self) -> str:
        """ OGC urn definition """
        return ogc.OGCUNIT.get(self.code)

    @property 
    def json(self):
        return {
            'code': self.code,
            'ref': self.ref,
        }


