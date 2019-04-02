""" Test just returning simple value
"""
from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputString,
                       QgsProcessingParameterEnum,
                       QgsProcessingAlgorithm)

class TestMultiOptionValue(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    IN_OPTIONS = ['value1','value2','value3']

    def __init__(self):
        super().__init__()

    @staticmethod
    def tr(string, context=''):
        return QCoreApplication.translate(context or 'Processing', string)

    def name(self):
        return 'testmultioptionvalue'

    def displayName(self):
        return 'Test Option Value'

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
            QgsProcessingParameterEnum(
                self.INPUT,
                'Values',
                optional=True,
                defaultValue=1,
                allowMultiple=True,
                options=self.IN_OPTIONS
            )
        )
        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))


    def processAlgorithm(self, parameters, context, feedback):
        
        param = self.parameterAsEnums(parameters, self.INPUT, context)

        return {self.OUTPUT: "selection is %s" % ','.join(str(x) for x in param)}
        
