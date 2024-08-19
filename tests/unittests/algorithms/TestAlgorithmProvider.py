""" Test processing Provider
"""

import traceback

from qgis.core import QgsProcessingProvider

from .TestClipRasterLayer import TestClipRasterLayer
from .TestCopyLayer import TestCopyLayer
from .TestFileDestination import TestFileDestination
from .TestInputFile import TestInputFile
from .TestInputGeometry import TestInputGeometry
from .TestInputMultiLayer import TestInputMultiLayer
from .TestInputRasterLayer import TestInputRasterLayer
from .TestLongProcess import TestLongProcess
from .TestMapContext import TestMapContext
from .TestMultiOptionValue import TestMultiOptionValue
from .TestOptionValue import TestOptionValue
from .TestOutputFile import TestOutputFile
from .TestOutputVectorLayer import TestOutputVectorLayer
from .TestRaiseError import TestRaiseError
from .TestSimpleBuffer import TestSimpleBuffer
from .TestSimpleValue import TestSimpleValue
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
        except Exception:
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
