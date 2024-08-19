""" Test just returning simple value
"""

import traceback

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingOutputString,
    QgsProcessingParameterString,
)


class TestMapContext(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testmapcontext'

    def displayName(self):
        return 'Test Context'

    def createInstance(self):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        # XXX Do not modify anything to 'self': we CANNOT presume that same
        # instance will be used for processAlgorithm().
        project_name = config.get('project_uri')
        try:
            self.addParameter(QgsProcessingParameterString(self.INPUT, 'Input string',
                              defaultValue=project_name, optional=True))
        except Exception:
            traceback.print_exc()

        self.addOutput(QgsProcessingOutputString(self.OUTPUT, "Output"))

    def processAlgorithm(self, parameters, context, feedback):

        param = self.parameterDefinition(self.INPUT)
        outval = param.defaultValue()

        return {self.OUTPUT: "%s" % outval}
