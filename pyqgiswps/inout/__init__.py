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
from typing import Union

from pyqgiswps.inout.basic import UOM  # noqa F401
from pyqgiswps.inout.formats import FORMATS, Format, get_format  # noqa F401
from pyqgiswps.inout.inputs import BoundingBoxInput, ComplexInput, LiteralInput
from pyqgiswps.inout.outputs import BoundingBoxOutput, ComplexOutput, LiteralOutput

WPSInput = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]
