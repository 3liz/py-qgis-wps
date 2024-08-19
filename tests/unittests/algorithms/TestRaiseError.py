""" Test just returning simple value
"""

from qgis.core import QgsProcessingAlgorithm, QgsProcessingOutputString, QgsProcessingParameterNumber


class TestRaiseError(QgsProcessingAlgorithm):

    PARAM1 = 'PARAM1'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testraiseerror'

    def displayName(self):
        return 'Test raising error'

    def createInstance(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config=None):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(QgsProcessingParameterNumber(self.PARAM1, 'Parameter 1',
                          type=QgsProcessingParameterNumber.Integer,
                          minValue=0, maxValue=999, defaultValue=10))
        self.addOutput(QgsProcessingOutputString(self.OUTPUT, "Output"))

    def processAlgorithm(self, parameters, context, feedback):

        param1 = self.parameterAsInt(parameters, self.PARAM1, context)

        raise Exception("I'm melting !!!")

        return {self.OUTPUT: "%s" % param1}
