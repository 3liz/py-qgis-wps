""" Test just returning simple value
"""

from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputString,
                       QgsProcessingAlgorithm)


class TestSimpleValue(QgsProcessingAlgorithm):

    PARAM1 = 'PARAM1'
    PARAM2 = 'PARAM2'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testsimplevalue'

    def displayName(self):
        return 'Test Simple Value'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm( self, config=None ):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(QgsProcessingParameterNumber(self.PARAM1, 'Parameter 1', 
                          type=QgsProcessingParameterNumber.Integer, 
                          minValue=0, maxValue=999, defaultValue=10))
        self.addParameter(QgsProcessingParameterString(self.PARAM2, 'Parameter 2', 
                          defaultValue=None))

        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))

    def processAlgorithm(self, parameters, context, feedback):
        
        param1 = self.parameterAsInt(parameters, self.PARAM1, context)
        param2 = self.parameterAsString(parameters, self.PARAM2, context)

        return {self.OUTPUT: f"{param1} {param2}"}
        
