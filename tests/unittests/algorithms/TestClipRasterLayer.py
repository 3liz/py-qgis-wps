""" Test just returning simple value
"""

import processing

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterExtent,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)


class TestClipRasterLayer(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    EXTENT = 'EXTENT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testcliprasterlayer'

    def displayName(self):
        return 'Test Clip Raster Layer'

    def createInstance(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config=None):
        """ Virtual override

           see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, 'Raster Layer'))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, 'Clip Extent'))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, 'Clipped Layer'))

    def processAlgorithm(self, parameters, context, feedback):

        output = self.parameterAsOutputLayer(parameters, 'OUTPUT', context)

        # Run buffer
        _buffer_result = processing.run("gdal:cliprasterbyextent", {
            'INPUT': parameters['INPUT'],
            'PROJWIN': parameters['EXTENT'],
            'NODATA': None,
            'OPTIONS': '',
            'DATA_TYPE': 0,
            'OUTPUT': output,
        }, context=context, feedback=feedback)

        return {self.OUTPUT: output}
