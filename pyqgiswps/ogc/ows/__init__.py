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
from .schema import E, WPS, OWS, NAMESPACES, XMLElement # noqa E402,F401

# Traits
from .process import Process       # noqa E402,F401
from .inputs import (Format,        # noqa E402,F401
                     UOM,           # noqa E402,F401
                     BoundingBoxInput,   # noqa E402,F401
                     ComplexInput,  # noqa E402,F401
                     LiteralInput,) # noqa E402,F401

from .outputs import (BoundingBoxOutput, # noqa E402,F401
                      ComplexOutput,     # noqa E402,F401
                      LiteralOutput,)    # noqa E402,F401

from .request import OWSRequest # noqa E402,F401

# Import stub variable
stub = None


