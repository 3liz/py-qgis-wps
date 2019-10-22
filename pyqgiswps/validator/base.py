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


from pyqgiswps.validator.mode import MODE


def emptyvalidator(data_input, mode):
    """Empty validator will return always false for security reason
    """

    if mode <= MODE.NONE:
        return True
    else:
        return False
