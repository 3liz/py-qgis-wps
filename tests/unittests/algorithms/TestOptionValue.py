""" Test just returning simple value
"""
from typing import ClassVar

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingOutputString,
    QgsProcessingParameterEnum,
)
from qgis.PyQt.QtCore import QCoreApplication


class TestOptionValue(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    IN_OPTIONS: ClassVar = ['value1', 'value2', 'value3']

    def __init__(self):
        super().__init__()

    @staticmethod
    def tr(string, context=''):
        return QCoreApplication.translate(context or 'Processing', string)

    def name(self):
        return 'testoptionvalue'

    def displayName(self):
        return 'Test Option Value'

    def createInstance(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config=None):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(
            QgsProcessingParameterEnum(
                self.INPUT,
                'Values',
                optional=True,
                defaultValue=1,
                options=self.IN_OPTIONS,
            ),
        )
        self.addOutput(QgsProcessingOutputString(self.OUTPUT, "Output"))

    def processAlgorithm(self, parameters, context, feedback):

        param = self.parameterAsString(parameters, self.INPUT, context)

        return {self.OUTPUT: "selection is %s" % (param)}
