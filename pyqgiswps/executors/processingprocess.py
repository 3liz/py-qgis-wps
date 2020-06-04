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
                           parse_input_definitions,
                           parse_output_definitions,
                           input_to_processing,
                           processing_to_output)

from qgis.core import (Qgis,
                       QgsApplication,
                       QgsMapLayer,
                       QgsVectorLayer,
                       QgsWkbTypes,
                       QgsProcessingException, 
                       QgsProcessing,
                       QgsProcessingFeedback,
                       QgsProcessingContext,
                       QgsProcessingAlgorithm,
                       QgsProcessingModelAlgorithm,
                       QgsProcessingUtils,
                       QgsFeatureRequest,
                       QgsExpressionContext,
                       QgsExpressionContextScope,
                       QgsProcessingOutputLayerDefinition)

from pyqgiswps.app.Process import WPSProcess
from pyqgiswps.app.WPSResponse import WPSResponse
from pyqgiswps.app.WPSRequest  import WPSRequest
from pyqgiswps.exceptions import ProcessException
from pyqgiswps.config import confservice

from pyqgiswps.utils.filecache import get_valid_filename

from processing.core.Processing import (Processing,
                                        ProcessingConfig,
                                        RenderingStyles)

from .processingcontext import ProcessingContext, MapContext

from .io import layersio

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

#---------------------------------
# Post processing
#---------------------------------

def _set_output_layer_style( layerName: str, layer: QgsMapLayer, alg: QgsProcessingAlgorithm, 
                             details: QgsProcessingContext.LayerDetails,
                             context: QgsProcessingContext,
                             parameters) -> None:
    """ Set layer style 

        Original code is from python/plugins/processing/gui/Postprocessing.py
    """

    '''If running a model, the execution will arrive here when an algorithm that is part of
    that model is executed. We check if its output is a final output of the model, and
    adapt the output name accordingly'''
    outputName = details.outputName
    if parameters:
        expcontext = QgsExpressionContext()
        scope = QgsExpressionContextScope()
        expcontext.appendScope(scope)
        for out in alg.outputDefinitions():
            if out.name() not in parameters:
                continue
            outValue = parameters[out.name()]
            if hasattr(outValue, "sink"):
                outValue = outValue.sink.valueAsString(expcontext)[0]
            else:
                outValue = str(outValue)
            if outValue == layerName:
                outputName = out.name()
                break


    style = None
    if outputName:
        # If a style with the same name as the outputName exists
        # in workdir then use it
        style = os.path.join(context.workdir, outputName + '.qml')
        if not os.path.exists(style):
            # Fallback to defined rendering styles
            style = RenderingStyles.getStyle(alg.id(), outputName)
        LOGGER.debug("Getting style for %s: %s <%s>", alg.id(), outputName, style)

    # Get defaults styles
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
        LOGGER.debug("Adding style '%s' to layer %s (outputName %s)", style, details.name, outputName)
        layer.loadNamedStyle(style)


def handle_layer_outputs(alg: QgsProcessingAlgorithm, 
                         context: QgsProcessingContext, 
                         parameters, results) -> bool:
    """ Handle algorithms result layers

        Insert result layers into destination project
    """
    # Transfer layers ownership to destination project
    wrongLayers = []
    for l, details in context.layersToLoadOnCompletion().items():
        try:
            # Take as layer
            layer = QgsProcessingUtils.mapLayerFromString(l, context, typeHint=details.layerTypeHint)
            if layer is not None:
                # Fix layer name
                # If details name is empty it well be set to the file name 
                # see https://qgis.org/api/qgsprocessingcontext_8cpp_source.html#l00128
                # XXX Make sure that Processing/Configuration/PREFER_FILENAME_AS_LAYER_NAME 
                # setting is set to false (see processfactory.py:129)
                details.setOutputLayerName(layer)
                LOGGER.debug("Layer name set to %s <details name was: %s>", layer.name(), details.name)
                # If project is not defined, set the default destination
                # project
                if not details.project and hasattr(context, 'destination_project'):
                    details.project = context.destination_project

                # Seek style for layer
                _set_output_layer_style(l, layer, alg, details, context, parameters)            

                # Add layer to destination project
                if details.project:
                    LOGGER.debug("Adding Map layer '%s' (outputName %s) to Qgs Project", l, details.outputName )
                    details.project.addMapLayer(context.temporaryLayerStore().takeMapLayer(layer))

                # Handle post processing
                if details.postProcessor():
                    details.postProcessor().postProcessLayer(layer, context, feedback)
            else:
                LOGGER.warning("No layer found for %s", l)
        except Exception:
            LOGGER.error("Processing: Error loading result layer:\n{}".format(traceback.format_exc()))
            wrongLayers.append(str(l))

    if wrongLayers:
        msg = "The following layers were not correctly generated:"
        msg += "\n".join("%s" % lay for lay in wrongLayers)
        msg += "You can check the log messages to find more information about the execution of the algorithm"
        LOGGER.error(msg)

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


