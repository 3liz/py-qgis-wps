""" Test processing Provider
"""

import traceback

from qgis.core import (QgsApplication,
                       QgsProcessingProvider)

from .TestSimpleValue import TestSimpleValue
from .TestOptionValue import TestOptionValue
from .TestMultiOptionValue import TestMultiOptionValue
from .TestCopyLayer import TestCopyLayer
from .TestFileDestination import TestFileDestination
from .TestSimpleBuffer import TestSimpleBuffer

class TestAlgorithmProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def getAlgs(self):
        try:
            algs = [
                 TestSimpleValue(),
                 TestOptionValue(),
                 TestMultiOptionValue(),
                 TestCopyLayer(),
                 TestFileDestination(),
                 TestSimpleBuffer(),
            ]
        except:
            traceback.print_exc()
            algs = []
        return algs
    
    def id(self):
        return 'qywps_test'

    def name(self):
        return "QyWPS Test"

    def loadAlgorithms(self):
        self.algs = self.getAlgs()
        for a in self.algs:
            self.addAlgorithm(a)

