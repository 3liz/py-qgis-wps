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

LOGGER = logging.getLogger("QYWPS")


class Metadata(object):
    """
    ows:Metadata content model.

    :param title: Metadata title, human readable string
    :param href: fully qualified URL
    :param type_: fully qualified URL
    """

    def __init__(self, title, href=None, type_='simple'):
        self.title = title
        self.href = href
        self.type = type_

    def __iter__(self):
        yield '{http://www.w3.org/1999/xlink}title', self.title
        if self.href is not None:
            yield '{http://www.w3.org/1999/xlink}href', self.href
        yield '{http://www.w3.org/1999/xlink}type', self.type


