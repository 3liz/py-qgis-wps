""" Returns a simple bar chart
"""
import traceback

import processing

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
)


class TestSimpleBuffer(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    DISTANCE = 'DISTANCE'
    OUTPUT_VECTOR = 'OUTPUT_VECTOR'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'simplebuffer'

    def displayName(self):
        return 'Simple buffer'

    def createInstance(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config=None):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                'Input layer',
            ),
        )

        self.addParameter(QgsProcessingParameterNumber(self.DISTANCE, 'Distance',
            type=QgsProcessingParameterNumber.Double, defaultValue=1000))

        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_VECTOR, 'Buffered Layer'))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            output = self.parameterAsOutputLayer(parameters, self.OUTPUT_VECTOR, context)

            # Run buffer
            _buffer_result = processing.run("qgis:buffer", {
                'INPUT': parameters[self.INPUT],
                'DISTANCE': parameters[self.DISTANCE],
                'SEGMENTS': 10,
                'END_CAP_STYLE': 0,
                'JOIN_STYLE': 0,
                'MITER_LIMIT': 2,
                'DISSOLVE': False,
                'OUTPUT': output,
            }, context=context, feedback=feedback)

            return {self.OUTPUT_VECTOR: output}

        except Exception:
            traceback.print_exc()
