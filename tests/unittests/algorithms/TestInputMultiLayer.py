""" Test just returning simple value
"""

from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterMultipleLayers


class TestInputMultiLayer(QgsProcessingAlgorithm):

    INPUT = 'INPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testinputmultilayer'

    def displayName(self):
        return 'Test Input Multi Layer'

    def createInstance(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config=None):
        """ Virtual override

           see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        param = QgsProcessingParameterMultipleLayers(self.INPUT, 'Multiple Layer')
        param.setMinimumNumberInputs(1)

        self.addParameter(param)

    def processAlgorithm(self, parameters, context, feedback):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """

        # layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
