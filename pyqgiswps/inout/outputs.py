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

import pyqgiswps.ogc as ogc

from pyqgiswps.inout import basic
from pyqgiswps.validator.mode import MODE


class BoundingBoxOutput(basic.BBoxInput, *ogc.exports.BoundingBoxOutput):
    """
    :param identifier: The name of this input.
    :param str title: Title of the input
    :param str abstract: Input abstract
    :param crss: List of supported coordinate reference system (e.g. ['EPSG:4326'])
    :param int dimensions: number of dimensions (2 or 3)
    :param int min_occurs: minimum occurence
    :param int max_occurs: maximum occurence
    :param pyqgiswps.validator.mode.MODE mode: validation mode (none to strict)
    :param metadata: List of metadata advertised by this process. They
                     should be :class:`pyqgiswps.app.common.Metadata` objects.
    """
    def __init__(self, identifier, title, crss, abstract='',
                 dimensions=2, metadata=[], min_occurs='1',
                 max_occurs='1', mode=MODE.NONE):
        basic.BBoxInput.__init__(self, identifier, title=title,
                                 abstract=abstract, crss=crss,
                                 dimensions=dimensions, mode=mode)

        self.metadata = metadata
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs


class ComplexOutput(basic.ComplexOutput, *ogc.exports.ComplexOutput):
    """
    :param identifier: The name of this output.
    :param title: Readable form of the output name.
    :param pyqgiswps.inout.formats.Format  supported_formats: List of supported
        formats. The first format in the list will be used as the default.
    :param str abstract: Description of the output
    :param pyqgiswps.validator.mode.MODE mode: validation mode (none to strict)
    :param metadata: List of metadata advertised by this process. They
                     should be :class:`pyqgiswps.app.common.Metadata` objects.
    """

    def __init__(self, identifier, title, supported_formats=None,
                 abstract='', metadata=None,
                 as_reference=False, mode=MODE.NONE):
        if metadata is None:
            metadata = []

        basic.ComplexOutput.__init__(self, identifier, title=title,
                                     abstract=abstract,
                                     supported_formats=supported_formats,
                                     mode=mode)
        self.metadata = metadata
        self.as_reference = as_reference
        self.url = None



class LiteralOutput(basic.LiteralOutput, *ogc.exports.LiteralOutput):
    """
    :param identifier: The name of this output.
    :param str title: Title of the input
    :param pyqgiswps.inout.literaltypes.LITERAL_DATA_TYPES data_type: data type
    :param str abstract: Input abstract
    :param str uoms: units
    :param pyqgiswps.validator.mode.MODE mode: validation mode (none to strict)
    :param metadata: List of metadata advertised by this process. They
                     should be :class:`pyqgiswps.app.common.Metadata` objects.
    """

    def __init__(self, identifier, title, data_type='string', abstract='',
                 metadata=[], uoms=[], mode=MODE.SIMPLE):
        if uoms is None:
            uoms = []
        basic.LiteralOutput.__init__(self, identifier, title=title,
                                     data_type=data_type, uoms=uoms, mode=mode)
        self.abstract = abstract
        self.metadata = metadata