def onFinishHandler(alg: QgsProcessingAlgorithm,
                    context: QgsProcessingContext,
                    feedback: QgsProcessingFeedback,
                    parameters = {},
                    **kwargs):
    """ This is a dummy function 
        Results will be handler after run()
    """
    if feedback.isCanceled():
        return False

    return True


def run_algorithm( alg: QgsProcessingAlgorithm, parameters, 
                   feedback: QgsProcessingFeedback,
                   context: QgsProcessingContext,
                   outputs: Mapping[str, WPSOutput],
                   output_uri:str):

    # XXX Fix destination names for models
    # Collect destination names for destination parameters for restoring
    # them later
    destinations = { p:v.destinationName for p,v in parameters.items() if isinstance(v,QgsProcessingOutputLayerDefinition) }

    # XXX Warning, a new instance of the algorithm without create_context will be created at the 'run' call
    # see https://qgis.org/api/qgsprocessingalgorithm_8cpp_source.html#l00434
    # We can deal with that because we will have a QgsProcessingContext and we should not 
    # rely on the create_context at this time.
    results = Processing.runAlgorithm(alg, parameters=parameters, onFinish=onFinishHandler,
                                      feedback=feedback, context=context)

    for outdef in alg.outputDefinitions():
        outputName = outdef.name()
        out = outputs.get(outputName)
        if out:
            value = results[outputName]
            #
            # Replace the Load On Completion Details name by the original input so
            # that we ensure that layer names will be correct - This is needed
            # for models as they enforce destination name to the output name
            #
            if outputName in destinations and context.willLoadLayerOnCompletion( value ):
                context.layerToLoadOnCompletionDetails( value ).name = destinations[outputName]
            processing_to_output(value, outdef, out, output_uri, context)
    #
    # Handle results, we do not use onFinish callback because
    # we want to deal with the results
    #
    handle_layer_outputs(alg, context, parameters, results)

    return results


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

        # Create input/output
        inputs  = list(parse_input_definitions( alg, context=context ))
        outputs = list(parse_output_definitions( alg, context=context ))

        version = alg.version() if hasattr(alg,'version') else _generic_version

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
        mapcontext = MapContext(map_uri=map_uri, **context)
        LOGGER.debug("Creating contextualized process for %s: %s", ident, mapcontext.create_context)
        alg = _create_algorithm(ident, **mapcontext.create_context)
        return QgsProcess(alg, mapcontext)

    @staticmethod
    def _handler( request: WPSRequest, response: WPSResponse, create_context: Mapping[str,Any] ) -> WPSResponse:
        """  WPS process handler
        """
        uuid_str = str(response.uuid)
        LOGGER.info("Starting task %s:%s", uuid_str[:8], request.identifier)

        alg = QgsApplication.processingRegistry().createAlgorithmById(request.identifier, create_context)

        # Get WMS output uri
        destination = get_valid_filename(alg.id())

        output_uri = confservice.get('server','wms_response_uri').format(
                            host_url=request.host_url,
                            uuid=response.uuid,
                            name=destination)

        workdir  = response.process.workdir
        context  = ProcessingContext(workdir, map_uri=request.map_uri)
        feedback = Feedback(response, alg.id(), uuid_str=uuid_str)

        context.setFeedback(feedback)
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometrySkipInvalid)

        # Convert parameters from WPS inputs
        parameters = dict( input_to_processing(ident, inp, alg, context) for ident,inp in request.inputs.items() )

        context.store_url = response.store_url

        try:
            results = run_algorithm(alg, parameters, feedback=feedback, context=context, 
                                    outputs=response.outputs,
                                    output_uri=output_uri)
        except QgsProcessingException as e:
            raise ProcessException("%s" % e)

        ok = context.write_result(context.workdir, destination)
        if not ok:
            raise ProcessException("Failed to write %s" % destination)

        LOGGER.info("Task finished %s:%s", request.identifier, uuid_str )

        return response

    def clean(self) -> None:
        """ Override default

            We use the workdir as our final output dir
            The cleanup policy is driven by the request expiration time
        """
        pass

