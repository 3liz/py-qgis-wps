""" Test just returning simple value
"""

from qgis.core import (QgsProcessingParameterRasterLayer,
                       QgsProcessingAlgorithm)


class TestInputRasterLayer(QgsProcessingAlgorithm):

    INPUT  = 'INPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testinputrasterlayer'

    def displayName(self):
        return 'Test Input Raster Layer'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm( self, config=None ):
        """ Virtual override
    
           see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, 'Raster Layer'))

    def processAlgorithm(self, parameters, context, feedback):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        layer   = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        
