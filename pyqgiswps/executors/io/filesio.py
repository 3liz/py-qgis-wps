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

from typing import Any,Union,Optional

WPSInput  = Union[LiteralInput, ComplexInput, BoundingBoxInput]
WPSOutput = Union[LiteralOutput, ComplexOutput, BoundingBoxOutput]

LOGGER = logging.getLogger('SRVLOG')

# ------------------------------------
# Processing parameters ->  WPS input
# ------------------------------------

def parse_input_definition( param: QgsProcessingParameterDefinition, kwargs) -> Union[LiteralInput,ComplexInput]:
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
            kwargs['metadata'].append(Metadata('processing:extension',param.extension()))
        return ComplexInput(**kwargs)
    elif typ == 'fileDestination':
        extension = '.'+param.defaultFileExtension()
        kwargs['data_type'] = 'string'
        kwargs['metadata'].append(Metadata('processing:format', mimetypes.types_map.get(extension,'')))
        return LiteralInput(**kwargs)
    elif typ == 'folderDestination':
        kwargs['data_type'] = 'string'
        return LiteralInput(**kwargs)


# --------------------------------------
# WPS inputs ->  processing inputs data
# --------------------------------------

def get_processing_value( param: QgsProcessingParameterDefinition, inp: WPSInput,
                          context: ProcessingContext) -> Any:
    """ Return processing value from wps inputs

        Processes other inputs than layers
    """
    typ = param.type()

    if typ in ('fileDestination','folderDestination'):
        # Normalize path
        value = basename(normpath(inp[0].data))
        if value != inp[0].data:
            LOGGER.warning("Value for file or folder destination '%s' has been truncated from '%s' to '%s'",
                           param.name(), inp[0].data, value )
        if typ == 'fileDestination':
            value = Path(value).with_suffix('.'+param.defaultFileExtension()).as_posix()
            
    elif typ == 'file':
        # Handle file reference
        outputfile = (Path(context.workdir)/param.name()).with_suffix(param.extension())
        LOGGER.debug("Saving input data as %s", outputfile.as_posix())
        inp[0].download_ref(outputfile)
        value = outputfile.name
    else:
        value = None

    return value


# -------------------------------------------
# Processing output definition -> WPS output
# -------------------------------------------

def parse_output_definition( outdef: QgsProcessingOutputDefinition, kwargs, 
                             alg: QgsProcessingAlgorithm=None ) -> ComplexOutput:
    """ Parse file output definition

        QgsProcessingOutputDefinition metadata will be checked to get 
        wps parameter settings:

            - 'wps:as_reference': boolean, True if the file will be sent as reference. If
            false, the file will included in the body of the response. Default is True.
    """
    as_reference = confservice.getboolean('server','outputfile_as_reference')
    if isinstance(outdef, QgsProcessingOutputHtml):
        mime = mimetypes.types_map.get('.html')
        return ComplexOutput(supported_formats=[Format(mime)], as_reference=as_reference, **kwargs)
    elif isinstance(outdef, QgsProcessingOutputFile):
        # Try to get a corresponding inputFileDefinition
        # See https://qgis.org/pyqgis/master/core/QgsProcessingParameterFileDestination.html
        mime = None
        if alg:
            inputdef = alg.parameterDefinition(outdef.name())
            if isinstance(inputdef, QgsProcessingParameterFileDestination):
                mime = mimetypes.types_map.get("."+inputdef.defaultFileExtension())
                as_reference = inputdef.metadata().get('wps:as_reference',as_reference)
        if mime is None:
            # We cannot guess the mimetype of the outputfile
            # Set generic type
            mime = "application/octet-stream"
    
        kwargs['supported_formats'] = [Format(mime)]
        return ComplexOutput(as_reference=as_reference, **kwargs)


def to_output_file( file_name: str, out: ComplexOutput, context: ProcessingContext ) -> ComplexOutput:
    """ Output file
    """
    if out.as_reference:
        # Use generic store uri, will be resolved when processing
        # outputs
        out.url = f"store:{file_name}"
    else:
        out.file = os.path.join(context.workdir, file_name)
    return out


def parse_response( value: Any, outdef: QgsProcessingOutputDefinition, out: WPSOutput, 
                    context: ProcessingContext ) -> Optional[WPSOutput]:
    """ Map processing output to WPS
    """
    if isinstance(outdef, QgsProcessingOutputHtml):
        out.output_format = mimetypes.types_map['.html']
        return to_output_file( value, out, context )
    elif isinstance(outdef, QgsProcessingOutputFile):
        _, sfx = os.path.splitext(value)
        mime = mimetypes.types_map.get(sfx.lower())
        LOGGER.debug("Return output file '%s' with mime type '%s'", value, mime)
        if mime is None:
            mime = "application/octet-stream"
        out.data_format = Format(mime)
        return to_output_file( value, out, context)

