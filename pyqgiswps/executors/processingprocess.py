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
import logging
import os
import traceback

from functools import partial
from pathlib import Path
from typing import (
    Any,
    Mapping,
    Optional,
    Union,
)

from processing.core.Processing import ProcessingConfig, RenderingStyles

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFeatureRequest,
    QgsMapLayer,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputLayerDefinition,
    QgsProcessingParameterDefinition,
    QgsProcessingUtils,
    QgsWkbTypes,
)

from pyqgiswps.app.process import WPSProcess
from pyqgiswps.app.request import WPSRequest, WPSResponse
from pyqgiswps.config import confservice
from pyqgiswps.exceptions import ProcessException
from pyqgiswps.utils.filecache import get_valid_filename

from .processingcontext import MapContext, ProcessingContext
from .processingio import (
    WPSOutput,
    input_to_processing,
    parse_input_definitions,
    parse_output_definitions,
    processing_to_output,
)

LOGGER = logging.getLogger('SRVLOG')


class ProcessingAlgorithmNotFound(Exception):
    pass


def _find_algorithm(algid: str) -> QgsProcessingAlgorithm:
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().algorithmById(algid)
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


def _create_algorithm(algid: str, mapcontext: MapContext) -> QgsProcessingAlgorithm:
    """ Fetch algoritm from its id
    """
    alg = QgsApplication.processingRegistry().createAlgorithmById(algid, mapcontext.create_context)
    if not alg:
        raise ProcessingAlgorithmNotFound(algid)
    return alg


_generic_version = "1.0generic"

# ---------------------------------
# Post processing
# ---------------------------------


def _set_output_layer_style(
    layerName: str,
    layer: QgsMapLayer,
    alg: QgsProcessingAlgorithm,
    details: QgsProcessingContext.LayerDetails,
    context: QgsProcessingContext,
    parameters: Mapping[str, QgsProcessingParameterDefinition],
):
    """ Set layer style

        Original code is from python/plugins/processing/gui/Postprocessing.py
    """
    outputName = details.outputName

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
        # Load default styles
        layer.loadDefaultStyle()

        if layer.type() == QgsMapLayer.RasterLayer:
            style = ProcessingConfig.getSetting(ProcessingConfig.RASTER_STYLE)
        else:
            match layer.geometryType():
                case QgsWkbTypes.PointGeometry:
                    style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_POINT_STYLE)
                case QgsWkbTypes.LineGeometry:
                    style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_LINE_STYLE)
                case _:
                    style = ProcessingConfig.getSetting(ProcessingConfig.VECTOR_POLYGON_STYLE)
    if style:
        LOGGER.debug("Adding style '%s' to layer %s (outputName %s)", style, details.name, outputName)
        layer.loadNamedStyle(style)


def handle_layer_outputs(
    alg: QgsProcessingAlgorithm,
    context: QgsProcessingContext,
    parameters: Mapping[str, QgsProcessingParameterDefinition],
    results: Mapping[str, Any],
    uuid: str,
    feedback: Optional[QgsProcessingFeedback] = None,
) -> bool:
    """ Handle algorithms result layers

        Insert result layers into destination project
    """
    # Transfer layers ownership to destination project
    wrongLayers = []
    host_url = confservice.get('wps.request', 'host_url', '').strip("/")
    for lyrname, details in context.layersToLoadOnCompletion().items():
        try:
            # Take as layer
            layer = QgsProcessingUtils.mapLayerFromString(
                lyrname,
                context,
                typeHint=details.layerTypeHint,
            )

            if layer is not None:
                # Fix layer name
                # If details name is empty it well be set to the file name
                # see https://qgis.org/api/qgsprocessingcontext_8cpp_source.html#l00128
                # XXX Make sure that Processing/Configuration/PREFER_FILENAME_AS_LAYER_NAME
                # setting is set to false (see processfactory.py:129)
                details.setOutputLayerName(layer)
                LOGGER.debug(
                    "Layer name set to %s <details name was: %s>",
                    layer.name(),
                    details.name,
                )
                # If project is not defined, set the default destination
                # project
                if not details.project and hasattr(context, 'destination_project'):
                    details.project = context.destination_project

                # Seek style for layer
                _set_output_layer_style(lyrname, layer, alg, details, context, parameters)

                # Advertise the associated file of the layer with as DataUrl
                data_url = "/".join([host_url, "jobs", uuid, "files", str(Path(lyrname))])
                if Qgis.QGIS_VERSION_INT >= 33800:
                    server_properties = layer.serverProperties()
                    server_properties.setDataUrl(data_url)
                    server_properties.setDataUrlFormat("text/plain")
                else:
                    layer.setDataUrl(data_url)
                    layer.setDataUrlFormat("text/plain")

                # Add layer to destination project
                if details.project:
                    LOGGER.debug(
                        "Adding Map layer '%s' (outputName %s) to Qgs Project",
                        lyrname,
                        details.outputName,
                    )
                    details.project.addMapLayer(context.temporaryLayerStore().takeMapLayer(layer))

                # Handle post processing
                if details.postProcessor():
                    details.postProcessor().postProcessLayer(layer, context, feedback)
            else:
                LOGGER.warning("No layer found for %s", lyrname)
        except Exception:
            LOGGER.error(f"Processing: Error loading result layer:\n{traceback.format_exc()}")
            wrongLayers.append(str(lyrname))

    if wrongLayers:
        msg = "The following layers were not correctly generated:"
        msg += "\n".join("%s" % lay for lay in wrongLayers)
        msg += (
            "You can check the log messages to find more information about "
            "the execution of the algorithm"
        )
        LOGGER.error(msg)

    return len(wrongLayers) == 0


