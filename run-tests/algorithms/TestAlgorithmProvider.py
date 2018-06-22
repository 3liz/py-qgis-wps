""" Test processing Provider
"""

from qgis.core import (QgsApplication,
                       QgsProcessingProvider)

from .TestSimpleValue import TestSimpleValue
from .TestCopyLayer import TestCopyLayer
from .TestLongProcess import TestLongProcess
from .TestRaiseError import TestRaiseError
from .TestMapContext import TestMapContext

class TestAlgorithmProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def getAlgs(self):
       algs = [
            TestSimpleValue(),
            TestCopyLayer(),
            TestLongProcess(),
            TestRaiseError(),
            TestMapContext(),
       ]
       return algs
    
    def id(self):
        return 'lzmtest'

    def name(self):
        return "QyWPS Test"

    def loadAlgorithms(self):
        self.algs = self.getAlgs()
        for a in self.algs:
            self.addAlgorithm(a)

