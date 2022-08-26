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
from .TestInputRasterLayer import TestInputRasterLayer
from .TestRaiseError import TestRaiseError
from .TestClipRasterLayer import TestClipRasterLayer
from .TestInputMultiLayer import TestInputMultiLayer
from .TestMapContext import TestMapContext
from .TestLongProcess import TestLongProcess
from .TestInputFile import TestInputFile
from .TestOutputVectorLayer import TestOutputVectorLayer
from .TestOutputFile import TestOutputFile
from .TestInputGeometry import TestInputGeometry
from .TestUltimateQuestion import TestUltimateQuestion


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
                 TestInputRasterLayer(),
                 TestRaiseError(),
                 TestClipRasterLayer(),
                 TestInputMultiLayer(),
                 TestMapContext(),
                 TestLongProcess(),
                 TestInputFile(),
                 TestOutputVectorLayer(),
                 TestOutputFile(),
                 TestInputGeometry(),
                 TestUltimateQuestion(),
            ]
        except:
            traceback.print_exc()
            algs = []
        return algs

    def id(self):
        return 'pyqgiswps_test'

    def name(self):
        return "PyQgisWPS Test"

    def loadAlgorithms(self):
        self.algs = self.getAlgs()
        for a in self.algs:
            self.addAlgorithm(a)

class DummyAlgorithmProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def id(self):
        return 'pyqgiswps_dummy_test'

    def name(self):
        return "Py-Qgis-WPS Dummy Test"

    def loadAlgorithms(self):
        pass

