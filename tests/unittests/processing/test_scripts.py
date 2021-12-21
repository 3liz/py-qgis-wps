""" Test Scripts algorithms
"""
import os
import pytest

from urllib.parse import urlparse, parse_qs, urlencode

from pyqgiswps.utils.contexts import chdir 

from pyqgiswps.inout import (LiteralInput, 
                        ComplexInput,
                        BoundingBoxInput, 
                        LiteralOutput, 
                        ComplexOutput,
                        BoundingBoxOutput)

from pyqgiswps.validator.allowed_value import ALLOWEDVALUETYPE

from qgis.core import QgsApplication
from qgis.core import (QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingOutputLayerDefinition,
                       QgsProcessingOutputHtml,
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputVectorLayer,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterField,
                       QgsProcessingUtils,
                       QgsProcessingFeedback,
                       QgsProcessingContext,
                       QgsReferencedRectangle,
                       QgsRectangle,
                       QgsCoordinateReferenceSystem,
                       QgsProject)

from processing.core.Processing import Processing


class Context(QgsProcessingContext):

    def __init__(self, project, workdir):
        super().__init__()
        self.workdir = workdir
        self.setProject(project)

        # Create the destination project
        self.destination_project = QgsProject()

    def write_result(self, workdir, name):
        """ Save results to disk
        """
        return self.destination_project.write(os.path.join(workdir,name+'.qgs'))


def test_alg_factory(): 
    """ Test that alg factory is functional
    """
    registry = QgsApplication.processingRegistry()

    provider = registry.providerById('script')
    assert provider is not None, 'script provider'
 
    alg = registry.algorithmById('script:testalgfactory')
    assert alg is not None, 'script:testalgfactory'


def test_model(): 
    """ Test that model  is functional
    """
    registry = QgsApplication.processingRegistry()

    provider = registry.providerById('model')
    assert provider is not None, 'model provider'
 
    alg = registry.algorithmById('model:centroides')
    assert alg is not None, 'model:centroides'


