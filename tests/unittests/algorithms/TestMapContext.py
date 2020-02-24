""" Test just returning simple value
"""
from pathlib import Path

from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputString,
                       QgsProcessingAlgorithm)


class TestMapContext(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self, project_uri='not_set'):
        super().__init__()
        self.project_uri = project_uri

    def name(self):
        return 'testmapcontext'

    def displayName(self):
        return 'Test Context'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__(self.project_uri)

    def initAlgorithm( self, config={} ):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.project_uri = config.get('project_uri',self.project_uri)
        project_name = Path(self.project_uri).stem
        self.addParameter(QgsProcessingParameterString(self.INPUT, 'Input string', 
                          defaultValue=project_name))

        self.addOutput(QgsProcessingOutputString(self.OUTPUT,"Output"))

    def processAlgorithm(self, parameters, context, feedback):

        value = self.parameterAsString(parameters, self.INPUT, context)
        outval = Path(self.project_uri).stem
        return {self.OUTPUT: "%s" %  outval}
        
