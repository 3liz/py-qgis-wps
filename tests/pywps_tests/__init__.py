##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import sys
import unittest

import logging
logging.basicConfig( stream=sys.stderr )

logger = logging.getLogger("QYWPS")

formatstr = '[%(levelname)s] file=%(pathname)s line=%(lineno)s module=%(module)s function=%(funcName)s %(message)s'
channel   = logging.StreamHandler(sys.stderr)
channel.setFormatter(logging.Formatter(formatstr))
logger.addHandler(channel)
logger.setLevel( logging.DEBUG )

from pywps_tests import test_capabilities
from pywps_tests import test_describe
from pywps_tests import test_execute
from pywps_tests import test_exceptions
from pywps_tests import test_inout
from pywps_tests import test_literaltypes
from pywps_tests import validator
from pywps_tests import test_ows
from pywps_tests import test_formats
from pywps_tests import test_dblog
from pywps_tests import test_wpsrequest
from pywps_tests.validator import test_complexvalidators
from pywps_tests.validator import test_literalvalidators

def load_tests(loader=None, tests=None, pattern=None):
    """Load tests
    """
    return unittest.TestSuite([
        test_capabilities.load_tests(),
        test_execute.load_tests(),
        test_describe.load_tests(),
        test_inout.load_tests(),
        test_exceptions.load_tests(),
        test_ows.load_tests(),
        test_literaltypes.load_tests(),
        test_complexvalidators.load_tests(),
        test_literalvalidators.load_tests(),
        test_formats.load_tests(),
        test_dblog.load_tests(),
        test_wpsrequest.load_tests()
    ])

if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2, buffer=True).run(load_tests())
    if not result.wasSuccessful():
        sys.exit(1)
