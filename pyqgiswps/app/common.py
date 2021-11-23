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

import pyqgiswps.ogc as ogc

class Metadata(*ogc.exports.Metadata):
    """
    ows:Metadata content model.

    :param title: Metadata title, human readable string
    :param href: fully qualified URL
    :param type_: fully qualified URL
    """

    def __init__(self, title, href=None, role=None, type_='simple'):
        self.title = title
        self.href = href
        self.role = role
        self.type = type_
       
