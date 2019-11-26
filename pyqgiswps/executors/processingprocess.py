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
import traceback

from functools import partial

from os.path import normpath, basename
from urllib.parse import urlparse, urlencode, parse_qs

from functools import partial

from .processingio import (ProcessingTypeParseError,
                           parse_input_definition,
                           parse_output_definition,
                           input_to_processing,
                           processing_to_output)

from qgis.core import (QgsApplication,
                       QgsMapLayer,
                       QgsVectorLayer,
                       QgsWkbTypes,
                       QgsProcessingException, 
                       QgsProcessing,
                       QgsProcessingFeedback,
                       QgsProcessingContext,
                       QgsProcessingAlgorithm,
                       QgsProcessingUtils,
                       QgsFeatureRequest)

from pyqgiswps.app.Process import WPSProcess
from pyqgiswps.app.WPSResponse import WPSResponse
from pyqgiswps.app.WPSRequest  import WPSRequest
from pyqgiswps.exceptions import ProcessException

from processing.core.Processing import (Processing,
                                        ProcessingConfig,
                                        RenderingStyles)

from .processingcontext import ProcessingContext, MapContext

from pyqgiswps import config

LOGGER = logging.getLogger('SRVLOG')

from typing import Union, Mapping, TypeVar, Any

WPSInput  = TypeVar('WPSInput')
WPSOutput = TypeVar('WPSOutput')


class ProcessingAlgorithmNotFound(Exception):
    pass


def _find_algorithm( algid: str ) -> QgsProcessingAlgorithm:
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().algorithmById( algid )
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


def _create_algorithm( algid: str, **context ) -> QgsProcessingAlgorithm:
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().createAlgorithmById( algid, context )
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


_generic_version="1.0generic"


def handle_algorithm_results(alg: QgsProcessingAlgorithm, 
                             context: QgsProcessingContext, 
                             feedback: QgsProcessingFeedback, 
                             **kwargs) -> bool:
    """ Handle algorithms result layeri

        Insert result layers into destination project
    """
    wrongLayers = []
    for l, details in context.layersToLoadOnCompletion().items():
        if feedback.isCanceled():
            return False
        try:
            # Take as layer
            layer = QgsProcessingUtils.mapLayerFromString(l, context)
            if layer is not None:
                if not ProcessingConfig.getSetting(ProcessingConfig.USE_FILENAME_AS_LAYER_NAME):
                    layer.setName(details.name)
                # Set styles
                style = None
                if details.outputName:
                    # Try to load custom style from workdir
                    style = os.path.join(context.workdir, details.outputName + '.qml')
                    if not os.path.exists(style):
                        style = RenderingStyles.getStyle(alg.id(), details.outputName)
                    LOGGER.debug("Getting style for %s: %s <%s>", alg.id(), details.outputName, style)
                if style is None:
                    if layer.type() == QgsMapLayer.RasterLayer:
                        style = ProcessingConfig.getSetting(ProcessingConfig.RASTER_STYLE)
                    else:
                        if layer.geometryType() == QgsWkbTypes.PointGeometry:
                            style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_POINT_STYLE)
                        elif layer.geometryType() == QgsWkbTypes.LineGeometry:
                            style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_LINE_STYLE)
                        else:
                            style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_POLYGON_STYLE)
                if style:
                    LOGGER.debug("Adding style to layer %s (outputName %s)", details.name, details.outputName)
                    layer.loadNamedStyle(style)

                # Add layer to destination project
                LOGGER.debug("Adding Map layer '%s' (outputName %s) to Qgs Project", l, details.outputName )
                details.project.addMapLayer(context.temporaryLayerStore().takeMapLayer(layer))

                # Handle post processing
                if details.postProcessor():
                    details.postProcessor().postProcessLayer(layer, context, feedback)

            else:
                LOGGER.warning("No layer found found for %s", l)
        except Exception:
            LOGGER.error("Processing: Error loading result layer:\n{}".format(traceback.format_exc()))
            wrongLayers.append(str(l))

    if wrongLayers:
        msg = "The following layers were not correctly generated:"
        msg += "\n".join("%s" % lay for lay in wrongLayers)
        msg += "You can check the log messages to find more information about the execution of the algorithm"
        feedback.reportError(msg)

    return len(wrongLayers) == 0


class Feedback(QgsProcessingFeedback):
    """ Handle processing proggress messages

        This is a wrapper around WPS status
    """

    def __init__(self, response: WPSResponse, name: str, uuid_str: str ) -> None:
        super().__init__()
        self._response  = response
        self.name       = name
        self.uuid       = uuid_str[:8]

    def setProgress( self, progress: float ) -> None:
        """ We update the wps status
        """
        self._response.update_status(status_percentage=int(progress+0.5))

    def setProgressText( self, message: str ) -> None:
        self._response.update_status(message=message)

    def cancel(self) -> None:
        """ Notify that job is cancelled
        """
        LOGGER.warning("Processing:%s:%s cancel() called", self.name, self.uuid)
        super(Feedback, self).cancel()
        # TODO Call update status  when
        # https://projects.3liz.org/infra-v3/py-qgis-wps/issues/1 is fixed

    def reportError(self, error: str, fatalError=False ) -> None:
        (LOGGER.critical if fatalError else LOGGER.error)("%s:%s %s", self.name, self.uuid, error)

    def pushInfo(self, info: str) -> None:
        LOGGER.info("%s:%s %s",self.name, self.uuid, info)

    def pushDebugInfo(self, info: str) -> None:
        LOGGER.debug("%s:%s %s",self.name, self.uuid, info)


