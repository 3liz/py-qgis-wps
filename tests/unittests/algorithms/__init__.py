
from qgis.core import QgsApplication

from .TestAlgorithmProvider import TestAlgorithmProvider


class Test:
    def __init__(self):
        pass

    def initProcessing(self):
        self._provider = TestAlgorithmProvider()

        reg = QgsApplication.processingRegistry()
        reg.addProvider(self._provider)


def classFactory(iface: None) -> Test:
    return Test()