class Feedback(QgsProcessingFeedback):
    """ Handle processing proggress messages

        This is a wrapper around WPS status
    """

    def __init__(self, response: WPSResponse, name: str, uuid_str: str):
        super().__init__()
        self._response = response
        self.name = name
        self.uuid = uuid_str[:8]

    def setProgress(self, progress: float):
        """ We update the wps status
        """
        self._response.update_status(status_percentage=int(progress + 0.5))

    def setProgressText(self, message: str):
        self._response.update_status(message=message)

    def cancel(self):
        """ Notify that job is cancelled
        """
        LOGGER.warning("Processing:%s:%s cancel() called", self.name, self.uuid)
        super().cancel()
        # TODO Call update status  when
        # https://projects.3liz.org/infra-v3/py-qgis-wps/issues/1 is fixed

    def reportError(self, error: str, fatalError: bool = False):
        (LOGGER.critical if fatalError else LOGGER.error)("%s:%s %s", self.name, self.uuid, error)

    def pushInfo(self, info: str):
        LOGGER.info("%s:%s %s", self.name, self.uuid, info)

    def pushDebugInfo(self, info: str):
        LOGGER.debug("%s:%s %s", self.name, self.uuid, info)


def run_processing_algorithm(
    alg: QgsProcessingAlgorithm,
    parameters: Mapping[str, QgsProcessingParameterDefinition],
    feedback: QgsProcessingFeedback,
    context: QgsProcessingContext,
    create_context: Mapping,
) -> Mapping[str, Any]:
    """ Re-implemente `Processing.runAlgorithm`

        Processing.runAlgorithm perform mainly checks useless in this context.
        More: it calls an `execute` function that in turns re-create the algorithm
        with no context

        see https://github.com/qgis/QGIS/blob/master/python/plugins/processing/core/Processing.py
    """
    # Check parameters values
    ok, msg = alg.checkParameterValues(parameters, context)
    if not ok:
        msg = f"Processing parameters error:\n{msg}"
        feedback.reportError(msg)
        raise ProcessException(msg)

    # Validate CRS
    if not alg.validateInputCrs(parameters, context):
        feedback.pushInfo(
            "Warning: Not all input layers use the same CRS\n"
            "This can cause unexpected results.")

    # Execute algorithm
    # XXX: The algorithm is recreated here
    # So we need to pass the create_context again
    # see https://qgis.org/api/qgsprocessingalgorithm_8cpp_source.html
    try:
        results, ok = alg.run(
            parameters,
            context,
            feedback,
            configuration=create_context,
            catchExceptions=False,
        )
        feedback.pushInfo(f"Results: {results}")
        return results
    except Exception as err:
        LOGGER.critical(traceback.format_exc())
        raise ProcessException(f"Algorithm failed with error {err}") from None


