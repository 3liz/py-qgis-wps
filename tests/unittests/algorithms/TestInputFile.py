""" Test just returning simple value
"""

from qgis.core import (QgsProcessingParameterFile,
                       QgsProcessingAlgorithm,
                       QgsProcessingOutputString)


class TestInputFile(QgsProcessingAlgorithm):

    INPUT  = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testinputfile'

    def displayName(self):
        return 'Test Input File'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm( self, config=None ):
        """ Virtual override
    
           see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        param = QgsProcessingParameterFile(self.INPUT, 'Input file', 
                                           extension=".txt")
        self.addParameter(param)
        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))

    def processAlgorithm(self, parameters, context, feedback):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        fileinput = self.parameterAsFile(parameters, self.INPUT, context)
        feedback.pushInfo("Opening file: %s" % fileinput)

        data = "NO DATA"
        with open(fileinput) as f:
            data = f.read()

        return { self.OUTPUT: data }