def handle_layer_outputs(results: Mapping[str,Any], context: QgsProcessingContext ) -> None:
    """ Replace output values by the layer names
    """
    for l, details in context.layersToLoadOnCompletion().items():
        if details.outputName in results:
            results[details.outputName] = details.name


def write_outputs( alg: QgsProcessingAlgorithm, results: Mapping[str,Any], outputs: Mapping[str, WPSOutput], 
                   output_uri: str=None,  context: QgsProcessingContext=None ) -> None:
    """ Set wps outputs and write project
    """
    for outdef in alg.outputDefinitions():
        out = outputs.get(outdef.name())
        if out:
            processing_to_output(results[outdef.name()], outdef, out, output_uri, context)

    if context is not None:
        context.write_result(context.workdir, alg.name())


class QgsProcess(WPSProcess):

    def __init__(self, algorithm: Union[QgsProcessingAlgorithm,str], context: MapContext=None) -> None:
        """ Initialize algorithm with a create context

            The create context may be used by the algorithm to provide
            contextualized inputs (i.e inputs that depends on the context source project or 
            associated data)

            WPSInputs and Outputs are parsed from the processing definition.
        """
        if context is not None:
            self._create_context = context.create_context
        else:
            self._create_context = {}

        alg = _find_algorithm( algorithm ) if isinstance(algorithm, str) else algorithm

        def _parse( parser, alg, defs ):
            for param in defs:
                try:
                    yield parser(param, alg, context=context)
                except ProcessingTypeParseError as e:
                    LOGGER.error("%s: unsupported param %s",alg.id(),e)

        # Create input/output
        inputs  = list(_parse(parse_input_definition, alg, alg.parameterDefinitions()))
        outputs = list(_parse(parse_output_definition, alg, alg.outputDefinitions()))

        version = alg.version() if hasattr(alg,'versions') else _generic_version

        handler = partial(QgsProcess._handler, create_context=self._create_context)

        super().__init__(handler,
                identifier = alg.id(),
                version    = version,
                title      = alg.displayName(),
                # XXX Scripts do not provide description string
                abstract   = alg.shortDescription() or alg.shortHelpString(),
                inputs     = inputs,
                outputs    = outputs)

    @staticmethod
    def createInstance( ident: str, map_uri=None, **context ) -> 'QgsProcess':
        """ Create a contextualized instance
        """
        LOGGER.debug("Creating contextualized process for %s: %s", ident, context)
        mapcontext = MapContext(map_uri=map_uri, **context)
        alg = _create_algorithm(ident, **mapcontext.create_context)
        return QgsProcess(alg, mapcontext)

    @staticmethod
    def _handler( request: WPSRequest, response: WPSResponse, create_context: Mapping[str,Any] ) -> WPSResponse:
        """  WPS process handler
        """
        uuid_str = str(response.uuid)
        LOGGER.info("Starting task %s:%s", uuid_str[:8], request.identifier)

        alg = QgsApplication.processingRegistry().createAlgorithmById(request.identifier, create_context)

        workdir  = response.process.workdir
        context  = ProcessingContext(workdir, map_uri=request.map_uri)
        feedback = Feedback(response, alg.id(), uuid_str=uuid_str)

        context.setFeedback(feedback)
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometrySkipInvalid)

        # Convert parameters from WPS inputs
        parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in request.inputs.items() )

        try:
            # XXX Warning, a new instance of the algorithm without create_context will be created at the 'run' call
            # see https://qgis.org/api/qgsprocessingalgorithm_8cpp_source.html#l00414
            # We can deal with that because we will have a QgsProcessingContext and we should not 
            # rely on the create_context at this time.
            results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=handle_algorithm_results,
                                              feedback=feedback, context=context)
        except QgsProcessingException as e:
            raise ProcessException("%s" % e)

        LOGGER.info("Task finished %s:%s", request.identifier, uuid_str )

        handle_layer_outputs(results, context)

        # Get WMS output uri
        output_uri = config.get_config('server')['wms_response_uri'].format(
                            host_url=request.host_url,
                            uuid=response.uuid,
                            name=alg.name())

        context.response = response
        write_outputs( alg, results, response.outputs, output_uri, context)

        return response

    def clean(self) -> None:
        """ Override default

            We use the workdir as our final output dir
            The cleanup policy is driven by the request expiration time
        """
        pass