def run_algorithm(
    alg: QgsProcessingAlgorithm,
    parameters: Mapping[str, QgsProcessingParameterDefinition],
    feedback: QgsProcessingFeedback,
    context: QgsProcessingContext,
    uuid: str,
    outputs: Mapping[str, WPSOutput],
    create_context: Mapping = {},
) -> Mapping[str, Any]:
    # XXX Fix destination names for models
    # Collect destination names for destination parameters for restoring
    # them later
    destinations = {p: v.destinationName for p, v in parameters.items(
    ) if isinstance(v, QgsProcessingOutputLayerDefinition)}

    results = run_processing_algorithm(
        alg,
        parameters=parameters,
        feedback=feedback,
        context=context,
        create_context=create_context,
    )

    # From https://github.com/qgis/QGIS/blob/master/python/plugins/processing/core/Processing.py
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
            if outputName in destinations and context.willLoadLayerOnCompletion(value):
                context.layerToLoadOnCompletionDetails(value).name = destinations[outputName]
            processing_to_output(value, outdef, out, context)
    #
    # Handle results, we do not use onFinish callback because
    # we want to deal with the results
    #
    handle_layer_outputs(alg, context, parameters, results, uuid, feedback=feedback)
    return results


class QgsProcess(WPSProcess):

    def __init__(
        self,
        algorithm: Union[QgsProcessingAlgorithm, str],
        context: Optional[MapContext] = None,
    ):
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

        alg = _find_algorithm(algorithm) if isinstance(algorithm, str) else algorithm

        # Create input/output
        inputs = list(parse_input_definitions(alg, context=context))
        outputs = list(parse_output_definitions(alg, context=context))

        version = alg.version() if hasattr(alg, 'version') else _generic_version

        handler = partial(QgsProcess._handler, create_context=self._create_context)

        super().__init__(
            handler,
            identifier=alg.id(),
            version=version,
            title=alg.displayName(),
            # XXX Scripts do not provide description string
            abstract=alg.shortDescription() or alg.shortHelpString(),
            inputs=inputs,
            outputs=outputs,
        )

    @staticmethod
    def createInstance(ident: str, map_uri: Optional[str] = None) -> 'QgsProcess':
        """ Create a contextualized instance
        """
        mapcontext = MapContext(map_uri=map_uri)
        LOGGER.debug("Creating contextualized process for %s: %s", ident, map_uri)
        alg = _create_algorithm(ident, mapcontext)
        return QgsProcess(alg, mapcontext)

    @staticmethod
    def _handler(
        request: WPSRequest,
        response: WPSResponse,
        create_context: Mapping,
    ) -> WPSResponse:
        """  WPS process handler
        """
        uuid_str = str(response.uuid)
        LOGGER.info("Starting task %s:%s", uuid_str[:8], request.identifier)

        alg = QgsApplication.processingRegistry().createAlgorithmById(
            request.identifier,
            create_context,
        )

        destination = get_valid_filename(alg.id())

        # Allow configparser to resolve host_url
        confservice.set('wps.request', 'host_url', request.host_url)

        workdir = response.process.workdir
        context = ProcessingContext(workdir, map_uri=request.map_uri)
        feedback = Feedback(response, alg.id(), uuid_str=uuid_str)

        context.setFeedback(feedback)
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometrySkipInvalid)

        # Convert parameters from WPS inputs
        parameters = dict(
            input_to_processing(
                ident,
                inp,
                alg,
                context,
            ) for ident, inp in request.inputs.items()
        )

        # Build MAP output url '{map_uri}{uuid}/{name}.qgs'
        output_map_url = (
            f"{confservice.get('server', 'wps_result_map_uri')}"
            f"{response.uuid}/{destination}.qgs"
        )

        # Build WMS output url
        output_url = confservice.get('server', 'wms_response_url').format(map_url=output_map_url)

        context.wms_url = output_url

        run_algorithm(
            alg,
            parameters,
            feedback=feedback,
            context=context,
            outputs=response.outputs,
            uuid=uuid_str,
            create_context=create_context,
        )

        # Build advertised OWS services urla
        advertised_url = confservice.get('qgis.projects', 'advertised_ows_url')
        advertised_url = f"{advertised_url}?MAP={output_map_url}"

        ok = context.write_result(context.workdir, destination, advertised_url)
        if not ok:
            raise ProcessException("Failed to write %s" % destination)

        LOGGER.info("Task finished %s:%s", request.identifier, uuid_str)

        return response

    def clean(self):
        """ Override default

            We use the workdir as our final output dir
            The cleanup policy is driven by the request expiration time
        """
        pass
