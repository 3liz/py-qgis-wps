""" Test just returning simple value
"""

from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputString,
                       QgsProcessingAlgorithm)

from time import sleep

class TestLongProcess(QgsProcessingAlgorithm):

    PARAM1 = 'PARAM1'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testlongprocess'

    def displayName(self):
        return 'Test long time process'

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
        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))

    def processAlgorithm(self, parameters, context, feedback):
        
        param1 = self.parameterAsInt(parameters, self.PARAM1, context)

        for i in range(1,11):
            sleep(param1) 
            feedback.setProgress(i*10)

        return {self.OUTPUT: "%s" % param1}
        
