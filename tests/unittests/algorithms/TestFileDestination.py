""" Test file destination parsing
"""

from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFileDestination


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

    def initAlgorithm(self, config=None):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        param = QgsProcessingParameterFileDestination(self.OUTPUT,
            'JSON file',
            'JSON Files (*.json)',
        )
        param.setMetadata({'wps:as_reference': True})

        self.addParameter(param)

    def processAlgorithm(self, parameters, context, feedback):

        value = parameters[self.OUTPUT]

        # Create the output file
        with open(value, 'w') as fp:
            fp.write('{ "title": "hello json" }')

        return {self.OUTPUT: value}
