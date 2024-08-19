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

# Schema
from .inputs import (  # noqa: F401
    UOM,
    BoundingBoxInput,
    ComplexInput,
    Format,
    LiteralInput,
)
from .outputs import (  # noqa: F401
    BoundingBoxOutput,
    ComplexOutput,
    LiteralOutput,
)

# Traits
from .process import Process  # noqa: F401
from .schema import NAMESPACES, OWS, WPS, E, XMLElement  # noqa: F401

# Import stub variable
stub = None
