#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Wrap qgis processing algorithms in WPS process
"""
import os
import logging
import mimetypes
import re

from os.path import normpath, basename
from pathlib import Path

from pyqgiswps.app.common import Metadata

from pyqgiswps.inout.formats import Format
from pyqgiswps.inout import (LiteralInput,
                             ComplexInput,
                             BoundingBoxInput,
                             LiteralOutput,
                             ComplexOutput,
                             BoundingBoxOutput)

from pyqgiswps.config import confservice

from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingParameterDefinition,
                       QgsProcessingOutputDefinition,
                       QgsProcessingOutputHtml,
                       QgsProcessingOutputFile,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterFile)

from ..processingcontext import ProcessingContext

from typing import Any, Union, Optional

WPSInput = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]

LOGGER = logging.getLogger('SRVLOG')

# ------------------------------------
# Processing parameters ->  WPS input
# ------------------------------------


def parse_input_definition(param: QgsProcessingParameterDefinition, kwargs) -> Union[LiteralInput, ComplexInput]:
    """ Convert processing input to File Input
    """
    typ = param.type()
    if typ == 'file':
        if param.behavior() == QgsProcessingParameterFile.Folder:
            kwargs['data_type'] = 'string'
            return LiteralInput(**kwargs)
        ext = param.extension()
        if ext:
            mime = mimetypes.types_map.get(ext)
            if mime is not None:
                kwargs['supported_formats'] = [Format(mime)]
            kwargs['metadata'].append(Metadata('processing:extension', param.extension()))
        return ComplexInput(**kwargs)
    elif typ == 'fileDestination':
        # By default, FileDestination parameters created with QGIS
        # model designer do not have a default value and a temporary
        # file is created on the fly when the model is executed.
        # Set a default value to reproduce this behavior.
        default_value = kwargs.get('default', '')
        if param.createByDefault() and not default_value:
            kwargs['default'] = param.name()

        extension = '.' + param.defaultFileExtension()
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:format', mimetypes.types_map.get(extension, '')))
        return LiteralInput(**kwargs)
    elif typ == 'folderDestination':
        kwargs['data_type'] = 'string'
        return LiteralInput(**kwargs)


# --------------------------------------
# WPS inputs ->  processing inputs data
# --------------------------------------

def get_processing_value(param: QgsProcessingParameterDefinition, inp: WPSInput,
                         context: ProcessingContext) -> Any:
    """ Return processing value from wps inputs

        Processes other inputs than layers
    """
    typ = param.type()

    if typ in ('fileDestination', 'folderDestination'):
        # Normalize path
        value = basename(normpath(inp[0].data))
        if value != inp[0].data:
            LOGGER.warning("Value for file or folder destination '%s' has been truncated from '%s' to '%s'",
                           param.name(), inp[0].data, value)
        if typ == 'fileDestination':
            value = Path(value).with_suffix('.' + param.defaultFileExtension()).as_posix()

    elif typ == 'file':
        # Handle file reference
        outputfile = (Path(context.workdir) / param.name()).with_suffix(param.extension())
        LOGGER.debug("Saving input data as %s", outputfile.as_posix())
        inp[0].download_ref(outputfile)
        value = outputfile.name
    else:
        value = None

    return value


# -------------------------------------------
# Processing output definition -> WPS output
# -------------------------------------------

def parse_output_definition(outdef: QgsProcessingOutputDefinition, kwargs,
                            alg: QgsProcessingAlgorithm = None) -> ComplexOutput:
    """ Parse file output definition

        QgsProcessingOutputDefinition metadata will be checked to get
        wps parameter settings:

            - 'wps:as_reference': boolean, True if the file will be sent as reference. If
            false, the file will included in the body of the response. Default is True.
    """
    as_reference = confservice.getboolean('server', 'outputfile_as_reference')
    if isinstance(outdef, QgsProcessingOutputHtml):
        mime = mimetypes.types_map.get('.html')
        return ComplexOutput(supported_formats=[Format(mime)], as_reference=as_reference, **kwargs)
    elif isinstance(outdef, QgsProcessingOutputFile):
        # Try to get a corresponding inputFileDefinition
        # See https://qgis.org/pyqgis/master/core/QgsProcessingParameterFileDestination.html
        supported_formats = []
        if alg:
            inputdef = alg.parameterDefinition(outdef.name())
            if isinstance(inputdef, QgsProcessingParameterFileDestination):
                default_mime = mimetypes.types_map.get("." + inputdef.defaultFileExtension())
                default_mime_idx = -1
                for filter_ in inputdef.fileFilter().split(";;"):
                    extension_regex = re.compile(r'.*([.][a-z]+)')
                    match = extension_regex.match(filter_)
                    if match:
                        mime = mimetypes.types_map.get(match.group(1))
                        if mime is not None:
                            if mime == default_mime:
                                default_mime_idx = len(supported_formats)

                            supported_formats.append(Format(mime))

                # The first format in the list is interpreted as the default one
                # Ensure that it corresponds to `default_mime`
                if default_mime_idx > 0:
                    supported_formats.insert(0, supported_formats.pop(Format(default_mime)))

                as_reference = inputdef.metadata().get('wps:as_reference', as_reference)
        if not supported_formats:
            # We cannot guess the mimetype of the outputfile
            # Set generic type
            supported_formats = [Format("application/octet-stream")]

        kwargs['supported_formats'] = supported_formats
        return ComplexOutput(as_reference=as_reference, **kwargs)


def to_output_file(file_name: str, out: ComplexOutput, context: ProcessingContext) -> ComplexOutput:
    """ Output file
    """
    if out.as_reference:
        # Use generic store uri, will be resolved when processing
        # outputs
        out.url = f"store:{file_name}"
    else:
        out.file = os.path.join(context.workdir, file_name)
    return out


def parse_response(value: Any, outdef: QgsProcessingOutputDefinition, out: WPSOutput,
                   context: ProcessingContext) -> Optional[WPSOutput]:
    """ Map processing output to WPS
    """
    if isinstance(outdef, QgsProcessingOutputHtml):
        out.output_format = mimetypes.types_map['.html']
        return to_output_file(value, out, context)
    elif isinstance(outdef, QgsProcessingOutputFile):
        _, sfx = os.path.splitext(value)
        mime = mimetypes.types_map.get(sfx.lower())
        LOGGER.debug("Return output file '%s' with mime type '%s'", value, mime)
        if mime is None:
            mime = "application/octet-stream"
        out.data_format = Format(mime)
        return to_output_file(value, out, context)
