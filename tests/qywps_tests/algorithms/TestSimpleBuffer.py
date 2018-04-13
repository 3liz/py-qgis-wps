""" Returns a simple bar chart
"""
import traceback



from qgis.core import (
    QgsProcessing,
    QgsProcessingUtils,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterFileDestination,
    QgsProcessingOutputHtml,
    QgsProcessingOutputFile,
    QgsProcessingOutputNumber,
    QgsProcessingOutputVectorLayer,
    QgsSettings,
    QgsFeatureRequest
)
from qgis.PyQt.QtCore import Qt, QCoreApplication

import processing

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

    def initAlgorithm( self, config=None ):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                'Input layer'
            )
        )

        self.addParameter(QgsProcessingParameterNumber(self.DISTANCE, 'Distance',
            type=QgsProcessingParameterNumber.Double, defaultValue=1000))

        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_VECTOR, 'Buffered Layer'))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            output = self.parameterAsOutputLayer(parameters, self.OUTPUT_VECTOR, context)

            # Run buffer
            buffer_result = processing.run("qgis:buffer", {
                'INPUT': parameters[self.INPUT],
                'DISTANCE': parameters[self.DISTANCE],
                'SEGMENTS': 10,
                'END_CAP_STYLE': 0,
                'JOIN_STYLE': 0,
                'MITER_LIMIT': 2,
                'DISSOLVE': True,
                'OUTPUT': output
            }, context=context, feedback=feedback)

            return { self.OUTPUT_VECTOR: output }

        except Exception:
            traceback.print_exc()

