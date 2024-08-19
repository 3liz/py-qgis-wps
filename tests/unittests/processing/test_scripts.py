""" Test Scripts algorithms
"""
import os

from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProject,
)


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
        return self.destination_project.write(os.path.join(workdir, name + '.qgs'))


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
