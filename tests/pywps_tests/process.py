##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

"""Test process
"""

import os
import sys
from io import StringIO
from lxml import objectify

qywpsPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0],".."))
sys.path.insert(0,qywpsPath)
sys.path.append(qywpsPath)

import unittest

from qywps import Process
from qywps.inout import LiteralInput
from qywps.inout import BoundingBoxInput
from qywps.inout import ComplexInput

class ProcessTestCase(unittest.TestCase):

    def test_get_input_title(self):
        """Test returning the proper input title"""

        # configure
        def donothing(*args, **kwargs):
            pass
        process = Process(donothing, "process", title="Process",
                          inputs=[
                              LiteralInput("length", title="Length"),
                              BoundingBoxInput("bbox", title="BBox", crss=[]),
                              ComplexInput("vector", title="Vector")
                          ],
                          outputs=[],
                          metadata=[Metadata('process metadata 1', 'http://example.org/1'), Metadata('process metadata 2', 'http://example.org/2')]
        )
        inputs = {
            input.identifier: input.title
            for input
            in process.inputs
        }
        self.assertEqual("Length", inputs['length'])
        self.assertEqual("BBox", inputs["bbox"])
        self.assertEqual("Vector", inputs["vector"])

if __name__ == "__main__":
   suite = unittest.TestLoader().loadTestsFromTestCase(ProcessTestCase)
   unittest.TextTestRunner(verbosity=4).run(suite)
