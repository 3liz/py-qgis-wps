""" Test file destination parsing
"""

from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputString,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingAlgorithm)


class TestFileDestination(QgsProcessingAlgorithm):

    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testfiledestination'

    def displayName(self):
        return 'Test input file destination'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm( self, config=None ):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(QgsProcessingParameterFileDestination(self.OUTPUT,
            'JSON file',
            'JSON Files (*.json)'
        ))

    def processAlgorithm(self, parameters, context, feedback):
        
        value = parameters[self.OUTPUT]
        return {self.OUTPUT: value}
        
