""" Test just returning simple value
"""

from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputString,
                       QgsProcessingAlgorithm)


class TestMapContext(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testmapcontext'

    def displayName(self):
        return 'Test Context'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm( self, config={} ):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        map_uri = config.get('map_uri','not_set')
        
        self.addParameter(QgsProcessingParameterString(self.INPUT, 'Input string', 
                          defaultValue=map_uri))

        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))

    def processAlgorithm(self, parameters, context, feedback):
        
        value = self.parameterAsString(parameters, self.INPUT, context)
        return {self.OUTPUT: "%s" %  value}
        
