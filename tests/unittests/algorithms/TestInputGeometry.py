""" Test Geomtry parameter
"""

from qgis.core import (QgsProcessingParameterGeometry,
                       QgsProcessingOutputString,
                       QgsProcessingAlgorithm)


class TestInputGeometry(QgsProcessingAlgorithm):

    INPUT  = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testinputgeometry'

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
        self.addParameter(QgsProcessingParameterGeometry(self.INPUT, 'Geometry'))

        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))

    def processAlgorithm(self, parameters, context, feedback):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        geom = self.parameterAsGeometry(parameters, self.INPUT, context)
        
        if geom.isEmpty():
            out = "{}"
        else:
            out = geom.asJson();

        return { self.OUTPUT: out }

