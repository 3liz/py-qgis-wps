""" Test just returning simple value
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingOutputLayerDefinition,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
    QgsVectorFileWriter,
)


class TestCopyLayer(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'testcopylayer'

    def displayName(self):
        return 'Test Copy Layer'

    def createInstance(self, config={}):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        return self.__class__()

    def initAlgorithm(self, config=None):
        """ Virtual override

           see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, 'Vector Layer'))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, 'Output Layer',
                          defaultValue=QgsProcessingOutputLayerDefinition(f'{self.OUTPUT}.shp')))

    def processAlgorithm(self, parameters, context, feedback):
        """ Virtual override

            see https://qgis.org/api/classQgsProcessingAlgorithm.html
        """
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        outlayer = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = QgsVectorFileWriter.driverForExtension('.shp')

        # Save a copy of our layer
        (err, msg, outfile, _layer_name) = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            outlayer,
            context.transformContext(),
            options,
        )

        if err != QgsVectorFileWriter.NoError:
            feedback.reportError(f"Error writing vector layer {outlayer}: {msg}")

        return {self.OUTPUT: outfile}
