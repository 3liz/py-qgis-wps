""" Test just returning simple value
"""

from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingOutputVectorLayer,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputNumber,
                       QgsProcessingAlgorithm,
                       QgsVectorFileWriter)


class TestCopyLayer(QgsProcessingAlgorithm):

    INPUT  = 'INPUT'
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

    def initAlgorithm( self, config=None ):
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
        layer   = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        outfile = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # Save a copy of our layer
        err = QgsVectorFileWriter.writeAsVectorFormat(layer, outfile, "utf-8", driverName="ESRI Shapefile") 

        if err[0] != QgsVectorFileWriter.NoError:
            feedback.reportError("Error writing vector layer %s: %s" % (outfile, err))

        return {self.OUTPUT: outfile }
        
