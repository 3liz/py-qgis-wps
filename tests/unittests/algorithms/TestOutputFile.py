""" Test file destination parsing
"""

from qgis.core import (QgsProcessingOutputFile,
                       QgsProcessingAlgorithm)


class TestOutputFile(QgsProcessingAlgorithm):

    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testoutputfile'

    def displayName(self):
        return 'Test output file'

    def createInstance(self, config={}):
        """ Virtual override 

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm( self, config=None ):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addOutput(QgsProcessingOutputFile(self.OUTPUT,
            'JSON output file',
        ))

    def processAlgorithm(self, parameters, context, feedback):
        
        value = 'output.json'

        # Create the output file
        with open(value,'w') as fp:
            fp.write('{ "title": "hello json" }')

        return {self.OUTPUT: value}
        
